/**
 * Update Index Feature
 *
 * Incrementally updates the codebase index by:
 * 1. Detecting files that have changed since last indexing
 * 2. Re-indexing only the changed files
 * 3. Removing deleted files from the index
 *
 * Uses SHA-256 hash comparison to detect real content changes.
 */

import { z } from "zod";
import * as fs from "node:fs";
import * as path from "node:path";
import * as crypto from "node:crypto";
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
  type EnrichmentOptions,
} from "@core/embeddings";
import { readPathAliasesCached } from "@core/utils";

/** Cache file name for storing hashes */
const HASH_CACHE_FILE = ".src-index-hashes.json";

export const updateIndexSchema = z.object({
  directory: z
    .string()
    .optional()
    .default(".")
    .describe("Path to the indexed directory"),
  dryRun: z
    .boolean()
    .optional()
    .default(false)
    .describe("Only report changes without updating the index"),
  force: z
    .boolean()
    .optional()
    .default(false)
    .describe("Force re-index of all files (ignore hash cache)"),
});

export type UpdateIndexInput = z.infer<typeof updateIndexSchema>;

type HashCache = Record<string, string>;

interface UpdateResult {
  directory: string;
  dryRun: boolean;
  added: string[];
  modified: string[];
  removed: string[];
  unchanged: number;
  errors: string[];
}

/**
 * Compute SHA-256 hash of content
 */
function computeHash(content: string): string {
  return crypto.createHash("sha256").update(content, "utf8").digest("hex");
}

/**
 * Get hash cache file path
 */
function getHashCachePath(directory: string): string {
  return path.join(directory, ".src-index", HASH_CACHE_FILE);
}

/**
 * Load hash cache from disk
 */
function loadHashCache(directory: string): HashCache {
  const cachePath = getHashCachePath(directory);
  if (fs.existsSync(cachePath)) {
    try {
      const content = fs.readFileSync(cachePath, "utf-8");
      return JSON.parse(content) as HashCache;
    } catch {
      return {};
    }
  }
  return {};
}

/**
 * Save hash cache to disk
 */
function saveHashCache(directory: string, cache: HashCache): void {
  const cachePath = getHashCachePath(directory);
  const cacheDir = path.dirname(cachePath);
  if (!fs.existsSync(cacheDir)) {
    fs.mkdirSync(cacheDir, { recursive: true });
  }
  fs.writeFileSync(cachePath, JSON.stringify(cache, null, 2));
}

/**
 * Create gitignore filter
 */
function createIgnoreFilter(directory: string): Ignore {
  const ig = ignore();
  ig.add(["node_modules", ".git", "dist", "build", ".src-index"]);

  const gitignorePath = path.join(directory, ".gitignore");
  if (fs.existsSync(gitignorePath)) {
    const content = fs.readFileSync(gitignorePath, "utf-8");
    ig.add(content);
  }

  return ig;
}

/**
 * Check if a name starts with a dot (hidden)
 */
function isHidden(name: string): boolean {
  return name.startsWith(".");
}

/**
 * Recursively collect files
 */
