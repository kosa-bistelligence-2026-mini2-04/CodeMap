import { z } from "zod";

import { parseCode } from "@core/parser";
import { extractSymbols, type SymbolFilter } from "@core/symbols";

import type { Feature, FeatureResult } from "@features/types";
import { errorResult, readContent, successResult } from "@features/utils";

const symbolTypeValues = [
  "function",
  "class",
  "variable",
  "constant",
  "interface",
  "type",
  "enum",
  "method",
  "property",
] as const;

export const listSymbolsSchema = z
  .object({
    file_path: z
      .string()
      .optional()
      .describe(
        "Path to the file to analyze (either file_path or content required)",
      ),
    content: z
      .string()
      .optional()
      .describe(
        "Code content to analyze directly (either file_path or content required)",
      ),
    language: z
      .string()
      .optional()
      .describe("Language name (auto-detected from file path if not provided)"),
    types: z
      .array(z.enum(symbolTypeValues))
      .optional()
      .describe(
        "Filter by symbol types: function, class, variable, constant, interface, type, enum, method, property",
      ),
  })
  .refine((data) => data.file_path ?? data.content, {
    message: "Either file_path or content must be provided",
  });

export type ListSymbolsInput = z.infer<typeof listSymbolsSchema>;

export async function execute(input: ListSymbolsInput): Promise<FeatureResult> {
  const { file_path, content: inputContent, language, types } = input;

  // Get content using shared helper
  const contentResult = readContent(file_path, inputContent);
  if (!contentResult.success) {
    return { success: false, error: contentResult.error };
  }

  try {
    // Parse the code
    const parseResult = await parseCode(contentResult.content, {
      language,
      filePath: file_path,
    });

    // Build filter
    const filter: SymbolFilter = {};
    if (types && types.length > 0) {
      filter.types = types;
    }

    // Extract symbols
    const { symbols, summary } = extractSymbols(
      parseResult.tree,
      parseResult.languageInstance,
      parseResult.language,
      filter,
    );

    return successResult(
      {
        symbols,
        summary,
        language: parseResult.language,
      },
      `Found ${String(summary.total)} symbol${summary.total === 1 ? "" : "s"} in ${parseResult.language} code`,
    );
  } catch (error) {
    return errorResult("extract symbols", error);
  }
}

export const listSymbolsFeature: Feature<typeof listSymbolsSchema> = {
  name: "list_symbols",
  description:
    "Extract all code symbols (functions, classes, variables, etc.) from a file. Returns structured information including name, type, location, and signature for each symbol.",
  schema: listSymbolsSchema,
  execute,
};
