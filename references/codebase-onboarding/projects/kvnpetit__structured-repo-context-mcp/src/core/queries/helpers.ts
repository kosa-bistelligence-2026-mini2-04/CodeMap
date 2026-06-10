/**
 * Query helper utilities
 *
 * Provides common patterns for working with Tree-sitter query captures
 */
import type { ASTNode, QueryCapture, QueryMatch } from "@core/ast/types";

/**
 * Find a capture by exact name
 *
 * @param captures - Array of captures from a query match
 * @param name - Exact capture name to find
 * @returns The matching capture or undefined
 */
export function findCapture(
  captures: QueryCapture[],
  name: string,
): QueryCapture | undefined {
  return captures.find((c) => c.name === name);
}

/**
 * Find a capture matching any of the given names
 *
 * @param captures - Array of captures from a query match
 * @param names - Array of capture names to search for
 * @returns The first matching capture or undefined
 */
export function findCaptureByNames(
  captures: QueryCapture[],
  names: string[],
): QueryCapture | undefined {
  return captures.find((c) => names.includes(c.name));
}

/**
 * Find a capture by name prefix
 *
 * @param captures - Array of captures from a query match
 * @param prefix - Prefix to match (e.g., "definition." matches "definition.function")
 * @returns The first matching capture or undefined
 */
export function findCaptureByPrefix(
  captures: QueryCapture[],
  prefix: string,
): QueryCapture | undefined {
  return captures.find((c) => c.name.startsWith(prefix));
}

/**
 * Get all captures matching a prefix
 *
 * @param captures - Array of captures from a query match
 * @param prefix - Prefix to match
 * @returns Array of matching captures
 */
export function filterCapturesByPrefix(
  captures: QueryCapture[],
  prefix: string,
): QueryCapture[] {
  return captures.filter((c) => c.name.startsWith(prefix));
}

/**
 * Extract the suffix from a capture name after the prefix
 *
 * @param captureName - Full capture name (e.g., "definition.function")
 * @param prefix - Prefix to remove (e.g., "definition.")
 * @returns The suffix (e.g., "function") or the original name if prefix not found
 */
export function getCaptureKind(captureName: string, prefix: string): string {
  return captureName.startsWith(prefix)
    ? captureName.slice(prefix.length)
    : captureName;
}

/**
 * Deduplicate nodes from query matches based on their position
 *
 * @param matches - Array of query matches
 * @param captureNames - Capture names to extract nodes from
 * @returns Array of unique ASTNode objects
 */
export function deduplicateNodes(
  matches: QueryMatch[],
  captureNames: string[],
): ASTNode[] {
  const nodes: ASTNode[] = [];
  const seen = new Set<number>();

  for (const match of matches) {
    const capture = findCaptureByNames(match.captures, captureNames);
    if (capture && !seen.has(capture.node.start.offset)) {
      nodes.push(capture.node);
      seen.add(capture.node.start.offset);
    }
  }

  return nodes;
}

/**
 * Extract nodes from matches without deduplication
 *
 * @param matches - Array of query matches
 * @param captureNames - Capture names to extract nodes from
 * @returns Array of ASTNode objects
 */
export function extractNodes(
  matches: QueryMatch[],
  captureNames: string[],
): ASTNode[] {
  const nodes: ASTNode[] = [];

  for (const match of matches) {
    const capture = findCaptureByNames(match.captures, captureNames);
    if (capture) {
      nodes.push(capture.node);
    }
  }

  return nodes;
}

/**
 * Create a deduplication set from node offsets
 *
 * @returns Object with add and has methods for tracking seen offsets
 */
export function createOffsetTracker(): {
  add: (node: ASTNode) => void;
  has: (node: ASTNode) => boolean;
} {
  const seen = new Set<number>();
  return {
    add: (node: ASTNode) => seen.add(node.start.offset),
    has: (node: ASTNode) => seen.has(node.start.offset),
  };
}
