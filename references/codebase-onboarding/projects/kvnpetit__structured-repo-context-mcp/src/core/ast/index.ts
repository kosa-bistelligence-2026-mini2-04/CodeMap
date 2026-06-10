/**
 * AST extraction and traversal utilities
 */
import type { Node } from "web-tree-sitter";

import { toPosition } from "@core/parser";

import type { ASTNode, Position } from "./types";

// Re-export types
export type * from "./types";

/**
 * Traversal callback function type
 */
export type TraversalCallback = (
  node: ASTNode,
  depth: number,
) => boolean | undefined;

/**
 * Traverse AST tree in depth-first order
 * Return false from callback to stop traversal
 */
export function traverseAST(
  node: ASTNode,
  callback: TraversalCallback,
  depth = 0,
): boolean {
  const result = callback(node, depth);
  if (result === false) {
    return false;
  }

  if (node.children) {
    for (const child of node.children) {
      const shouldContinue = traverseAST(child, callback, depth + 1);
      if (!shouldContinue) {
        return false;
      }
    }
  }

  return true;
}

/**
 * Find all nodes matching a predicate
 */
export function findNodes(
  root: ASTNode,
  predicate: (node: ASTNode) => boolean,
): ASTNode[] {
  const matches: ASTNode[] = [];

  traverseAST(root, (node) => {
    if (predicate(node)) {
      matches.push(node);
    }
    return undefined;
  });

  return matches;
}

/**
 * Find all nodes of a specific type
 */
export function findNodesByType(root: ASTNode, type: string): ASTNode[] {
  return findNodes(root, (node) => node.type === type);
}

/**
 * Find all nodes of multiple types
 */
export function findNodesByTypes(root: ASTNode, types: string[]): ASTNode[] {
  const typeSet = new Set(types);
  return findNodes(root, (node) => typeSet.has(node.type));
}

/**
 * Find the first node matching a predicate
 */
export function findFirstNode(
  root: ASTNode,
  predicate: (node: ASTNode) => boolean,
): ASTNode | undefined {
  let found: ASTNode | undefined;

  traverseAST(root, (node) => {
    if (predicate(node)) {
      found = node;
      return false; // Stop traversal
    }
    return true;
  });

  return found;
}

/**
 * Find node at a specific position
 */
export function findNodeAtPosition(
  root: ASTNode,
  line: number,
  column: number,
): ASTNode | undefined {
  let found: ASTNode | undefined;

  traverseAST(root, (node) => {
    const startLine = node.start.line;
    const endLine = node.end.line;
    const startCol = node.start.column;
    const endCol = node.end.column;

    // Check if position is within node range
    const afterStart =
      line > startLine || (line === startLine && column >= startCol);
    const beforeEnd = line < endLine || (line === endLine && column <= endCol);

    if (afterStart && beforeEnd) {
      found = node; // Keep updating to get the most specific (deepest) node
    }
    return true;
  });

  return found;
}

/**
 * Get the path from root to a node
 */
export function getNodePath(
  root: ASTNode,
  target: ASTNode,
): ASTNode[] | undefined {
  const path: ASTNode[] = [];

  function search(node: ASTNode): boolean {
    path.push(node);

    if (
      node.start.offset === target.start.offset &&
      node.end.offset === target.end.offset &&
      node.type === target.type
    ) {
      return true;
    }

    if (node.children) {
      for (const child of node.children) {
        if (search(child)) {
          return true;
        }
      }
    }

    path.pop();
    return false;
  }

  return search(root) ? path : undefined;
}

/**
 * Get all ancestor types from a node to root
 */
export function getAncestorTypes(root: ASTNode, target: ASTNode): string[] {
  const path = getNodePath(root, target);
  return path ? path.map((n) => n.type) : [];
}

/**
 * Extract text from a position range
 */
export function extractText(
  source: string,
  start: Position,
  end: Position,
): string {
  return source.slice(start.offset, end.offset);
}

/**
 * Get line count of source code
 */
export function getLineCount(source: string): number {
  // Normalize line endings (handle CRLF and CR)
  const normalizedSource = source.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  return normalizedSource.split("\n").length;
}

/**
 * Options for AST extraction
 */
export interface ExtractOptions {
  /** Maximum depth to extract (undefined = unlimited) */
  maxDepth?: number;
  /** Include only named nodes */
  namedOnly?: boolean;
  /** Node types to include (undefined = all) */
  includeTypes?: string[];
  /** Node types to exclude */
  excludeTypes?: string[];
}

/**
 * Extract a filtered/limited AST from a Tree-sitter tree
 */
export function extractAST(
  rootNode: Node,
  options: ExtractOptions = {},
): ASTNode {
  const { maxDepth, namedOnly = true, includeTypes, excludeTypes } = options;

  function shouldInclude(node: Node): boolean {
    if (namedOnly && !node.isNamed) {
      return false;
    }
    if (includeTypes && !includeTypes.includes(node.type)) {
      return false;
    }
    if (excludeTypes?.includes(node.type)) {
      return false;
    }
    return true;
  }

  function extract(node: Node, depth: number): ASTNode {
    const astNode: ASTNode = {
      type: node.type,
      text: node.text,
      start: toPosition(node.startPosition, node.startIndex),
      end: toPosition(node.endPosition, node.endIndex),
      isNamed: node.isNamed,
    };

    // Check depth limit
    if (maxDepth !== undefined && depth >= maxDepth) {
      return astNode;
    }

    // Process children
    const children: ASTNode[] = [];
    for (const child of node.namedChildren) {
      if (shouldInclude(child)) {
        children.push(extract(child, depth + 1));
      }
    }

    if (children.length > 0) {
      astNode.children = children;
    }

    return astNode;
  }

  return extract(rootNode, 0);
}

/**
 * Serialize AST to a compact string representation
 */
export function serializeAST(node: ASTNode, indent = 0): string {
  const prefix = "  ".repeat(indent);
  let result = `${prefix}(${node.type}`;

  if (node.children && node.children.length > 0) {
    result += "\n";
    for (const child of node.children) {
      result += serializeAST(child, indent + 1) + "\n";
    }
    result += `${prefix})`;
  } else {
    // Leaf node - show text excerpt
    const text =
      node.text.length > 30 ? node.text.slice(0, 30) + "..." : node.text;
    const escaped = text.replace(/\n/g, "\\n").replace(/"/g, '\\"');
    result += ` "${escaped}")`;
  }

  return result;
}

/**
 * Get statistics about an AST
 */
export interface ASTStats {
  totalNodes: number;
  maxDepth: number;
  nodeTypes: Map<string, number>;
}

export function getASTStats(root: ASTNode): ASTStats {
  const stats: ASTStats = {
    totalNodes: 0,
    maxDepth: 0,
    nodeTypes: new Map(),
  };

  traverseAST(root, (node, depth) => {
    stats.totalNodes++;
    stats.maxDepth = Math.max(stats.maxDepth, depth);
    stats.nodeTypes.set(node.type, (stats.nodeTypes.get(node.type) ?? 0) + 1);
    return true;
  });

  return stats;
}
