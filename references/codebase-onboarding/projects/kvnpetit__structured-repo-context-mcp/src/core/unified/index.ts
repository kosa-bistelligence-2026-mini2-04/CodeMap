/**
 * Unified Parser Module
 *
 * Provides a single interface for code parsing with automatic fallback:
 * 1. Tree-sitter (AST parsing) - for supported languages
 * 2. LangChain text splitter - for unsupported languages but known file types
 * 3. Generic text splitting - for any other text files
 */
import { readFileSync } from "fs";
import { extname } from "path";

import type { Language, Tree } from "web-tree-sitter";

import type { ASTNode } from "@core/ast/types";
import {
  isTextSplitterLanguage,
  splitCode,
  type TextChunk,
} from "@core/fallback";
import {
  getASTRoot,
  getLanguageFromPath,
  isLanguageSupported,
  parseCode,
} from "@core/parser";
import {
  extractSymbolsFromTags,
  findClasses,
  findFunctions,
} from "@core/queries";
import {
  DEFAULT_CHUNK_OVERLAP,
  DEFAULT_CHUNK_SIZE,
  SKIP_KEYWORDS,
} from "@core/constants";
import { loadJsonConfig, registerCache } from "@core/utils";

// Centralized config types
interface LanguagesConfig {
  treesitter: Record<
    string,
    {
      wasm: string;
      queries: string;
      extensions: string[];
      aliases?: string[];
    }
  >;
  fallbackExtensions: Record<string, string>;
  specialFilenames: Record<string, string>;
  binaryExtensions: string[];
}

// Config cache
let configCache: LanguagesConfig | null = null;
let binaryExtensionsCache: Set<string> | null = null;
let extensionToLanguageCache: Record<string, string> | null = null;
let specialFilenamesCache: Record<string, string> | null = null;

function loadConfig(): LanguagesConfig {
  if (configCache) {
    return configCache;
  }

  configCache = loadJsonConfig<LanguagesConfig>("languages.json", {
    treesitter: {},
    fallbackExtensions: {},
    specialFilenames: {},
    binaryExtensions: [],
  });
  return configCache;
}

function getBinaryExtensions(): Set<string> {
  if (binaryExtensionsCache) {
    return binaryExtensionsCache;
  }
  const config = loadConfig();
  binaryExtensionsCache = new Set(config.binaryExtensions);
  return binaryExtensionsCache;
}

function getExtensionToLanguage(): Record<string, string> {
  if (extensionToLanguageCache) {
    return extensionToLanguageCache;
  }
  const config = loadConfig();
  extensionToLanguageCache = config.fallbackExtensions;
  return extensionToLanguageCache;
}

function getSpecialFilenames(): Record<string, string> {
  if (specialFilenamesCache) {
    return specialFilenamesCache;
  }
  const config = loadConfig();
  specialFilenamesCache = config.specialFilenames;
  return specialFilenamesCache;
}

/** Clear caches (for testing) */
export function clearUnifiedCache(): void {
  configCache = null;
  binaryExtensionsCache = null;
  extensionToLanguageCache = null;
  specialFilenamesCache = null;
}

/**
 * Unified parse result - works for both Tree-sitter and fallback
 */
export interface UnifiedParseResult {
  /** Parsing method used */
  method: "tree-sitter" | "langchain" | "generic";
  /** Language detected */
  language: string;
  /** File path */
  filePath: string;
  /** Original content */
  content: string;
  /** Line count */
  lineCount: number;

  // Tree-sitter specific (only when method === "tree-sitter")
  /** Tree-sitter tree (if available) */
  tree?: Tree;
  /** Language instance (if available) */
  languageInstance?: Language;
  /** AST root node (if available) */
  ast?: ASTNode;

  // Fallback specific (only when method !== "tree-sitter")
  /** Text chunks (if using fallback) */
  chunks?: TextChunk[];
}

/**
 * Unified symbol extraction result
 */
