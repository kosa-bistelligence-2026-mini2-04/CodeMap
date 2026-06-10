/**
 * Get Call Graph Feature
 *
 * Analyzes function call relationships in a codebase.
 * Can either:
 * 1. Build a full call graph for a directory
 * 2. Query callers/callees for a specific function
 */

import { z } from "zod";
import * as fs from "node:fs";
import * as path from "node:path";
import ignore, { type Ignore } from "ignore";
import type { Feature, FeatureResult } from "@features/types";
import {
  buildCallGraph,
  getCallContext,
  formatCallContext,
  shouldIndexFile,
  type CallGraphNode,
} from "@core/embeddings";
import { logger } from "@utils";

export const getCallGraphSchema = z.object({
  directory: z
    .string()
    .optional()
    .default(".")
    .describe("Path to the directory to analyze"),
  functionName: z
    .string()
    .optional()
    .describe("Optional: specific function name to query callers/callees for"),
  filePath: z
    .string()
    .optional()
    .describe(
      "Optional: file path to narrow down function search (used with functionName)",
    ),
  maxDepth: z
    .number()
    .int()
    .positive()
    .optional()
    .default(2)
    .describe("Maximum depth for call chain traversal (default: 2)"),
  exclude: z
    .array(z.string())
    .optional()
    .default([])
    .describe("Glob patterns to exclude from analysis"),
});

export type GetCallGraphInput = z.infer<typeof getCallGraphSchema>;

interface CallGraphResult {
  directory: string;
  mode: "full" | "query";
  totalFunctions: number;
  totalCalls: number;
  filesAnalyzed: number;
  query?: {
    functionName: string;
    filePath?: string;
    callers: CallGraphNode[];
    callees: CallGraphNode[];
    formattedContext: string;
  };
  graph?: {
    nodes: Record<string, CallGraphNode>;
    topCallers: { name: string; callCount: number }[];
    topCallees: { name: string; calledByCount: number }[];
  };
}

/**
 * Create gitignore filter from .gitignore file
 */
function createIgnoreFilter(
  directory: string,
  extraPatterns: string[],
): Ignore {
  const ig = ignore();

  // Add default ignores
  ig.add(["node_modules", ".git", "dist", "build", ".src-index"]);

  // Add extra patterns
  if (extraPatterns.length > 0) {
    ig.add(extraPatterns);
  }

  // Read .gitignore if exists
  const gitignorePath = path.join(directory, ".gitignore");
  if (fs.existsSync(gitignorePath)) {
    const content = fs.readFileSync(gitignorePath, "utf-8");
    ig.add(content);
  }

  return ig;
}

/**
 * Check if a name starts with a dot (hidden file/folder)
 */
function isHidden(name: string): boolean {
  return name.startsWith(".");
}

/**
 * Recursively collect files from a directory
 */
function collectFiles(dir: string, ig: Ignore, baseDir: string): string[] {
  const files: string[] = [];

  const entries = fs.readdirSync(dir, { withFileTypes: true });

  for (const entry of entries) {
    if (isHidden(entry.name)) {
      continue;
    }

    const fullPath = path.join(dir, entry.name);
    const relativePath = path.relative(baseDir, fullPath).replace(/\\/g, "/");

    if (ig.ignores(relativePath)) {
      continue;
    }

    if (entry.isDirectory()) {
      files.push(...collectFiles(fullPath, ig, baseDir));
    } else if (entry.isFile() && shouldIndexFile(entry.name)) {
      files.push(fullPath);
    }
  }

  return files;
}

/**
 * Execute the get_call_graph feature
 */
