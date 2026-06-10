/**
 * Code chunker for splitting source files into embeddable chunks
 *
 * Uses tree-sitter for semantic chunking based on symbols (functions, classes, etc.)
 * This produces much better embeddings than character-based splitting.
 */

import * as crypto from "node:crypto";
import type { Symbol } from "@core/ast/types";
import { parseCode } from "@core/parser";
import { extractSymbols } from "@core/symbols";
import { logger } from "@utils";

import type { CodeChunk, EmbeddingConfig } from "./types";

/**
 * Generate a unique ID for a chunk
 */
function generateChunkId(
  filePath: string,
  content: string,
  startLine: number,
): string {
  const hash = crypto
    .createHash("md5")
    .update(`${filePath}:${String(startLine)}:${content}`)
    .digest("hex")
    .slice(0, 12);
  return `chunk_${hash}`;
}

/**
 * Detect language from file extension
 */
export function detectLanguage(filePath: string): string {
  const ext = filePath.split(".").pop()?.toLowerCase() ?? "";

  const extensionMap: Record<string, string> = {
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    mjs: "javascript",
    cjs: "javascript",
    py: "python",
    rs: "rust",
    go: "go",
    java: "java",
    kt: "kotlin",
    rb: "ruby",
    php: "php",
    c: "c",
    cpp: "cpp",
    h: "c",
    hpp: "cpp",
    cs: "csharp",
    swift: "swift",
    scala: "scala",
    vue: "vue",
    svelte: "svelte",
    md: "markdown",
    json: "json",
    yaml: "yaml",
    yml: "yaml",
    toml: "toml",
    xml: "xml",
    html: "html",
    css: "css",
    scss: "scss",
    less: "less",
    sql: "sql",
    sh: "bash",
    bash: "bash",
    zsh: "bash",
  };

  return extensionMap[ext] ?? "unknown";
}

/**
 * Get line number from byte offset
 */
function getLineFromOffset(content: string, offset: number): number {
  const before = content.slice(0, offset);
  return (before.match(/\n/g) ?? []).length + 1;
}

/**
 * Extract code content for a symbol using its offsets
 */
function getSymbolContent(content: string, symbol: Symbol): string {
  return content.slice(symbol.start.offset, symbol.end.offset);
}

/**
 * Split large content into smaller chunks while respecting line boundaries
 */
function splitLargeContent(
  content: string,
  maxSize: number,
  overlap: number,
): string[] {
  // Normalize line endings (handle CRLF and CR)
  const normalizedContent = content.replace(/\r\n/g, "\n").replace(/\r/g, "\n");

  if (normalizedContent.length <= maxSize) {
    return [normalizedContent];
  }

  const chunks: string[] = [];
  const lines = normalizedContent.split("\n");
  let currentChunk: string[] = [];
  let currentSize = 0;

  for (const line of lines) {
    const lineSize = line.length + 1; // +1 for newline

    if (currentSize + lineSize > maxSize && currentChunk.length > 0) {
      chunks.push(currentChunk.join("\n"));

      // Keep overlap lines
      const overlapLines: string[] = [];
      let overlapSize = 0;
      for (
        let i = currentChunk.length - 1;
        i >= 0 && overlapSize < overlap;
        i--
      ) {
        const l = currentChunk[i];
        if (l !== undefined) {
          overlapLines.unshift(l);
          overlapSize += l.length + 1;
        }
      }
      currentChunk = overlapLines;
      currentSize = overlapSize;
    }

    currentChunk.push(line);
    currentSize += lineSize;
  }

  if (currentChunk.length > 0) {
    chunks.push(currentChunk.join("\n"));
  }

  return chunks;
}

/**
 * Create a chunk from content
 */
function createChunk(
  filePath: string,
  language: string,
  content: string,
  startLine: number,
  endLine: number,
  symbolName?: string,
  symbolType?: string,
): CodeChunk {
  return {
    id: generateChunkId(filePath, content, startLine),
    content,
    filePath,
    language,
    startLine,
    endLine,
    symbolName,
    symbolType,
  };
}

/**
 * Group consecutive small items (imports, constants, types) into a single chunk
 */
interface ContentRegion {
  content: string;
  startOffset: number;
  endOffset: number;
  startLine: number;
  endLine: number;
  symbolName?: string;
  symbolType?: string;
}

/**
 * Chunk a source file using tree-sitter for semantic boundaries
 *
 * Strategy:
 * 1. Parse file with tree-sitter and extract symbols
 * 2. Each function/class/method becomes its own chunk
 * 3. Code between symbols (imports, top-level code) is grouped together
 * 4. Large symbols are split at line boundaries if they exceed maxSize
 */
