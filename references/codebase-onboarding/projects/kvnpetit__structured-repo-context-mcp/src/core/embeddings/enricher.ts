/**
 * Chunk enrichment module for better embeddings
 *
 * Enriches code chunks with semantic metadata (symbols, imports, exports)
 * and cross-file context (resolved import definitions) to improve
 * embedding quality for semantic search.
 *
 * Pipeline:
 *   File → chunkFile() → CodeChunk[] → enrichChunks() → EnrichedChunk[]
 *                                                           ↓
 *                                              embedBatch(enrichedContent)
 */

import type { Export, Import, Symbol } from "@core/ast/types";
import { parseCode, type ParseResult } from "@core/parser";
import { extractExports, extractImports, extractSymbols } from "@core/symbols";
import { registerCache } from "@core/utils";
import { logger } from "@utils";
import { ENRICHMENT_CONFIG } from "@config";

import type { ChunkSymbol, CodeChunk, EnrichedChunk } from "./types";
import {
  resolveCrossFileContext,
  type CrossFileContext,
  type CrossFileOptions,
} from "./crossfile";

/**
 * Cached file analysis result
 */
interface FileAnalysisCache {
  parseResult: ParseResult;
  symbols: Symbol[];
  imports: Import[];
  exports: Export[];
  crossFileContext?: CrossFileContext;
}

/**
 * Options for enrichment
 */
export interface EnrichmentOptions {
  /** Project root directory for cross-file resolution */
  projectRoot?: string;
  /** Path aliases (e.g., {"@core": "src/core"}) */
  pathAliases?: Record<string, string>;
  /** Whether to include cross-file context (default: from config) */
  includeCrossFileContext?: boolean;
}

/**
 * AST cache per file path to avoid re-parsing
 */
const astCache = new Map<string, FileAnalysisCache>();

/**
 * Clear the AST cache
 */
export function clearASTCache(): void {
  astCache.clear();
}

// Register cache for centralized clearing
registerCache("embeddings:astCache", clearASTCache);

/** Maximum number of imports to include in enriched content */
const MAX_IMPORTS = 10;

/** Maximum number of exports to include in enriched content */
const MAX_EXPORTS = 10;

/**
 * Get or create file analysis from cache
 */
async function getFileAnalysis(
  filePath: string,
  content: string,
  options?: EnrichmentOptions,
): Promise<FileAnalysisCache | null> {
  // Check cache first
  const cached = astCache.get(filePath);
  if (cached) {
    return cached;
  }

  try {
    // Parse the file
    const parseResult = await parseCode(content, { filePath });

    // Extract symbols, imports, and exports
    const { symbols } = extractSymbols(
      parseResult.tree,
      parseResult.languageInstance,
      parseResult.language,
    );
    const imports = extractImports(
      parseResult.tree,
      parseResult.languageInstance,
      parseResult.language,
    );
    const exports = extractExports(
      parseResult.tree,
      parseResult.languageInstance,
      parseResult.language,
    );

    const analysis: FileAnalysisCache = {
      parseResult,
      symbols,
      imports,
      exports,
    };

    // Resolve cross-file context if enabled
    const shouldIncludeCrossFile =
      options?.includeCrossFileContext ??
      ENRICHMENT_CONFIG.includeCrossFileContext;

    if (shouldIncludeCrossFile && imports.length > 0 && options?.projectRoot) {
      try {
        const crossFileOptions: CrossFileOptions = {
          projectRoot: options.projectRoot,
          pathAliases: options.pathAliases,
          maxImports: ENRICHMENT_CONFIG.maxImportsToResolve,
          maxSymbolsPerFile: ENRICHMENT_CONFIG.maxSymbolsPerImport,
        };

        const crossFileContext = await resolveCrossFileContext(
          imports,
          filePath,
          crossFileOptions,
        );

        analysis.crossFileContext = crossFileContext;
        logger.debug(
          `Resolved cross-file context for ${filePath}: ${String(crossFileContext.resolvedImports.length)} imports`,
        );
      } catch (error) {
        logger.debug(
          `Failed to resolve cross-file context for ${filePath}: ${error instanceof Error ? error.message : String(error)}`,
        );
      }
    }

    // Cache for future chunks from same file
    astCache.set(filePath, analysis);

    return analysis;
  } catch (error) {
    logger.debug(
      `Failed to parse ${filePath}: ${error instanceof Error ? error.message : String(error)}`,
    );
    return null;
  }
}