export async function execute(
  input: GetCallGraphInput,
): Promise<FeatureResult> {
  const { directory, functionName, filePath, maxDepth, exclude } = input;

  // Validate directory exists
  if (!fs.existsSync(directory)) {
    return {
      success: false,
      error: `Directory not found: ${directory}`,
    };
  }

  const absoluteDir = path.resolve(directory);

  try {
    // Create ignore filter
    const ig = createIgnoreFilter(absoluteDir, exclude);

    // Collect files
    const files = collectFiles(absoluteDir, ig, absoluteDir);

    if (files.length === 0) {
      return {
        success: true,
        message: "No analyzable files found in directory",
        data: {
          directory: absoluteDir,
          mode: "full",
          totalFunctions: 0,
          totalCalls: 0,
          filesAnalyzed: 0,
        } satisfies CallGraphResult,
      };
    }

    logger.debug(`Analyzing call graph for ${String(files.length)} files`);

    // Read file contents and build call graph
    const fileContents = files.map((f) => ({
      path: f,
      content: fs.readFileSync(f, "utf-8"),
    }));

    const graph = await buildCallGraph(fileContents);

    const result: CallGraphResult = {
      directory: absoluteDir,
      mode: functionName ? "query" : "full",
      totalFunctions: graph.nodes.size,
      totalCalls: Array.from(graph.nodes.values()).reduce(
        (sum, node) => sum + node.calls.length,
        0,
      ),
      filesAnalyzed: files.length,
    };

    // If querying for a specific function
    if (functionName) {
      const targetFilePath = filePath
        ? path.resolve(directory, filePath)
        : undefined;

      const callContext = getCallContext(
        graph,
        targetFilePath ?? "",
        functionName,
      );

      if (!callContext) {
        // Try to find function in any file
        let foundContext: {
          callers: CallGraphNode[];
          callees: CallGraphNode[];
        } | null = null;
        let foundFilePath = "";

        for (const node of graph.nodes.values()) {
          if (node.name === functionName) {
            foundFilePath = node.filePath;
            foundContext = getCallContext(graph, node.filePath, functionName);
            if (foundContext) {
              break;
            }
          }
        }

        if (foundContext) {
          result.query = {
            functionName,
            filePath: foundFilePath,
            callers: foundContext.callers,
            callees: foundContext.callees,
            formattedContext: formatCallContext(
              foundContext.callers,
              foundContext.callees,
              maxDepth,
            ),
          };
        } else {
          return {
            success: false,
            error: `Function '${functionName}' not found in the codebase`,
          };
        }
      } else {
        result.query = {
          functionName,
          filePath: targetFilePath,
          callers: callContext.callers,
          callees: callContext.callees,
          formattedContext: formatCallContext(
            callContext.callers,
            callContext.callees,
            maxDepth,
          ),
        };
      }

      const message = `Call graph for '${functionName}':\n\n${result.query.formattedContext}`;

      return {
        success: true,
        message,
        data: result,
      };
    }

    // Full graph mode - compute top callers and callees
    const callerCounts = new Map<string, number>();
    const calleeCounts = new Map<string, number>();

    for (const node of graph.nodes.values()) {
      callerCounts.set(node.name, node.calls.length);
      calleeCounts.set(node.name, node.calledBy.length);
    }

    const topCallers = Array.from(callerCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([name, callCount]) => ({ name, callCount }));

    const topCallees = Array.from(calleeCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 10)
      .map(([name, calledByCount]) => ({ name, calledByCount }));

    result.graph = {
      nodes: Object.fromEntries(graph.nodes),
      topCallers,
      topCallees,
    };

    // Build summary message
    const topCallersStr = topCallers
      .map((c) => `  - ${c.name}: ${String(c.callCount)} calls`)
      .join("\n");
    const topCalleesStr = topCallees
      .map(
        (c) => `  - ${c.name}: called by ${String(c.calledByCount)} functions`,
      )
      .join("\n");

    const message = `Call graph analysis complete:
- Files analyzed: ${String(files.length)}
- Functions found: ${String(result.totalFunctions)}
- Total calls: ${String(result.totalCalls)}

Top callers (functions that call the most):
${topCallersStr}

Most called (functions called by the most):
${topCalleesStr}

Use functionName parameter to query specific function relationships.`;

    return {
      success: true,
      message,
      data: result,
    };
  } catch (err) {
    const errorMsg = err instanceof Error ? err.message : String(err);
    return {
      success: false,
      error: `Call graph analysis failed: ${errorMsg}`,
    };
  }
}

export const getCallGraphFeature: Feature<typeof getCallGraphSchema> = {
  name: "get_call_graph",
  description:
    "Analyze function call relationships in a codebase. Query callers/callees for a specific function or get full call graph statistics.",
  schema: getCallGraphSchema,
  execute,
};
