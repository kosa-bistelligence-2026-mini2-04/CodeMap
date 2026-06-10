/**
 * Tree-sitter parser module
 *
 * Provides code parsing functionality using web-tree-sitter
 * WASM files are loaded from local assets directory for minimal bundle size
 */
import { existsSync } from "fs";
import { join } from "path";

import {
  Language,
  type Node,
  Parser,
  type Point,
  type Tree,
} from "web-tree-sitter";

import type { ASTNode, Position } from "@core/ast/types";
import { getAssetsDir, registerCache } from "@core/utils";

import {
  getLanguageByName,
  getLanguageFromPath,
  type LanguageConfig,
} from "./languages";

// Re-export language utilities
export * from "./languages";

// Re-export types for external use
export type { Language, Node, Point, Tree };

/**
 * Parser initialization state
 */
let isInitialized = false;
let initPromise: Promise<void> | null = null;

/**
 * Cache for loaded languages
 */
const languageCache = new Map<string, Language>();

/**
 * Parser instance (reused)
 */
let parser: Parser | null = null;

/**
 * Initialize the Tree-sitter WASM module
 * Must be called before any parsing operations
 */
export async function initializeParser(): Promise<void> {
  if (isInitialized) {
    return;
  }

  if (initPromise) {
    return initPromise;
  }

  initPromise = (async () => {
    // web-tree-sitter loads its WASM from node_modules automatically
    await Parser.init();
    parser = new Parser();
    isInitialized = true;
  })();

  return initPromise;
}

/**
 * Check if the parser is initialized
 */
export function isParserInitialized(): boolean {
  return isInitialized;
}

/**
 * Get or create a parser instance
 */
async function getParser(): Promise<Parser> {
  await initializeParser();
  if (!parser) {
    throw new Error("Parser not initialized");
  }
  return parser;
}

/**
 * Load a language grammar from local assets
 */
async function loadLanguage(config: LanguageConfig): Promise<Language> {
  const cacheKey = config.name;

  // Check cache first
  const cached = languageCache.get(cacheKey);
  if (cached) {
    return cached;
  }

  await initializeParser();

  // Load WASM from local assets directory
  const assetsDir = getAssetsDir();
  const wasmPath = join(assetsDir, "wasm", `tree-sitter-${config.name}.wasm`);

  if (!existsSync(wasmPath)) {
    throw new Error(
      `WASM file not found for language ${config.name}: ${wasmPath}`,
    );
  }

  const language = await Language.load(wasmPath);
  languageCache.set(cacheKey, language);

  return language;
}

/**
 * Parse result
 */
export interface ParseResult {
  /** The Tree-sitter tree */
  tree: Tree;
  /** Language that was used */
  language: string;
  /** The parser instance (for queries) */
  parser: Parser;
  /** The language instance (for queries) */
  languageInstance: Language;
}

/**
 * Parse options
 */
export interface ParseOptions {
  /** Language name (auto-detected from file path if not provided) */
  language?: string;
  /** File path (for language detection) */
  filePath?: string;
}

/**
 * Parse code content
 */
export async function parseCode(
  content: string,
  options: ParseOptions = {},
): Promise<ParseResult> {
  const { language, filePath } = options;

  // Determine language config
  let config: LanguageConfig | undefined;

  if (language) {
    config = getLanguageByName(language);
    if (!config) {
      throw new Error(`Unsupported language: ${language}`);
    }
  } else if (filePath) {
    config = getLanguageFromPath(filePath);
    if (!config) {
      throw new Error(`Could not detect language for file: ${filePath}`);
    }
  } else {
    throw new Error("Either language or filePath must be provided");
  }

  // Load the language grammar
  const languageInstance = await loadLanguage(config);

  // Get parser and set language
  const parserInstance = await getParser();
  parserInstance.setLanguage(languageInstance);

  // Parse the content
  const tree = parserInstance.parse(content);

  if (!tree) {
    throw new Error("Failed to parse content");
  }

  return {
    tree,
    language: config.name,
    parser: parserInstance,
    languageInstance,
  };
}

/**
 * Convert Tree-sitter position to our Position type
 */
export function toPosition(point: Point, offset: number): Position {
  return {
    line: point.row + 1, // Convert 0-based to 1-based
    column: point.column,
    offset,
  };
}

/**
 * Convert Tree-sitter node to ASTNode
 */
export function toASTNode(
  node: Node,
  maxDepth?: number,
  currentDepth = 0,
): ASTNode {
  const astNode: ASTNode = {
    type: node.type,
    text: node.text,
    start: toPosition(node.startPosition, node.startIndex),
    end: toPosition(node.endPosition, node.endIndex),
    isNamed: node.isNamed,
  };

  // Check depth limit
  if (maxDepth !== undefined && currentDepth >= maxDepth) {
    return astNode;
  }

  // Add children if present
  if (node.childCount > 0) {
    const namedChildren = node.namedChildren;
    if (namedChildren.length > 0) {
      astNode.children = namedChildren.map((child) =>
        toASTNode(child, maxDepth, currentDepth + 1),
      );
    }
  }

  // Add named fields using the language's field names
  const treeLang = node.tree.language;
  const fields: Record<string, ASTNode | ASTNode[]> = {};
  const langFields = treeLang.fields;

  for (const fieldName of langFields) {
    if (fieldName) {
      const fieldNode = node.childForFieldName(fieldName);
      if (fieldNode) {
        fields[fieldName] = toASTNode(fieldNode, maxDepth, currentDepth + 1);
      }
    }
  }

  if (Object.keys(fields).length > 0) {
    astNode.fields = fields;
  }

  return astNode;
}

/**
 * Get the root ASTNode from a parse result
 */
export function getASTRoot(
  parseResult: ParseResult,
  maxDepth?: number,
): ASTNode {
  return toASTNode(parseResult.tree.rootNode, maxDepth);
}

/**
 * Count nodes in the tree
 */
export function countNodes(node: Node): number {
  let count = 1;
  for (const child of node.namedChildren) {
    count += countNodes(child);
  }
  return count;
}

/**
 * Clear the language cache (useful for testing)
 */
export function clearLanguageCache(): void {
  languageCache.clear();
}

/**
 * Reset the parser state (useful for testing)
 */
export function resetParser(): void {
  languageCache.clear();
  parser = null;
  isInitialized = false;
  initPromise = null;
}

// Register caches for centralized clearing
registerCache("parser:languageCache", clearLanguageCache);
registerCache("parser:state", resetParser);
