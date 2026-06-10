/**
 * Content reading utilities for features
 *
 * Provides consistent file/content handling across features
 */
import { readFileSync } from "fs";

/**
 * Result of reading content
 */
export type ContentResult =
  | { success: true; content: string }
  | { success: false; error: string };

/**
 * Read content from either a file path or direct content string
 *
 * This is a common pattern used by multiple features that accept
 * either a file_path or content parameter.
 *
 * @param filePath - Optional path to file to read
 * @param content - Optional content string
 * @returns ContentResult with either the content or an error message
 */
export function readContent(
  filePath?: string,
  content?: string,
): ContentResult {
  // If content is provided directly, use it
  if (content !== undefined) {
    return { success: true, content };
  }

  // If file path is provided, read it
  if (filePath !== undefined) {
    try {
      const fileContent = readFileSync(filePath, "utf-8");
      return { success: true, content: fileContent };
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return { success: false, error: `Failed to read file: ${message}` };
    }
  }

  // Neither provided
  return {
    success: false,
    error: "Either file_path or content must be provided",
  };
}

/**
 * Require that either filePath or content is provided
 *
 * @param filePath - Optional path to file
 * @param content - Optional content string
 * @returns True if at least one is provided
 */
export function hasContentSource(filePath?: string, content?: string): boolean {
  return filePath !== undefined || content !== undefined;
}
