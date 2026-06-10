import { z } from "zod";

import { getASTRoot } from "@core/parser";
import { extractCodeInfo } from "@core/symbols";
import {
  canParse,
  extractSymbols,
  getParsingCapabilities,
  parseFile,
} from "@core/unified";

import type { Feature, FeatureResult } from "@features/types";

export const analyzeFileSchema = z.object({
  file_path: z.string().describe("Path to the file to analyze"),
  include_ast: z
    .boolean()
    .default(false)
    .describe("Include full AST in response (default: false, can be verbose)"),
  include_symbols: z
    .boolean()
    .default(true)
    .describe("Include extracted symbols (default: true)"),
  include_imports: z
    .boolean()
    .default(true)
    .describe("Include import statements (default: true)"),
  include_exports: z
    .boolean()
    .default(true)
    .describe("Include export statements (default: true)"),
  ast_max_depth: z
    .number()
    .int()
    .positive()
    .optional()
    .describe("Maximum depth for AST if included"),
  include_chunks: z
    .boolean()
    .default(false)
    .describe("Include text chunks for fallback parsing (default: false)"),
});

export type AnalyzeFileInput = z.input<typeof analyzeFileSchema>;

export async function execute(
  rawInput: AnalyzeFileInput,
): Promise<FeatureResult> {
  // Parse with defaults applied
  const input = analyzeFileSchema.parse(rawInput);
  const {
    file_path,
    include_ast,
    include_symbols,
    include_imports,
    include_exports,
    ast_max_depth,
    include_chunks,
  } = input;

  try {
    // Check if file can be parsed
    if (!canParse(file_path)) {
      return {
        success: false,
        error: `Cannot parse binary file: ${file_path}`,
      };
    }

    // Get parsing capabilities for this file
    const capabilities = getParsingCapabilities(file_path);

    // Parse the file with automatic fallback
    const parseResult = await parseFile(file_path, {
      includeAst: include_ast,
      astMaxDepth: ast_max_depth,
    });

    // If parsing failed (unsupported file type), return error
    if (!parseResult) {
      return {
        success: false,
        error: `Cannot parse file: ${file_path}. Unsupported or unreadable file type.`,
      };
    }

    // Build response based on parsing method
    const response: Record<string, unknown> = {
      file_path,
      language: parseResult.language,
      parsing_method: parseResult.method,
      capabilities: capabilities.features,
      metrics: {
        lines: parseResult.lineCount,
        functions: 0,
        classes: 0,
        imports: 0,
        exports: 0,
      },
    };

    // Tree-sitter path - full analysis
    if (
      parseResult.method === "tree-sitter" &&
      parseResult.tree &&
      parseResult.languageInstance
    ) {
      const codeInfo = extractCodeInfo(
        parseResult.tree,
        parseResult.languageInstance,
        parseResult.language,
      );

      response.metrics = {
        lines: parseResult.lineCount,
        functions: codeInfo.symbols.summary.functions,
        classes: codeInfo.symbols.summary.classes,
        imports: codeInfo.imports.length,
        exports: codeInfo.exports.length,
      };

      if (include_symbols) {
        response.symbols = codeInfo.symbols.symbols;
      }

      if (include_imports) {
        response.imports = codeInfo.imports;
      }

      if (include_exports) {
        response.exports = codeInfo.exports;
      }

      if (include_ast) {
        response.ast = getASTRoot(
          {
            tree: parseResult.tree,
            language: parseResult.language,
            parser: null as never,
            languageInstance: parseResult.languageInstance,
          },
          ast_max_depth,
        );
      }
    } else {
      // Fallback path - limited analysis
      const symbols = extractSymbols(parseResult);

      response.metrics = {
        lines: parseResult.lineCount,
        functions: symbols.functions.length,
        classes: symbols.classes.length,
        imports: 0, // Not available in fallback
        exports: 0, // Not available in fallback
      };

      if (include_symbols) {
        response.symbols = symbols.all;
        response.symbol_extraction_method = symbols.method;
      }

      if (include_chunks && parseResult.chunks) {
        response.chunks = parseResult.chunks.map((chunk) => ({
          index: chunk.index,
          startLine: chunk.startLine,
          endLine: chunk.endLine,
          preview:
            chunk.content.slice(0, 100) +
            (chunk.content.length > 100 ? "..." : ""),
        }));
        response.chunk_count = parseResult.chunks.length;
      }

      // Note about limited analysis
      response.note = `File parsed using ${parseResult.method} fallback. Some features (imports, exports, full AST) are not available.`;
    }

    // Build summary message
    const metrics = response.metrics as Record<string, number>;
    const methodNote =
      parseResult.method !== "tree-sitter" ? ` [${parseResult.method}]` : "";
    const summary = [
      `${parseResult.language} file${methodNote}`,
      `${String(metrics.lines)} lines`,
      `${String(metrics.functions)} functions`,
      `${String(metrics.classes)} classes`,
    ];

    if (parseResult.method === "tree-sitter") {
      summary.push(`${String(metrics.imports)} imports`);
      summary.push(`${String(metrics.exports)} exports`);
    }

    return {
      success: true,
      data: response,
      message: `Analyzed ${file_path}: ${summary.join(", ")}`,
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      success: false,
      error: `Failed to analyze file: ${message}`,
    };
  }
}

export const analyzeFileFeature: Feature<typeof analyzeFileSchema> = {
  name: "analyze_file",
  description:
    "Perform a comprehensive analysis of a source code file. Returns symbols, imports, exports, and code metrics. Optionally includes the full AST.",
  schema: analyzeFileSchema,
  execute,
};
