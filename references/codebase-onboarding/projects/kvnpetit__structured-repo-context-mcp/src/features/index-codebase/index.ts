/**
 * Index Codebase Feature
 *
 * Indexes a directory by:
 * 1. Scanning for supported files
 * 2. Chunking each file
 * 3. Generating embeddings via Ollama
 * 4. Storing in LanceDB
 */

import { z } from "zod";
import * as fs from "node:fs";
import * as path from "node:path";
import ignore, { type Ignore } from "ignore";
import type { Feature, FeatureResult } from "@features/types";
import { EMBEDDING_CONFIG } from "@config";
import {
  chunkFile,
  createOllamaClient,
  createVectorStore,
  enrichChunksFromFile,
  shouldIndexFile,
  type EmbeddedChunk,
  type EnrichedChunk,
  type EnrichmentOptions,
} from "@core/embeddings";
import { logger } from "@utils";
import { readPathAliasesCached } from "@core/utils";

/** Default concurrency for parallel file processing */
const DEFAULT_CONCURRENCY = 4;

/**
 * Process items in parallel with concurrency limit using worker pool pattern
 */
async function parallelMap<T, R>(
  items: T[],
  processor: (item: T) => Promise<R>,
  concurrency: number,
): Promise<R[]> {
  const results: (R | undefined)[] = new Array<R | undefined>(items.length);
  let currentIndex = 0;

  const worker = async (): Promise<void> => {
    while (currentIndex < items.length) {
      const index = currentIndex++;
      const item = items[index];
      if (item !== undefined) {
        results[index] = await processor(item);
      }
    }
  };

  const workers = Array.from(
    { length: Math.min(concurrency, items.length) },
    async () => worker(),
  );
  await Promise.all(workers);

  // Filter out undefined values (shouldn't happen but TypeScript needs this)
  return results.filter((r): r is R => r !== undefined);
}

export const indexCodebaseSchema = z.object({
  directory: z
    .string()
    .optional()
    .default(".")
    .describe("Path to the directory to index (defaults to current directory)"),
  force: z
    .boolean()
    .optional()
    .default(false)
    .describe("Force re-indexing even if index exists"),
  exclude: z
    .array(z.string())
    .optional()
    .default([])
    .describe("Additional glob patterns to exclude"),
  concurrency: z
    .number()
    .int()
    .positive()
    .optional()
    .default(DEFAULT_CONCURRENCY)
    .describe("Number of files to process in parallel (default: 4)"),
});

export type IndexCodebaseInput = z.infer<typeof indexCodebaseSchema>;

interface IndexResult {
  directory: string;
  filesIndexed: number;
  chunksCreated: number;
  languages: Record<string, number>;
  errors: string[];
}

/**
 * Create an ignore instance with gitignore patterns and additional exclusions
 */
function createIgnoreFilter(
  baseDir: string,
  additionalExclusions: string[],
): Ignore {
  const ig = ignore();

  // Read .gitignore if it exists
  const gitignorePath = path.join(baseDir, ".gitignore");
  if (fs.existsSync(gitignorePath)) {
    try {
      const content = fs.readFileSync(gitignorePath, "utf-8");
      ig.add(content);
    } catch {
      // Ignore read errors
    }
  }

  // Add additional user exclusions
  if (additionalExclusions.length > 0) {
    ig.add(additionalExclusions);
  }

  return ig;
}

/**
 * Check if a name starts with a dot (hidden file/folder)
 */
function isHidden(name: string): boolean {
  return name.startsWith(".");
}

/**
 * Recursively collect files from a directory
 */
function collectFiles(dir: string, ig: Ignore, baseDir: string): string[] {
  const files: string[] = [];

  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    // Skip hidden files/folders (starting with .)
    if (isHidden(entry.name)) {
      continue;
    }

    const fullPath = path.join(dir, entry.name);
    const relativePath = path.relative(baseDir, fullPath).replace(/\\/g, "/");

    // Check if ignored by gitignore patterns
    if (ig.ignores(relativePath)) {
      continue;
    }

    if (entry.isDirectory()) {
      files.push(...collectFiles(fullPath, ig, baseDir));
    } else if (entry.isFile() && shouldIndexFile(entry.name)) {
      files.push(fullPath);
    }
  }

  return files;
}

/**
 * Execute the index_codebase feature
 */
