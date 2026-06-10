import { z } from "zod";

import { parseCode } from "@core/parser";
import {
  executePresetQuery,
  executeQuery,
  getAvailablePresets,
  type QueryPreset,
} from "@core/queries";

import type { Feature, FeatureResult } from "@features/types";
import {
  errorMessage,
  errorResult,
  readContent,
  successResult,
} from "@features/utils";

const presetValues = [
  "functions",
  "classes",
  "imports",
  "exports",
  "comments",
  "strings",
  "variables",
  "types",
] as const;

export const queryCodeSchema = z
  .object({
    file_path: z
      .string()
      .optional()
      .describe(
        "Path to the file to query (either file_path or content required)",
      ),
    content: z
      .string()
      .optional()
      .describe(
        "Code content to query directly (either file_path or content required)",
      ),
    language: z
      .string()
      .optional()
      .describe("Language name (auto-detected from file path if not provided)"),
    query: z
      .string()
      .optional()
      .describe("SCM query pattern (either query or preset required)"),
    preset: z
      .enum(presetValues)
      .optional()
      .describe(
        "Preset query name: functions, classes, imports, exports, comments, strings, variables, types",
      ),
    max_matches: z
      .number()
      .int()
      .positive()
      .optional()
      .describe("Maximum number of matches to return"),
  })
  .refine((data) => data.file_path ?? data.content, {
    message: "Either file_path or content must be provided",
  })
  .refine((data) => data.query ?? data.preset, {
    message: "Either query or preset must be provided",
  });

export type QueryCodeInput = z.infer<typeof queryCodeSchema>;

export async function execute(input: QueryCodeInput): Promise<FeatureResult> {
  const {
    file_path,
    content: inputContent,
    language,
    query,
    preset,
    max_matches,
  } = input;

  // Get content
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

    // Execute query
    let result;
    if (preset) {
      // Check if preset is available for this language
      const availablePresets = getAvailablePresets(parseResult.language);
      if (!availablePresets.includes(preset)) {
        return errorMessage(
          `Preset '${preset}' is not available for ${parseResult.language}. Available presets: ${availablePresets.join(", ")}`,
        );
      }

      result = executePresetQuery(
        parseResult.tree,
        parseResult.languageInstance,
        parseResult.language,
        preset as QueryPreset,
        { maxMatches: max_matches },
      );
    } else if (query) {
      result = executeQuery(
        parseResult.tree,
        parseResult.languageInstance,
        query,
        parseResult.language,
        { maxMatches: max_matches },
      );
    } else {
      return errorMessage("Either query or preset must be provided");
    }

    return successResult(
      {
        matches: result.matches,
        count: result.count,
        language: result.language,
        query: result.query,
      },
      `Found ${String(result.count)} match${result.count === 1 ? "" : "es"} in ${parseResult.language} code`,
    );
  } catch (error) {
    return errorResult("query", error);
  }
}

export const queryCodeFeature: Feature<typeof queryCodeSchema> = {
  name: "query_code",
  description:
    "Execute Tree-sitter SCM queries on code to find patterns. Use preset queries (functions, classes, imports, exports, comments, strings, variables, types) or custom SCM query patterns.",
  schema: queryCodeSchema,
  execute,
};