/**
 * Find symbols that overlap with a chunk's line range
 */
function findSymbolsInRange(
  symbols: Symbol[],
  startLine: number,
  endLine: number,
): ChunkSymbol[] {
  const chunkSymbols: ChunkSymbol[] = [];

  for (const symbol of symbols) {
    // Check if symbol overlaps with chunk's line range
    const symbolStart = symbol.start.line;
    const symbolEnd = symbol.end.line;

    // Symbol overlaps if it starts before chunk ends AND ends after chunk starts
    if (symbolStart <= endLine && symbolEnd >= startLine) {
      chunkSymbols.push({
        name: symbol.name,
        type: symbol.type,
        signature: symbol.signature,
      });
    }
  }

  return chunkSymbols;
}

/**
 * Format import sources for enrichment header
 */
function formatImportSources(imports: Import[]): string {
  const sources = imports
    .slice(0, MAX_IMPORTS)
    .map((imp) => imp.source)
    .filter((source) => source.length > 0);

  return sources.join(", ");
}

/**
 * Format export names for enrichment header
 */
function formatExportNames(exports: Export[]): string {
  const names = exports
    .slice(0, MAX_EXPORTS)
    .map((exp) => exp.name)
    .filter((name) => name.length > 0 && name !== "default");

  return names.join(", ");
}

/**
 * Format symbols for enrichment header
 */
function formatSymbols(symbols: ChunkSymbol[]): string {
  return symbols.map((s) => `${s.name} (${s.type})`).join(", ");
}

/**
 * Build enriched content with metadata header
 */
function buildEnrichedContent(
  chunk: CodeChunk,
  symbols: ChunkSymbol[],
  imports: Import[],
  exports: Export[],
  crossFileContext?: CrossFileContext,
): string {
  const headerLines: string[] = [];

  // Always include file path
  headerLines.push(`File: ${chunk.filePath}`);

  // Always include language
  headerLines.push(`Language: ${chunk.language}`);

  // Include symbols if present
  if (symbols.length > 0) {
    headerLines.push(`Symbols: ${formatSymbols(symbols)}`);
  }

  // Include imports if present
  if (imports.length > 0) {
    const importStr = formatImportSources(imports);
    if (importStr.length > 0) {
      headerLines.push(`Imports: ${importStr}`);
    }
  }

  // Include exports if present
  if (exports.length > 0) {
    const exportStr = formatExportNames(exports);
    if (exportStr.length > 0) {
      headerLines.push(`Exports: ${exportStr}`);
    }
  }

  // Include cross-file context (resolved import definitions)
  if (crossFileContext && crossFileContext.importedSymbolsSummary.length > 0) {
    headerLines.push(
      `Imported definitions:\n${crossFileContext.importedSymbolsSummary}`,
    );
  }

  // Always have header with at least file path and language
  return headerLines.join("\n") + "\n\n---\n" + chunk.content;
}

/**
 * Enrich a single chunk with semantic metadata
 *
 * Note: For multiple chunks from the same file, use `enrichChunksFromFile`
 * which is more efficient as it parses the file only once.
 */
export async function enrichChunk(
  chunk: CodeChunk,
  content: string,
  options?: EnrichmentOptions,
): Promise<EnrichedChunk> {
  const analysis = await getFileAnalysis(chunk.filePath, content, options);

  if (!analysis) {
    // Fallback: return with basic enrichment (file path and language only)
    const basicHeader = `File: ${chunk.filePath}\nLanguage: ${chunk.language}\n\n---\n`;
    return {
      ...chunk,
      enrichedContent: basicHeader + chunk.content,
      containedSymbols: [],
      wasEnriched: false,
    };
  }

  // Find symbols in this chunk's range
  const chunkSymbols = findSymbolsInRange(
    analysis.symbols,
    chunk.startLine,
    chunk.endLine,
  );

  // Build enriched content with cross-file context
  const enrichedContent = buildEnrichedContent(
    chunk,
    chunkSymbols,
    analysis.imports,
    analysis.exports,
    analysis.crossFileContext,
  );

  return {
    ...chunk,
    enrichedContent,
    containedSymbols: chunkSymbols,
    wasEnriched: true,
  };
}

