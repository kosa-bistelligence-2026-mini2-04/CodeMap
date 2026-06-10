/**
 * Cross-file context resolution for enriched embeddings
 *
 * Resolves imports and includes relevant symbol definitions from
 * imported files to provide better context for semantic search.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import type { Export, Import, Symbol } from "@core/ast/types";
import { parseCode } from "@core/parser";
import { extractExports, extractSymbols } from "@core/symbols";
import { registerCache } from "@core/utils";
import { logger } from "@utils";

/**
 * Resolved import with source file information
 */
export interface ResolvedImport {
  /** Original import statement */
  import: Import;
  /** Resolved absolute file path (null if unresolved) */
  resolvedPath: string | null;
  /** Exported symbols from the resolved file */
  symbols: Symbol[];
  /** Exports from the resolved file */
  exports: Export[];
}

/**
 * Cross-file context for a chunk
 */
export interface CrossFileContext {
  /** Resolved imports with their definitions */
  resolvedImports: ResolvedImport[];
  /** Summary of imported symbols used */
  importedSymbolsSummary: string;
}

/**
 * Options for cross-file resolution
 */
export interface CrossFileOptions {
  /** Project root directory */
  projectRoot: string;
  /** Path aliases (e.g., {"@core": "src/core"}) */
  pathAliases?: Record<string, string>;
  /** Maximum number of imports to resolve */
  maxImports?: number;
  /** Maximum symbols per imported file */
  maxSymbolsPerFile?: number;
}

/**
 * Cache for resolved file analysis
 */
interface ResolvedFileCache {
  symbols: Symbol[];
  exports: Export[];
}

const resolvedFileCache = new Map<string, ResolvedFileCache | null>();

/**
 * Clear the resolved file cache
 */
export function clearCrossFileCache(): void {
  resolvedFileCache.clear();
}

// Register cache for centralized clearing
registerCache("embeddings:crossFileCache", clearCrossFileCache);

/**
 * Common file extensions to try when resolving imports
 */
const EXTENSIONS = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"];

/**
 * Resolve an import source to an absolute file path
 */
function resolveImportPath(
  importSource: string,
  currentFilePath: string,
  options: CrossFileOptions,
): string | null {
  const { projectRoot, pathAliases = {} } = options;

  // Skip external packages (node_modules)
  if (
    !importSource.startsWith(".") &&
    !importSource.startsWith("@") &&
    !Object.keys(pathAliases).some((alias) => importSource.startsWith(alias))
  ) {
    return null;
  }

  let resolvedPath: string | undefined;

  // Handle path aliases
  for (const [alias, target] of Object.entries(pathAliases)) {
    if (importSource.startsWith(alias)) {
      const relativePart = importSource.slice(alias.length);
      resolvedPath = path.join(projectRoot, target, relativePart);
      break;
    }
  }

  // Handle relative imports
  if (resolvedPath === undefined) {
    if (importSource.startsWith(".")) {
      const currentDir = path.dirname(currentFilePath);
      resolvedPath = path.resolve(currentDir, importSource);
    } else {
      // Unresolved alias or external package
      return null;
    }
  }

  // Try to find the actual file
  // First, check if it's a direct file with extension
  for (const ext of EXTENSIONS) {
    const withExt = resolvedPath + ext;
    if (fs.existsSync(withExt) && fs.statSync(withExt).isFile()) {
      return withExt;
    }
  }

  // Check if the path itself exists and is a file (already has extension)
  if (fs.existsSync(resolvedPath) && fs.statSync(resolvedPath).isFile()) {
    return resolvedPath;
  }

  // Check for index file in directory
  for (const ext of EXTENSIONS) {
    const indexPath = path.join(resolvedPath, `index${ext}`);
    if (fs.existsSync(indexPath) && fs.statSync(indexPath).isFile()) {
      return indexPath;
    }
  }

  return null;
}

/**
 * Analyze a resolved file and extract its symbols
 */