function collectFiles(dir: string, ig: Ignore, baseDir: string): string[] {
  const files: string[] = [];

  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    if (isHidden(entry.name)) {
      continue;
    }

    const fullPath = path.join(dir, entry.name);
    const relativePath = path.relative(baseDir, fullPath).replace(/\\/g, "/");

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
 * Execute the update_index feature
 */
export async function execute(input: UpdateIndexInput): Promise<FeatureResult> {
  const { directory, dryRun, force } = input;

  // Validate directory
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

  // Check if index exists
  if (!vectorStore.exists()) {
    return {
      success: false,
      error: `No index found for directory. Run index_codebase first: ${absoluteDir}`,
    };
  }

  const result: UpdateResult = {
    directory: absoluteDir,
    dryRun,
    added: [],
    modified: [],
    removed: [],
    unchanged: 0,
    errors: [],
  };

  try {
    // Check Ollama health (only if not dry run)
    if (!dryRun) {
      const health = await ollamaClient.healthCheck();
      if (!health.ok) {
        return {
          success: false,
          error: health.error ?? "Ollama is not available",
        };
      }
    }

    // Connect to vector store
    await vectorStore.connect();

    // Load hash cache
    const hashCache = force ? {} : loadHashCache(absoluteDir);
    const newHashCache: HashCache = {};

    // Collect current files
    const ig = createIgnoreFilter(absoluteDir);
    const currentFiles = new Set(collectFiles(absoluteDir, ig, absoluteDir));

    // Get indexed files from vector store
    const indexedFiles = new Set(await vectorStore.getIndexedFiles());

    // Find files to add/modify/remove
    const filesToProcess: { path: string; type: "add" | "modify" }[] = [];

    for (const filePath of currentFiles) {
      const content = fs.readFileSync(filePath, "utf-8");
      const hash = computeHash(content);
      newHashCache[filePath] = hash;

      if (!indexedFiles.has(filePath)) {
        // New file
        result.added.push(path.relative(absoluteDir, filePath));
        filesToProcess.push({ path: filePath, type: "add" });
      } else if (hashCache[filePath] !== hash) {
        // Modified file
        result.modified.push(path.relative(absoluteDir, filePath));
        filesToProcess.push({ path: filePath, type: "modify" });
      } else {
        result.unchanged++;
      }
    }

    // Find removed files
    for (const filePath of indexedFiles) {
      if (!currentFiles.has(filePath)) {
        result.removed.push(path.relative(absoluteDir, filePath));
      }
    }

    // If dry run, just report what would be done
    if (dryRun) {
      vectorStore.close();

      const message = buildDryRunMessage(result);
      return {
        success: true,
        message,
        data: result,
      };
    }

    // Read path aliases from tsconfig.json if present
    const pathAliases = readPathAliasesCached(absoluteDir);

    // Enrichment options
    const enrichmentOptions: EnrichmentOptions = {
      projectRoot: absoluteDir,
      pathAliases,
      includeCrossFileContext: true,
    };

    // Process files
    const embeddedChunks: EmbeddedChunk[] = [];

    for (const { path: filePath, type } of filesToProcess) {
      try {
        // Delete existing chunks if modifying
        if (type === "modify") {
          await vectorStore.deleteByFilePath(filePath);
        }

        const content = fs.readFileSync(filePath, "utf-8");
        const chunks = await chunkFile(filePath, content, EMBEDDING_CONFIG);

        if (chunks.length === 0) {
          continue;
        }

        const enrichedChunks = await enrichChunksFromFile(
          chunks,
          content,
          enrichmentOptions,
        );

        const texts = enrichedChunks.map((c) => c.enrichedContent);
        const embeddings = await ollamaClient.embedBatch(texts);

        for (let i = 0; i < enrichedChunks.length; i++) {
          const chunk = enrichedChunks[i];
          const vector = embeddings[i];
          if (chunk && vector) {
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
        result.errors.push(`Error processing ${filePath}: ${errorMsg}`);
      }
    }

    // Add new chunks
    if (embeddedChunks.length > 0) {
      await vectorStore.addChunks(embeddedChunks);
    }

    // Remove deleted files
    for (const relativePath of result.removed) {
      const filePath = path.join(absoluteDir, relativePath);
      await vectorStore.deleteByFilePath(filePath);
    }

    // Save new hash cache
    saveHashCache(absoluteDir, newHashCache);

    vectorStore.close();

    const message = buildResultMessage(result);

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
      error: `Update failed: ${errorMsg}`,
    };
  }
}

/**
 * Build message for dry run
 */
function buildDryRunMessage(result: UpdateResult): string {
  const lines: string[] = ["Dry run - changes detected:"];

  if (result.added.length > 0) {
    lines.push(`\nFiles to add (${String(result.added.length)}):`);
    for (const f of result.added.slice(0, 10)) {
      lines.push(`  + ${f}`);
    }
    if (result.added.length > 10) {
      lines.push(`  ... and ${String(result.added.length - 10)} more`);
    }
  }

  if (result.modified.length > 0) {
    lines.push(`\nFiles to update (${String(result.modified.length)}):`);
    for (const f of result.modified.slice(0, 10)) {
      lines.push(`  ~ ${f}`);
    }
    if (result.modified.length > 10) {
      lines.push(`  ... and ${String(result.modified.length - 10)} more`);
    }
  }

  if (result.removed.length > 0) {
    lines.push(`\nFiles to remove (${String(result.removed.length)}):`);
    for (const f of result.removed.slice(0, 10)) {
      lines.push(`  - ${f}`);
    }
    if (result.removed.length > 10) {
      lines.push(`  ... and ${String(result.removed.length - 10)} more`);
    }
  }

  lines.push(`\nUnchanged: ${String(result.unchanged)} files`);

  if (
    result.added.length === 0 &&
    result.modified.length === 0 &&
    result.removed.length === 0
  ) {
    return "Index is up to date - no changes detected.";
  }

  lines.push("\nRun without --dryRun to apply changes.");

  return lines.join("\n");
}

/**
 * Build message for actual update
 */
function buildResultMessage(result: UpdateResult): string {
  const changes =
    result.added.length + result.modified.length + result.removed.length;

  if (changes === 0) {
    return "Index is up to date - no changes needed.";
  }

  const lines: string[] = ["Index updated successfully:"];

  if (result.added.length > 0) {
    lines.push(`  Added: ${String(result.added.length)} files`);
  }
  if (result.modified.length > 0) {
    lines.push(`  Modified: ${String(result.modified.length)} files`);
  }
  if (result.removed.length > 0) {
    lines.push(`  Removed: ${String(result.removed.length)} files`);
  }
  lines.push(`  Unchanged: ${String(result.unchanged)} files`);

  if (result.errors.length > 0) {
    lines.push(`\nErrors (${String(result.errors.length)}):`);
    for (const err of result.errors.slice(0, 5)) {
      lines.push(`  - ${err}`);
    }
  }

  return lines.join("\n");
}

export const updateIndexFeature: Feature<typeof updateIndexSchema> = {
  name: "update_index",
  description:
    "Refresh the search index after code changes. USE THIS instead of re-indexing - it's fast because it only processes changed files (SHA-256 hash detection). Use dryRun=true to preview changes first.",
  schema: updateIndexSchema,
  execute,
};