/**
 * Enrich all chunks from a single file (optimized - parses once)
 */
export async function enrichChunksFromFile(
  chunks: CodeChunk[],
  content: string,
  options?: EnrichmentOptions,
): Promise<EnrichedChunk[]> {
  if (chunks.length === 0) {
    return [];
  }

  // All chunks should be from the same file
  const filePath = chunks[0]?.filePath;
  if (!filePath) {
    return chunks.map((chunk) => {
      const basicHeader = `File: ${chunk.filePath}\nLanguage: ${chunk.language}\n\n---\n`;
      return {
        ...chunk,
        enrichedContent: basicHeader + chunk.content,
        containedSymbols: [],
        wasEnriched: false,
      };
    });
  }

  // Parse once for all chunks
  const analysis = await getFileAnalysis(filePath, content, options);

  if (!analysis) {
    // Fallback: return with basic enrichment
    return chunks.map((chunk) => {
      const basicHeader = `File: ${chunk.filePath}\nLanguage: ${chunk.language}\n\n---\n`;
      return {
        ...chunk,
        enrichedContent: basicHeader + chunk.content,
        containedSymbols: [],
        wasEnriched: false,
      };
    });
  }

  // Enrich each chunk using the cached analysis with cross-file context
  return chunks.map((chunk) => {
    const chunkSymbols = findSymbolsInRange(
      analysis.symbols,
      chunk.startLine,
      chunk.endLine,
    );

    const enrichedContent = buildEnrichedContent(
      chunk,
      chunkSymbols,
      analysis.imports,
      analysis.exports,
      analysis.crossFileContext,
    );

    return {
      ...chunk,
      enrichedContent,
      containedSymbols: chunkSymbols,
      wasEnriched: true,
    };
  });
}

/**
 * Enrich chunks from multiple files
 *
 * Groups chunks by file path for efficient processing.
 */
export async function enrichChunks(
  chunks: CodeChunk[],
  fileContents: Map<string, string>,
  options?: EnrichmentOptions,
): Promise<EnrichedChunk[]> {
  // Group chunks by file path
  const chunksByFile = new Map<string, CodeChunk[]>();
  for (const chunk of chunks) {
    const existing = chunksByFile.get(chunk.filePath) ?? [];
    existing.push(chunk);
    chunksByFile.set(chunk.filePath, existing);
  }

  // Process each file's chunks
  const enrichedByFile = new Map<string, EnrichedChunk[]>();

  for (const [filePath, fileChunks] of chunksByFile) {
    const content = fileContents.get(filePath);
    if (!content) {
      // No content available, return with basic enrichment
      enrichedByFile.set(
        filePath,
        fileChunks.map((chunk) => {
          const basicHeader = `File: ${chunk.filePath}\nLanguage: ${chunk.language}\n\n---\n`;
          return {
            ...chunk,
            enrichedContent: basicHeader + chunk.content,
            containedSymbols: [],
            wasEnriched: false,
          };
        }),
      );
      continue;
    }

    const enriched = await enrichChunksFromFile(fileChunks, content, options);
    enrichedByFile.set(filePath, enriched);
  }

  // Reconstruct in original order
  return chunks.map((chunk) => {
    const fileEnriched = enrichedByFile.get(chunk.filePath);
    if (!fileEnriched) {
      const basicHeader = `File: ${chunk.filePath}\nLanguage: ${chunk.language}\n\n---\n`;
      return {
        ...chunk,
        enrichedContent: basicHeader + chunk.content,
        containedSymbols: [],
        wasEnriched: false,
      };
    }

    // Find matching enriched chunk by id
    const enriched = fileEnriched.find((e) => e.id === chunk.id);
    if (enriched) {
      return enriched;
    }

    const basicHeader = `File: ${chunk.filePath}\nLanguage: ${chunk.language}\n\n---\n`;
    return {
      ...chunk,
      enrichedContent: basicHeader + chunk.content,
      containedSymbols: [],
      wasEnriched: false,
    };
  });
}

/**
 * Get cache statistics
 */
export function getASTCacheStats(): { files: number; entries: string[] } {
  return {
    files: astCache.size,
    entries: Array.from(astCache.keys()),
  };
}