async function analyzeResolvedFile(
  filePath: string,
): Promise<ResolvedFileCache | null> {
  // Check cache
  const cached = resolvedFileCache.get(filePath);
  if (cached !== undefined) {
    return cached;
  }

  try {
    const content = fs.readFileSync(filePath, "utf-8");
    const parseResult = await parseCode(content, { filePath });

    const { symbols } = extractSymbols(
      parseResult.tree,
      parseResult.languageInstance,
      parseResult.language,
    );

    const exports = extractExports(
      parseResult.tree,
      parseResult.languageInstance,
      parseResult.language,
    );

    const result: ResolvedFileCache = { symbols, exports };
    resolvedFileCache.set(filePath, result);
    return result;
  } catch (error) {
    logger.debug(
      `Failed to analyze ${filePath}: ${error instanceof Error ? error.message : String(error)}`,
    );
    resolvedFileCache.set(filePath, null);
    return null;
  }
}

/**
 * Find symbols that match imported names
 */
function findImportedSymbols(
  importStatement: Import,
  symbols: Symbol[],
  exports: Export[],
): Symbol[] {
  const importedNames = new Set<string>();

  // Collect all imported names
  for (const name of importStatement.names) {
    importedNames.add(name.name);
  }

  // If namespace import, include all exported symbols
  if (importStatement.isNamespace) {
    const exportedNames = new Set(exports.map((e) => e.name));
    return symbols.filter((s) => exportedNames.has(s.name));
  }

  // If default import, look for default export
  if (importStatement.isDefault) {
    const defaultExport = exports.find((e) => e.isDefault);
    if (defaultExport) {
      importedNames.add(defaultExport.name);
    }
  }

  // Find matching symbols
  return symbols.filter((s) => importedNames.has(s.name));
}

/**
 * Resolve imports and get cross-file context
 */
export async function resolveCrossFileContext(
  imports: Import[],
  currentFilePath: string,
  options: CrossFileOptions,
): Promise<CrossFileContext> {
  const maxImports = options.maxImports ?? 10;
  const maxSymbolsPerFile = options.maxSymbolsPerFile ?? 5;

  const resolvedImports: ResolvedImport[] = [];

  // Process imports (limited to maxImports)
  for (const imp of imports.slice(0, maxImports)) {
    const resolvedPath = resolveImportPath(
      imp.source,
      currentFilePath,
      options,
    );

    if (!resolvedPath) {
      resolvedImports.push({
        import: imp,
        resolvedPath: null,
        symbols: [],
        exports: [],
      });
      continue;
    }

    const analysis = await analyzeResolvedFile(resolvedPath);

    if (!analysis) {
      resolvedImports.push({
        import: imp,
        resolvedPath,
        symbols: [],
        exports: [],
      });
      continue;
    }

    // Find symbols that match the imported names
    const importedSymbols = findImportedSymbols(
      imp,
      analysis.symbols,
      analysis.exports,
    ).slice(0, maxSymbolsPerFile);

    resolvedImports.push({
      import: imp,
      resolvedPath,
      symbols: importedSymbols,
      exports: analysis.exports,
    });
  }

  // Build summary of imported symbols
  const summary = buildImportedSymbolsSummary(resolvedImports);

  return {
    resolvedImports,
    importedSymbolsSummary: summary,
  };
}

/**
 * Build a summary string of imported symbols for enrichment
 */
function buildImportedSymbolsSummary(
  resolvedImports: ResolvedImport[],
): string {
  const lines: string[] = [];

  for (const resolved of resolvedImports) {
    if (resolved.symbols.length === 0) {
      continue;
    }

    // Group by import source
    const symbolDescriptions = resolved.symbols.map((s) => {
      if (s.signature) {
        return `${s.name}: ${s.signature}`;
      }
      return `${s.name} (${s.type})`;
    });

    if (symbolDescriptions.length > 0) {
      lines.push(
        `From ${resolved.import.source}: ${symbolDescriptions.join("; ")}`,
      );
    }
  }

  return lines.join("\n");
}

/**
 * Get cross-file cache statistics
 */
export function getCrossFileCacheStats(): {
  files: number;
  entries: string[];
} {
  return {
    files: resolvedFileCache.size,
    entries: Array.from(resolvedFileCache.keys()),
  };
}
