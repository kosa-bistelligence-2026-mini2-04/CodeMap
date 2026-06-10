/**
 * Get Index Status Feature
 *
 * Returns information about the embedding index for a directory:
 * - Whether an index exists
 * - Total chunks and files indexed
 * - Language breakdown
 */

import { z } from "zod";
import * as fs from "node:fs";
import * as path from "node:path";
import type { Feature, FeatureResult } from "@features/types";
import { EMBEDDING_CONFIG } from "@config";
import {
  createVectorStore,
  getIndexPath,
  type IndexStatus,
} from "@core/embeddings";

export const getIndexStatusSchema = z.object({
  directory: z
    .string()
    .optional()
    .default(".")
    .describe("Path to the directory to check (defaults to current directory)"),
});

export type GetIndexStatusInput = z.infer<typeof getIndexStatusSchema>;

/**
 * Execute the get_index_status feature
 */
export async function execute(
  input: GetIndexStatusInput,
): Promise<FeatureResult> {
  const { directory } = input;

  // Validate directory exists
  if (!fs.existsSync(directory)) {
    return {
      success: false,
      error: `Directory not found: ${directory}`,
    };
  }

  const absoluteDir = path.resolve(directory);
  const indexPath = getIndexPath(absoluteDir);

  // Check if index exists
  if (!fs.existsSync(indexPath)) {
    const status: IndexStatus = {
      directory: absoluteDir,
      indexPath,
      exists: false,
      totalChunks: 0,
      totalFiles: 0,
      languages: {},
    };

    return {
      success: true,
      message: `No index found for ${absoluteDir}. Run index_codebase to create one.`,
      data: status,
    };
  }

  try {
    const vectorStore = createVectorStore(absoluteDir, EMBEDDING_CONFIG);
    await vectorStore.connect();

    const status = await vectorStore.getStatus(absoluteDir);
    vectorStore.close();

    // Format language breakdown
    const languageLines = Object.entries(status.languages)
      .sort(([, a], [, b]) => b - a)
      .map(([lang, count]) => `  - ${lang}: ${String(count)} chunks`);

    const message = [
      `Index Status for ${absoluteDir}`,
      ``,
      `Index Path: ${status.indexPath}`,
      `Total Files: ${String(status.totalFiles)}`,
      `Total Chunks: ${String(status.totalChunks)}`,
      ``,
      `Languages:`,
      ...languageLines,
    ].join("\n");

    return {
      success: true,
      message,
      data: status,
    };
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    return {
      success: false,
      error: `Failed to read index status: ${errorMsg}`,
    };
  }
}

export const getIndexStatusFeature: Feature<typeof getIndexStatusSchema> = {
  name: "get_index_status",
  description:
    "Check if a codebase is indexed and ready for search. USE THIS to verify index exists before searching. Returns file count, chunk count, and indexed languages.",
  schema: getIndexStatusSchema,
  execute,
};