export interface UnifiedSymbols {
  /** Extraction method used */
  method: "tree-sitter" | "regex";
  /** Functions found */
  functions: UnifiedSymbol[];
  /** Classes found */
  classes: UnifiedSymbol[];
  /** All symbols */
  all: UnifiedSymbol[];
}

/**
 * Unified symbol representation
 */
export interface UnifiedSymbol {
  name: string;
  type: "function" | "method" | "class" | "interface" | "module" | "variable";
  line: number;
  endLine?: number;
  signature?: string;
  documentation?: string;
}

/**
 * Parse options
 */
export interface UnifiedParseOptions {
  /** Force a specific language (skip auto-detection) */
  language?: string;
  /** Include AST in result (Tree-sitter only, can be verbose) */
  includeAst?: boolean;
  /** Max AST depth (Tree-sitter only) */
  astMaxDepth?: number;
  /** Chunk size for fallback splitting */
  chunkSize?: number;
  /** Chunk overlap for fallback splitting */
  chunkOverlap?: number;
}

/**
 * Extract a meaningful name from AST node text, skipping keywords
 */
function extractNameFromNode(text: string): string {
  // Split by common delimiters
  const parts = text.split(/[(\s{<:=[\]]/);

  // Find first non-keyword identifier
  for (const part of parts) {
    const trimmed = part.trim();
    if (
      trimmed &&
      !SKIP_KEYWORDS.has(trimmed.toLowerCase()) &&
      /^[a-zA-Z_]/.test(trimmed)
    ) {
      return trimmed;
    }
  }

  return "anonymous";
}

/**
 * Check if a file is binary based on extension
 */
export function isBinaryFile(filePath: string): boolean {
  const ext = extname(filePath).toLowerCase();
  return getBinaryExtensions().has(ext);
}

/**
 * Detect language from file path (extended detection)
 */
export function detectLanguage(filePath: string): string {
  // First try Tree-sitter supported languages
  const tsConfig = getLanguageFromPath(filePath);
  if (tsConfig) {
    return tsConfig.name;
  }

  // Then try extension mapping from config
  const ext = extname(filePath).toLowerCase();
  const extensionMap = getExtensionToLanguage();
  const mappedLang = extensionMap[ext];
  if (mappedLang) {
    return mappedLang;
  }

  // Check for special filenames from config
  const filename = filePath.split(/[/\\]/).pop()?.toLowerCase() ?? "";
  const specialFilenames = getSpecialFilenames();
  const specialLang = specialFilenames[filename];
  if (specialLang) {
    return specialLang;
  }

  // Check for patterns like .env.local, dockerfile.prod
  if (filename.startsWith(".env.") || filename === ".env") {
    return "env";
  }
  if (filename.startsWith("dockerfile.") || filename === "dockerfile") {
    return "dockerfile";
  }

  return "text";
}

/**
 * Parse a file with automatic fallback
 *
 * 1. If Tree-sitter supports the language → full AST parsing
 * 2. If LangChain supports the language → text splitting with language separators
 * 3. LangChain generic → text splitting with default separators
 * 4. If all fail → returns undefined (file is ignored)
 */
export async function parseFile(
  filePath: string,
  options: UnifiedParseOptions = {},
): Promise<UnifiedParseResult | undefined> {
  // Check for binary files - ignore them
  if (isBinaryFile(filePath)) {
    return undefined;
  }

  // Read file content
  let content: string;
  try {
    const rawContent = readFileSync(filePath, "utf-8");
    // Normalize line endings (handle CRLF and CR)
    content = rawContent.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  } catch {
    // Cannot read file - ignore
    return undefined;
  }

  const lineCount = content.split("\n").length;

  // Detect language
  const language = options.language ?? detectLanguage(filePath);

  // Try Tree-sitter first
  if (isLanguageSupported(language)) {
    try {
      const parseResult = await parseCode(content, { language });

      const result: UnifiedParseResult = {
        method: "tree-sitter",
        language: parseResult.language,
        filePath,
        content,
        lineCount,
        tree: parseResult.tree,
        languageInstance: parseResult.languageInstance,
      };

      // Include AST if requested
      if (options.includeAst) {
        result.ast = getASTRoot(parseResult, options.astMaxDepth);
      }

      return result;
    } catch {
      // Tree-sitter failed, fall through to LangChain
    }
  }

  // Try LangChain with detected language
  const {
    chunkSize = DEFAULT_CHUNK_SIZE,
    chunkOverlap = DEFAULT_CHUNK_OVERLAP,
  } = options;

  if (isTextSplitterLanguage(language)) {
    try {
      const splitResult = await splitCode(content, language, {
        chunkSize,
        chunkOverlap,
      });

      return {
        method: "langchain",
        language,
        filePath,
        content,
        lineCount,
        chunks: splitResult.chunks,
      };
    } catch {
      // LangChain with language failed, try generic
    }
  }

  // Try LangChain generic
  try {
    const splitResult = await splitCode(content, "generic", {
      chunkSize,
      chunkOverlap,
    });

    return {
      method: "generic",
      language,
      filePath,
      content,
      lineCount,
      chunks: splitResult.chunks,
    };
  } catch {
    // All methods failed - ignore file
    return undefined;
  }
}

/**
 * Parse content directly (without file)
 *
 * Returns undefined if content cannot be parsed
 */
export async function parseContent(
  content: string,
  language: string,
  options: Omit<UnifiedParseOptions, "language"> = {},
): Promise<Omit<UnifiedParseResult, "filePath"> | undefined> {
  // Normalize line endings (handle CRLF and CR)
  const normalizedContent = content.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const lineCount = normalizedContent.split("\n").length;

  // Try Tree-sitter first
  if (isLanguageSupported(language)) {
    try {
      const parseResult = await parseCode(content, { language });

      const result: Omit<UnifiedParseResult, "filePath"> = {
        method: "tree-sitter",
        language: parseResult.language,
        content,
        lineCount,
        tree: parseResult.tree,
        languageInstance: parseResult.languageInstance,
      };

      if (options.includeAst) {
        result.ast = getASTRoot(parseResult, options.astMaxDepth);
      }

      return result;
    } catch {
      // Tree-sitter failed, fall through to LangChain
    }
  }

  // Try LangChain with detected language
  const {
    chunkSize = DEFAULT_CHUNK_SIZE,
    chunkOverlap = DEFAULT_CHUNK_OVERLAP,
  } = options;

  if (isTextSplitterLanguage(language)) {
    try {
      const splitResult = await splitCode(content, language, {
        chunkSize,
        chunkOverlap,
      });

      return {
        method: "langchain",
        language,
        content,
        lineCount,
        chunks: splitResult.chunks,
      };
    } catch {
      // LangChain with language failed, try generic
    }
  }

  // Try LangChain generic
  try {
    const splitResult = await splitCode(content, "generic", {
      chunkSize,
      chunkOverlap,
    });

    return {
      method: "generic",
      language,
      content,
      lineCount,
      chunks: splitResult.chunks,
    };
  } catch {
    // All methods failed - ignore
    return undefined;
  }
}

/**
 * Extract symbols with automatic fallback
 *
 * 1. Tree-sitter → accurate AST-based extraction
 * 2. Regex fallback → best-effort pattern matching
 */
export function extractSymbols(result: UnifiedParseResult): UnifiedSymbols {
  // Tree-sitter path
  if (
    result.method === "tree-sitter" &&
    result.tree &&
    result.languageInstance
  ) {
    const { definitions } = extractSymbolsFromTags(
      result.tree,
      result.languageInstance,
      result.language,
    );

    const functions: UnifiedSymbol[] = [];
    const classes: UnifiedSymbol[] = [];
    const all: UnifiedSymbol[] = [];

    for (const def of definitions) {
      const symbol: UnifiedSymbol = {
        name: def.name,
        type: def.kind as UnifiedSymbol["type"],
        line: def.node.start.line,
        endLine: def.node.end.line,
        documentation: def.documentation,
      };

      all.push(symbol);

      if (def.kind === "function" || def.kind === "method") {
        functions.push(symbol);
      } else if (
        def.kind === "class" ||
        def.kind === "interface" ||
        def.kind === "module"
      ) {
        classes.push(symbol);
      }
    }

    // If tags.scm didn't find anything, try direct AST queries
    if (functions.length === 0) {
      const funcNodes = findFunctions(
        result.tree,
        result.languageInstance,
        result.language,
      );
      for (const node of funcNodes) {
        const symbol: UnifiedSymbol = {
          name: extractNameFromNode(node.text),
          type: "function",
          line: node.start.line,
          endLine: node.end.line,
        };
        functions.push(symbol);
        all.push(symbol);
      }
    }

    if (classes.length === 0) {
      const classNodes = findClasses(
        result.tree,
        result.languageInstance,
        result.language,
      );
      for (const node of classNodes) {
        const symbol: UnifiedSymbol = {
          name: extractNameFromNode(node.text),
          type: "class",
          line: node.start.line,
          endLine: node.end.line,
        };
        classes.push(symbol);
        all.push(symbol);
      }
    }

    return { method: "tree-sitter", functions, classes, all };
  }

  // LangChain fallback - no symbol extraction (text splitting only)
  return { method: "regex", functions: [], classes: [], all: [] };
}

/**
 * Get a summary of parsing capabilities for a file
 */
export function getParsingCapabilities(filePath: string): {
  language: string;
  method: "tree-sitter" | "langchain" | "generic";
  features: string[];
} {
  if (isBinaryFile(filePath)) {
    return {
      language: "binary",
      method: "generic",
      features: [],
    };
  }

  const language = detectLanguage(filePath);

  if (isLanguageSupported(language)) {
    return {
      language,
      method: "tree-sitter",
      features: [
        "Full AST parsing",
        "Accurate symbol extraction",
        "Syntax highlighting queries",
        "Code navigation",
        "Semantic analysis",
      ],
    };
  }

  if (isTextSplitterLanguage(language)) {
    return {
      language,
      method: "langchain",
      features: [
        "Intelligent text splitting",
        "Language-aware chunking",
        "Basic symbol extraction (regex)",
      ],
    };
  }

  return {
    language,
    method: "generic",
    features: ["Generic text splitting", "Basic symbol extraction (regex)"],
  };
}

/**
 * Check if a file can be parsed (not binary)
 */
export function canParse(filePath: string): boolean {
  return !isBinaryFile(filePath);
}

/**
 * Get all supported languages with their parsing method
 */
export function getSupportedLanguagesInfo(): {
  language: string;
  method: "tree-sitter" | "langchain";
  extensions: string[];
}[] {
  const result: {
    language: string;
    method: "tree-sitter" | "langchain";
    extensions: string[];
  }[] = [];

  const config = loadConfig();

  // Tree-sitter languages from config
  for (const [name, langConfig] of Object.entries(config.treesitter)) {
    result.push({
      language: name,
      method: "tree-sitter",
      extensions: langConfig.extensions,
    });
  }

  // LangChain languages - group extensions by language from fallbackExtensions
  const langchainExtensions: Record<string, string[]> = {};
  for (const [ext, lang] of Object.entries(config.fallbackExtensions)) {
    // Skip languages already covered by Tree-sitter
    if (config.treesitter[lang]) {
      continue;
    }
    langchainExtensions[lang] ??= [];
    langchainExtensions[lang].push(ext);
  }

  for (const [lang, extensions] of Object.entries(langchainExtensions)) {
    result.push({
      language: lang,
      method: "langchain",
      extensions,
    });
  }

  return result;
}

// Register cache for centralized clearing
registerCache("unified:config", clearUnifiedCache);
