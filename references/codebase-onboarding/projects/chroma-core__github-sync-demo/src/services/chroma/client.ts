import { ChromaClient, CloudClient } from "chromadb";
import {
  ChromaCloudQwenEmbeddingFunction,
  ChromaCloudQwenEmbeddingModel,
  ChromaCloudQwenEmbeddingTask,
} from "@chroma-core/chroma-cloud-qwen";
import { env } from "@/lib/env";
import { trace } from "@opentelemetry/api";
import { chromaDocumentMetadataSchema, type QueryResult } from "@/types/chroma";

const tracer = trace.getTracer("chroma");

const client = new CloudClient({
  apiKey: env.CHROMA_API_KEY,
  tenant: env.CHROMA_TENANT,
  database: env.CHROMA_DATABASE,
});

const qwenEf = new ChromaCloudQwenEmbeddingFunction({
  model: ChromaCloudQwenEmbeddingModel.QWEN3_EMBEDDING_0p6B,
  task: ChromaCloudQwenEmbeddingTask.NL_TO_CODE,
});

function parseResults(
  ids: string[],
  metadatas: (Record<string, unknown> | null)[],
  documents: (string | null)[],
  distances?: (number | null)[],
): QueryResult[] {
  const results: QueryResult[] = [];

  for (let i = 0; i < ids.length; i++) {
    const id = ids[i];
    const rawMetadata = metadatas[i];
    const document = documents[i];

    if (!rawMetadata || !document) continue;

    const parseResult = chromaDocumentMetadataSchema.safeParse(rawMetadata);
    if (!parseResult.success) continue;

    results.push({
      id,
      distance: distances?.[i] ?? 0,
      metadata: parseResult.data,
      document,
    });
  }

  return results;
}

export async function queryCollection(
  collectionName: string,
  queryText: string,
  nResults: number = 10,
): Promise<QueryResult[]> {
  const span = tracer.startSpan("chroma.queryCollection");

  try {
    const collection = await client.getCollection({
      name: collectionName,
      embeddingFunction: qwenEf,
    });

    const results = await collection.query({
      queryTexts: [queryText],
      nResults,
    });

    if (!results.ids?.[0]) return [];

    const parsed = parseResults(
      results.ids[0],
      results.metadatas?.[0] ?? [],
      results.documents?.[0] ?? [],
      results.distances?.[0],
    );

    span.setAttribute("results.count", parsed.length);
    return parsed;
  } catch (error) {
    span.recordException(error as Error);
    throw error;
  } finally {
    span.end();
  }
}

export async function getFileContents(
  collectionName: string,
  filePath: string,
): Promise<string | null> {
  const span = tracer.startSpan("chroma.getFileContents");

  try {
    const collection = await client.getCollection({
      name: collectionName,
      embeddingFunction: qwenEf,
    });

    const results = await collection.get({
      where: { document_key: filePath },
      limit: 300,
    });

    if (!results.ids || results.ids.length === 0) return null;

    const parsed = parseResults(
      results.ids,
      results.metadatas ?? [],
      results.documents ?? [],
    );

    if (parsed.length === 0) return null;

    const sorted = parsed.sort((a, b) => {
      const aStart = a.metadata?.start_line ?? Infinity;
      const bStart = b.metadata?.start_line ?? Infinity;
      return aStart - bStart;
    });

    const content = sorted
      .map((r) => r.document)
      .filter((doc): doc is string => doc !== undefined)
      .join("\n");

    span.setAttribute("results.chunks", parsed.length);
    return content;
  } catch (error) {
    span.recordException(error as Error);
    throw error;
  } finally {
    span.end();
  }
}

export interface GrepMatch {
  lineNumber: number;
  content: string;
}

export interface GrepFileResult {
  path: string;
  matches: GrepMatch[];
}

export interface GrepResult {
  files: GrepFileResult[];
  totalMatches: number;
}

export async function grepCollection(
  collectionName: string,
  pattern: string,
  maxChunks: number = 50,
): Promise<GrepResult> {
  const span = tracer.startSpan("chroma.grepCollection");

  try {
    const collection = await client.getCollection({
      name: collectionName,
      embeddingFunction: qwenEf,
    });

    const results = await collection.get({
      whereDocument: { $contains: pattern },
      limit: maxChunks,
    });

    if (!results.ids) {
      return { files: [], totalMatches: 0 };
    }

    const parsed = parseResults(
      results.ids,
      results.metadatas ?? [],
      results.documents ?? [],
    );

    const fileMatches = new Map<string, GrepMatch[]>();
    let totalMatches = 0;

    for (const chunk of parsed) {
      const path = chunk.metadata.document_key;
      const startLine = chunk.metadata.start_line ?? 1;
      const lines = chunk.document.split("\n");

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        if (line.includes(pattern)) {
          const lineNumber = startLine + i;
          if (!fileMatches.has(path)) {
            fileMatches.set(path, []);
          }
          fileMatches.get(path)!.push({
            lineNumber,
            content: line.trim(),
          });
          totalMatches++;
        }
      }
    }

    const files = Array.from(fileMatches.entries())
      .map(([path, matches]) => ({
        path,
        matches: matches.sort((a, b) => a.lineNumber - b.lineNumber),
      }))
      .sort((a, b) => a.path.localeCompare(b.path));

    span.setAttribute("results.files", files.length);
    span.setAttribute("results.totalMatches", totalMatches);
    return { files, totalMatches };
  } catch (error) {
    span.recordException(error as Error);
    throw error;
  } finally {
    span.end();
  }
}
