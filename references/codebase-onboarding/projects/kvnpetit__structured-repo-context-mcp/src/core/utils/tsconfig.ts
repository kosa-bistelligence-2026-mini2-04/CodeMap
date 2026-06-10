/**
 * TSConfig utilities for reading path aliases
 *
 * Reads and parses tsconfig.json to extract path aliases
 * in a format usable by the cross-file resolution system.
 */

import * as fs from "node:fs";
import * as path from "node:path";
import { logger } from "@utils";

/**
 * TSConfig paths as defined in compilerOptions.paths
 */
type TsConfigPaths = Record<string, string[]>;

/**
 * Partial TSConfig structure
 */
interface TsConfig {
  compilerOptions?: {
    baseUrl?: string;
    paths?: TsConfigPaths;
  };
  extends?: string;
}

/**
 * Converted path aliases in simple format
 * Key is the alias prefix (e.g., "@core", "@/")
 * Value is the resolved directory path relative to project root
 */
export type PathAliases = Record<string, string>;

/**
 * Strip JSON comments (single-line // and multi-line)
 */
function stripJsonComments(json: string): string {
  let result = "";
  let inString = false;
  let inSingleLineComment = false;
  let inMultiLineComment = false;

  for (let i = 0; i < json.length; i++) {
    const char = json.charAt(i);
    const nextChar = json.charAt(i + 1);

    if (inSingleLineComment) {
      if (char === "\n") {
        inSingleLineComment = false;
        result += char;
      }
      continue;
    }

    if (inMultiLineComment) {
      if (char === "*" && nextChar === "/") {
        inMultiLineComment = false;
        i++; // Skip the '/'
      }
      continue;
    }

    if (inString) {
      result += char;
      if (char === '"' && json.charAt(i - 1) !== "\\") {
        inString = false;
      }
      continue;
    }

    // Not in string or comment
    if (char === '"') {
      inString = true;
      result += char;
    } else if (char === "/" && nextChar === "/") {
      inSingleLineComment = true;
      i++; // Skip the second '/'
    } else if (char === "/" && nextChar === "*") {
      inMultiLineComment = true;
      i++; // Skip the '*'
    } else {
      result += char;
    }
  }

  return result;
}

/**
 * Parse tsconfig.json content
 */
function parseTsConfig(content: string): TsConfig | null {
  try {
    const strippedContent = stripJsonComments(content);
    return JSON.parse(strippedContent) as TsConfig;
  } catch (error) {
    logger.debug(
      `Failed to parse tsconfig.json: ${error instanceof Error ? error.message : String(error)}`,
    );
    return null;
  }
}

/**
 * Convert tsconfig paths to simple path aliases format
 *
 * TSConfig format:
 *   "@core": ["src/core"]
 *   "@core/*": ["src/core/*"]
 *
 * Output format:
 *   "@core": "src/core"
 *   "@core/": "src/core/"
 */
function convertPaths(
  paths: TsConfigPaths,
  baseUrl: string,
  projectRoot: string,
): PathAliases {
  const aliases: PathAliases = {};

  for (const [pattern, targets] of Object.entries(paths)) {
    const target = targets[0];
    if (!target) {
      continue;
    }

    // Handle wildcard patterns like "@core/*" -> ["src/core/*"]
    if (pattern.endsWith("/*") && target.endsWith("/*")) {
      // Remove the /* from both pattern and target
      const aliasPrefix = pattern.slice(0, -2) + "/";
      const targetPath = target.slice(0, -2) + "/";

      // Resolve relative to baseUrl
      const resolvedTarget = path.join(projectRoot, baseUrl, targetPath);
      const relativeTarget = path.relative(projectRoot, resolvedTarget);

      aliases[aliasPrefix] = relativeTarget.replace(/\\/g, "/") + "/";
    } else {
      // Handle exact matches like "@core" -> ["src/core"]
      const resolvedTarget = path.join(projectRoot, baseUrl, target);
      const relativeTarget = path.relative(projectRoot, resolvedTarget);

      aliases[pattern] = relativeTarget.replace(/\\/g, "/");
    }
  }

  return aliases;
}

/**
 * Read tsconfig.json and extract path aliases
 *
 * Handles:
 * - Comments in tsconfig (// and /* *\/)
 * - baseUrl relative paths
 * - Wildcard patterns (@core/* -> src/core/*)
 * - Exact patterns (@core -> src/core)
 *
 * @param projectRoot - The project root directory containing tsconfig.json
 * @returns Path aliases in simple format, or empty object if not found/invalid
 */
export function readPathAliases(projectRoot: string): PathAliases {
  const tsconfigPath = path.join(projectRoot, "tsconfig.json");

  if (!fs.existsSync(tsconfigPath)) {
    logger.debug(`No tsconfig.json found at ${tsconfigPath}`);
    return {};
  }

  try {
    const content = fs.readFileSync(tsconfigPath, "utf-8");
    const tsconfig = parseTsConfig(content);

    if (!tsconfig) {
      return {};
    }

    const paths = tsconfig.compilerOptions?.paths;
    const baseUrl = tsconfig.compilerOptions?.baseUrl ?? ".";

    if (!paths || Object.keys(paths).length === 0) {
      logger.debug("No paths defined in tsconfig.json");
      return {};
    }

    const aliases = convertPaths(paths, baseUrl, projectRoot);
    logger.debug(
      `Loaded ${String(Object.keys(aliases).length)} path aliases from tsconfig.json`,
    );

    return aliases;
  } catch (error) {
    logger.debug(
      `Failed to read tsconfig.json: ${error instanceof Error ? error.message : String(error)}`,
    );
    return {};
  }
}

/**
 * Get cache key for memoization
 */
const pathAliasCache = new Map<string, PathAliases>();

/**
 * Read path aliases with caching
 */
export function readPathAliasesCached(projectRoot: string): PathAliases {
  const normalizedRoot = path.normalize(projectRoot);
  const cached = pathAliasCache.get(normalizedRoot);

  if (cached !== undefined) {
    return cached;
  }

  const aliases = readPathAliases(projectRoot);
  pathAliasCache.set(normalizedRoot, aliases);
  return aliases;
}

/**
 * Clear the path aliases cache
 */
export function clearPathAliasCache(): void {
  pathAliasCache.clear();
}
