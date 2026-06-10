import { z } from "zod";

import { getASTRoot, parseCode } from "@core/parser";

import type { Feature, FeatureResult } from "@features/types";
import { errorResult, readContent, successResult } from "@features/utils";

export const parseAstSchema = z
  .object({
    file_path: z
      .string()
      .optional()
      .describe(
        "Path to the file to parse (either file_path or content required)",
      ),
    content: z
      .string()
      .optional()
      .describe(
        "Code content to parse directly (either file_path or content required)",
      ),
    language: z
      .string()
      .optional()
      .describe("Language name (auto-detected from file path if not provided)"),
    max_depth: z
      .number()
      .int()
      .positive()
      .optional()
      .describe("Maximum depth of AST to return (default: unlimited)"),
  })
  .refine((data) => data.file_path ?? data.content, {
    message: "Either file_path or content must be provided",
  });

export type ParseAstInput = z.infer<typeof parseAstSchema>;

export async function execute(input: ParseAstInput): Promise<FeatureResult> {
  const { file_path, content: inputContent, language, max_depth } = input;

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

    // Get AST root with optional depth limit
    const root = getASTRoot(parseResult, max_depth);

    // Count nodes (without depth limit for accurate count)
    const fullRoot = getASTRoot(parseResult);
    const countNodesRecursive = (node: typeof fullRoot): number => {
      let count = 1;
      if (node.children) {
        for (const child of node.children) {
          count += countNodesRecursive(child);
        }
      }
      return count;
    };
    const nodeCount = countNodesRecursive(fullRoot);

    return successResult(
      {
        language: parseResult.language,
        root,
        node_count: nodeCount,
      },
      `Parsed ${parseResult.language} code with ${String(nodeCount)} nodes`,
    );
  } catch (error) {
    return errorResult("parse", error);
  }
}

export const parseAstFeature: Feature<typeof parseAstSchema> = {
  name: "parse_ast",
  description:
    "Parse code and return the Abstract Syntax Tree (AST). Supports multiple languages including JavaScript, TypeScript, Python, Go, Rust, Java, C, C++, and more.",
  schema: parseAstSchema,
  execute,
};