export async function execute(
  input: IndexCodebaseInput,
): Promise<FeatureResult> {
  const { directory, force, exclude, concurrency } = input;

  // Validate directory exists
  if (!fs.existsSync(directory)) {
    return {
      success: false,
      error: `Directory not found: ${directory}`,
    };
  }

  const absoluteDir = path.resolve(directory);

  // Initialize components
  const ollamaClient = createOllamaClient(EMBEDDING_CONFIG);
  const vectorStore = createVectorStore(absoluteDir, EMBEDDING_CONFIG);

  // Check Ollama health
  const health = await ollamaClient.healthCheck();
  if (!health.ok) {
    return {
      success: false,
      error: health.error ?? "Ollama is not available",
    };
  }

  // Check if index exists and force is not set
  if (vectorStore.exists() && !force) {
    return {
      success: false,
      error:
        "Index already exists. Use force=true to re-index or search_code to query.",
    };
  }

  const result: IndexResult = {
    directory: absoluteDir,
    filesIndexed: 0,
    chunksCreated: 0,
    languages: {},
    errors: [],
  };

  try {
    // Connect to vector store
    await vectorStore.connect();

    // Clear existing data if force re-indexing
    if (force && vectorStore.exists()) {
      await vectorStore.clear();
    }

    // Create ignore filter from .gitignore and user exclusions
    const ig = createIgnoreFilter(absoluteDir, exclude);

    // Collect files
    const files = collectFiles(absoluteDir, ig, absoluteDir);

    if (files.length === 0) {
      return {
        success: true,
        message: "No indexable files found in directory",
        data: result,
      };
    }

    // Read path aliases from tsconfig.json if present
    const pathAliases = readPathAliasesCached(absoluteDir);
    const aliasCount = Object.keys(pathAliases).length;

    // Enrichment options with cross-file context enabled
    const enrichmentOptions: EnrichmentOptions = {
      projectRoot: absoluteDir,
      pathAliases,
      includeCrossFileContext: true,
    };

    logger.debug(
      `Indexing ${String(files.length)} files with concurrency=${String(concurrency)} (projectRoot: ${absoluteDir}, ${String(aliasCount)} path aliases)`,
    );

    // Process files in parallel: chunk and enrich
    interface FileProcessResult {
      chunks: EnrichedChunk[];
      error?: string;
    }

    const processFile = async (
      filePath: string,
    ): Promise<FileProcessResult> => {
      try {
        const content = fs.readFileSync(filePath, "utf-8");
        const chunks = await chunkFile(filePath, content, EMBEDDING_CONFIG);

        // Enrich chunks with semantic metadata including cross-file context
        const enrichedChunks = await enrichChunksFromFile(
          chunks,
          content,
          enrichmentOptions,
        );

        return { chunks: enrichedChunks };
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err);
        return {
          chunks: [],
          error: `Error processing ${filePath}: ${errorMsg}`,
        };
      }
    };

    // Process all files in parallel with concurrency limit
    const fileResults = await parallelMap(files, processFile, concurrency);

    // Aggregate results
    const allEnrichedChunks: EnrichedChunk[] = [];

    for (const fileResult of fileResults) {
      if (fileResult.error) {
        result.errors.push(fileResult.error);
      } else {
        allEnrichedChunks.push(...fileResult.chunks);
        result.filesIndexed++;

        // Track language stats
        for (const chunk of fileResult.chunks) {
          result.languages[chunk.language] =
            (result.languages[chunk.language] ?? 0) + 1;
        }
      }
    }

    // Generate embeddings in batches using enriched content
    const { batchSize } = EMBEDDING_CONFIG;
    const embeddedChunks: EmbeddedChunk[] = [];

    for (let i = 0; i < allEnrichedChunks.length; i += batchSize) {
      const batch = allEnrichedChunks.slice(i, i + batchSize);
      // Use enrichedContent for embedding (contains metadata header + original code)
      const texts = batch.map((c) => c.enrichedContent);

      try {
        const embeddings = await ollamaClient.embedBatch(texts);

        for (let j = 0; j < batch.length; j++) {
          const chunk = batch[j];
          const vector = embeddings[j];

          if (chunk && vector) {
            // Store original chunk data (without enrichedContent to save space)
            embeddedChunks.push({
              id: chunk.id,
              content: chunk.content,
              filePath: chunk.filePath,
              language: chunk.language,
              startLine: chunk.startLine,
              endLine: chunk.endLine,
              symbolName: chunk.symbolName,
              symbolType: chunk.symbolType,
              vector,
            });
          }
        }
      } catch (err) {
        const errorMsg = err instanceof Error ? err.message : String(err);
        result.errors.push(`Embedding batch error: ${errorMsg}`);
      }
    }

    // Store embeddings
    if (embeddedChunks.length > 0) {
      await vectorStore.addChunks(embeddedChunks);
      result.chunksCreated = embeddedChunks.length;
    }

    vectorStore.close();

    const hasErrors = result.errors.length > 0;
    const message = hasErrors
      ? `Indexed ${String(result.filesIndexed)} files (${String(result.chunksCreated)} chunks) with ${String(result.errors.length)} errors`
      : `Successfully indexed ${String(result.filesIndexed)} files (${String(result.chunksCreated)} chunks)`;

    return {
      success: true,
      message,
      data: result,
    };
  } catch (err) {
    vectorStore.close();
    const errorMsg = err instanceof Error ? err.message : String(err);
    return {
      success: false,
      error: `Indexing failed: ${errorMsg}`,
      data: result,
    };
  }
}

export const indexCodebaseFeature: Feature<typeof indexCodebaseSchema> = {
  name: "index_codebase",
  description:
    "Index a codebase for semantic code search. USE THIS FIRST before search_code. Required once per project - creates vector embeddings for 50+ languages. After initial indexing, use update_index for incremental updates.",
  schema: indexCodebaseSchema,
  execute,
};