export async function chunkFile(
  filePath: string,
  content: string,
  config: Pick<EmbeddingConfig, "defaultChunkSize" | "defaultChunkOverlap">,
): Promise<CodeChunk[]> {
  const language = detectLanguage(filePath);
  const maxSize = config.defaultChunkSize;
  const overlap = config.defaultChunkOverlap;

  // Try to parse with tree-sitter
  let symbols: Symbol[] = [];
  try {
    const parseResult = await parseCode(content, { filePath });
    const result = extractSymbols(
      parseResult.tree,
      parseResult.languageInstance,
      parseResult.language,
    );
    symbols = result.symbols;
  } catch (error) {
    logger.debug(
      `Tree-sitter parsing failed for ${filePath}, using fallback chunking: ${
        error instanceof Error ? error.message : String(error)
      }`,
    );
    // Fallback to simple line-based chunking
    return fallbackChunk(filePath, content, language, maxSize, overlap);
  }

  // If no symbols found, use fallback
  if (symbols.length === 0) {
    return fallbackChunk(filePath, content, language, maxSize, overlap);
  }

  // Sort symbols by start offset
  const sortedSymbols = [...symbols].sort(
    (a, b) => a.start.offset - b.start.offset,
  );

  // Build regions: symbols + gaps between them
  const regions: ContentRegion[] = [];
  let lastEndOffset = 0;

  for (const symbol of sortedSymbols) {
    // Add gap before this symbol (if any significant content)
    if (symbol.start.offset > lastEndOffset) {
      const gapContent = content
        .slice(lastEndOffset, symbol.start.offset)
        .trim();
      if (gapContent.length > 0) {
        regions.push({
          content: content.slice(lastEndOffset, symbol.start.offset),
          startOffset: lastEndOffset,
          endOffset: symbol.start.offset,
          startLine: getLineFromOffset(content, lastEndOffset),
          endLine: getLineFromOffset(content, symbol.start.offset),
        });
      }
    }

    // Add symbol region
    const symbolContent = getSymbolContent(content, symbol);
    regions.push({
      content: symbolContent,
      startOffset: symbol.start.offset,
      endOffset: symbol.end.offset,
      startLine: symbol.start.line,
      endLine: symbol.end.line,
      symbolName: symbol.name,
      symbolType: symbol.type,
    });

    lastEndOffset = Math.max(lastEndOffset, symbol.end.offset);
  }

  // Add trailing content after last symbol
  if (lastEndOffset < content.length) {
    const trailingContent = content.slice(lastEndOffset).trim();
    if (trailingContent.length > 0) {
      regions.push({
        content: content.slice(lastEndOffset),
        startOffset: lastEndOffset,
        endOffset: content.length,
        startLine: getLineFromOffset(content, lastEndOffset),
        endLine: getLineFromOffset(content, content.length),
      });
    }
  }

  // Convert regions to chunks, splitting large ones
  const chunks: CodeChunk[] = [];

  for (const region of regions) {
    const regionContent = region.content.trim();
    if (regionContent.length === 0) {
      continue;
    }

    if (regionContent.length <= maxSize) {
      // Small enough, create single chunk
      chunks.push(
        createChunk(
          filePath,
          language,
          regionContent,
          region.startLine,
          region.endLine,
          region.symbolName,
          region.symbolType,
        ),
      );
    } else {
      // Too large, split it
      const parts = splitLargeContent(regionContent, maxSize, overlap);
      let currentLine = region.startLine;

      for (const part of parts) {
        const partLines = (part.match(/\n/g) ?? []).length + 1;
        chunks.push(
          createChunk(
            filePath,
            language,
            part,
            currentLine,
            currentLine + partLines - 1,
            region.symbolName,
            region.symbolType,
          ),
        );
        currentLine += partLines - Math.floor(overlap / 50); // Approximate line overlap
      }
    }
  }

  return chunks;
}

/**
 * Fallback chunking when tree-sitter fails or finds no symbols
 * Uses simple line-based splitting
 */
function fallbackChunk(
  filePath: string,
  content: string,
  language: string,
  maxSize: number,
  overlap: number,
): CodeChunk[] {
  // Handle empty content
  if (content.trim().length === 0) {
    return [];
  }

  const chunks: CodeChunk[] = [];
  const parts = splitLargeContent(content, maxSize, overlap);

  let currentLine = 1;
  for (const part of parts) {
    const partLines = (part.match(/\n/g) ?? []).length + 1;
    chunks.push(
      createChunk(
        filePath,
        language,
        part,
        currentLine,
        currentLine + partLines - 1,
      ),
    );
    currentLine += partLines - Math.floor(overlap / 50);
  }

  return chunks;
}

/**
 * Chunk multiple files
 */
export async function chunkFiles(
  files: { path: string; content: string }[],
  config: Pick<EmbeddingConfig, "defaultChunkSize" | "defaultChunkOverlap">,
): Promise<CodeChunk[]> {
  const allChunks: CodeChunk[] = [];

  for (const file of files) {
    const chunks = await chunkFile(file.path, file.content, config);
    allChunks.push(...chunks);
  }

  return allChunks;
}

/**
 * Supported file extensions for indexing
 */
export const SUPPORTED_EXTENSIONS = [
  ".ts",
  ".tsx",
  ".js",
  ".jsx",
  ".mjs",
  ".cjs",
  ".py",
  ".rs",
  ".go",
  ".java",
  ".kt",
  ".rb",
  ".php",
  ".c",
  ".cpp",
  ".h",
  ".hpp",
  ".cs",
  ".swift",
  ".scala",
  ".vue",
  ".svelte",
  ".md",
];

/**
 * Check if a file should be indexed
 */
export function shouldIndexFile(filePath: string): boolean {
  const ext = "." + (filePath.split(".").pop()?.toLowerCase() ?? "");
  return SUPPORTED_EXTENSIONS.includes(ext);
}
