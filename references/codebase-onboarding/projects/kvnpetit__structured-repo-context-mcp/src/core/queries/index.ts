/**
 * SCM Query engine for Tree-sitter
 *
 * Supports both official .scm query files and custom preset patterns
 */
import {
  type Language,
  Query,
  type QueryMatch as TSQueryMatch,
  type Tree,
} from "web-tree-sitter";

import type { ASTNode, QueryCapture, QueryMatch } from "@core/ast/types";
import { toASTNode } from "@core/parser";

import {
  deduplicateNodes,
  extractNodes,
  findCapture,
  findCaptureByPrefix,
  getCaptureKind,
} from "./helpers";
import {
  hasOfficialTags,
  loadHighlightsQuery,
  loadLocalsQuery,
  loadTagsQuery,
  type SCMQueryType,
} from "./loader";
import {
  getAvailablePresets as getAvailablePresetsBase,
  getQueryPattern,
  type QueryPreset,
} from "./patterns";

// Re-export helpers for external use
export * from "./helpers";

// Re-export patterns and loader (except getAvailablePresets which we override)
export * from "./loader";
export {
  getQueryPattern,
  getQuerySupportedLanguages,
  isPresetAvailable,
  FALLBACK_PATTERNS,
  type QueryPreset,
} from "./patterns";

/**
 * Get all available presets for a language
 * Automatically checks for official tags.scm support
 */
export function getAvailablePresets(language: string): QueryPreset[] {
  return getAvailablePresetsBase(language, hasOfficialTags(language));
}

/**
 * Query execution result
 */
export interface QueryResult {
  /** Query matches */
  matches: QueryMatch[];
  /** Total match count */
  count: number;
  /** Query that was executed */
  query: string;
  /** Language used */
  language: string;
  /** Source of the query (official .scm or custom preset) */
  source: "official" | "preset";
}

/**
 * Query options
 */
export interface QueryOptions {
  /** Maximum number of matches to return */
  maxMatches?: number;
  /** Start index (byte offset) */
  startIndex?: number;
  /** End index (byte offset) */
  endIndex?: number;
  /** Prefer official .scm files when available */
  preferOfficial?: boolean;
}

/**
 * Execute a SCM query on parsed code
 */
export function executeQuery(
  tree: Tree,
  languageInstance: Language,
  queryString: string,
  language: string,
  options: QueryOptions = {},
): QueryResult {
  const { maxMatches, startIndex, endIndex } = options;

  // Create query
  let query: Query;
  try {
    query = new Query(languageInstance, queryString);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Invalid query: ${message}`);
  }

  // Get matches
  const queryMatches: TSQueryMatch[] = query.matches(tree.rootNode, {
    startIndex,
    endIndex,
  });

  const matches: QueryMatch[] = [];
  let count = 0;

  for (const match of queryMatches) {
    // Check max matches limit
    if (maxMatches !== undefined && count >= maxMatches) {
      break;
    }

    const captures: QueryCapture[] = match.captures.map((capture) => ({
      name: capture.name,
      node: toASTNode(capture.node),
    }));

    matches.push({
      pattern: match.patternIndex,
      captures,
    });

    count++;
  }

  return {
    matches,
    count,
    query: queryString,
    language,
    source: "preset",
  };
}

/**
 * Execute an official .scm query file
 *
 * @param tree - Parsed tree
 * @param languageInstance - Tree-sitter language instance
 * @param language - Language name
 * @param queryType - Type of query (tags, highlights, locals, etc.)
 * @param options - Query options
 */
export function executeOfficialQuery(
  tree: Tree,
  languageInstance: Language,
  language: string,
  queryType: SCMQueryType,
  options: QueryOptions = {},
): QueryResult | undefined {
  let queryString: string | undefined;

  switch (queryType) {
    case "tags":
      queryString = loadTagsQuery(language);
      break;
    case "highlights":
      queryString = loadHighlightsQuery(language);
      break;
    case "locals":
      queryString = loadLocalsQuery(language);
      break;
    case "injections":
    case "indents":
    case "folds":
      // These query types are not yet implemented
      return undefined;
  }

  if (!queryString) {
    return undefined;
  }

  try {
    const result = executeQuery(
      tree,
      languageInstance,
      queryString,
      language,
      options,
    );
    return {
      ...result,
      source: "official",
    };
  } catch {
    // Official query might have incompatible patterns
    return undefined;
  }
}

/**
 * Execute tags.scm for comprehensive symbol extraction
 *
 * This uses the official Tree-sitter tags.scm file which provides:
 * - Function definitions with documentation
 * - Class definitions
 * - Method definitions
 * - Module/interface definitions
 * - Reference tracking (calls, types)
 */
export function executeTagsQuery(
  tree: Tree,
  languageInstance: Language,
  language: string,
  options: QueryOptions = {},
): QueryResult | undefined {
  return executeOfficialQuery(
    tree,
    languageInstance,
    language,
    "tags",
    options,
  );
}

/**
 * Execute a preset query
 * Uses official tags.scm for functions/classes when available,
 * otherwise falls back to preset patterns
 */
export function executePresetQuery(
  tree: Tree,
  languageInstance: Language,
  language: string,
  preset: QueryPreset,
  options: QueryOptions = {},
): QueryResult {
  const { maxMatches } = options;

  // Check if we have a language-specific fallback pattern for this preset
  // This is needed for languages like TypeScript where official tags.scm is incomplete
  const fallbackPattern = getQueryPattern(language, preset);

  // For functions and classes, try official tags.scm first, then fallback patterns
  if (preset === "functions" || preset === "classes") {
    // First try official tags.scm
    if (hasOfficialTags(language)) {
      const { definitions } = extractSymbolsFromTags(
        tree,
        languageInstance,
        language,
      );

      let filteredDefs =
        preset === "functions"
          ? definitions.filter(
              (d) => d.kind === "function" || d.kind === "method",
            )
          : definitions.filter(
              (d) =>
                d.kind === "class" ||
                d.kind === "interface" ||
                d.kind === "module",
            );

      // If official tags.scm found results, use them
      if (filteredDefs.length > 0) {
        // Apply maxMatches limit
        if (maxMatches !== undefined && filteredDefs.length > maxMatches) {
          filteredDefs = filteredDefs.slice(0, maxMatches);
        }

        // Convert to QueryResult format
        const matches: QueryMatch[] = filteredDefs.map((def) => ({
          pattern: 0,
          captures: [
            {
              name:
                preset === "functions"
                  ? "function.definition"
                  : "class.definition",
              node: def.node,
            },
            { name: `${preset.slice(0, -1)}.name`, node: def.nameNode },
          ],
        }));

        return {
          matches,
          count: matches.length,
          query: `[tags.scm ${preset}]`,
          language,
          source: "official",
        };
      }

      // Official tags.scm found 0 results - try fallback pattern or return empty
      if (fallbackPattern) {
        return executeQuery(
          tree,
          languageInstance,
          fallbackPattern,
          language,
          options,
        );
      }

      // No fallback pattern and 0 results from official - return empty result
      return {
        matches: [],
        count: 0,
        query: `[tags.scm ${preset}]`,
        language,
        source: "official",
      };
    }

    // No official tags.scm - must use fallback pattern
    if (fallbackPattern) {
      return executeQuery(
        tree,
        languageInstance,
        fallbackPattern,
        language,
        options,
      );
    }
  }

  // For other presets, use fallback patterns
  if (!fallbackPattern) {
    throw new Error(`No '${preset}' query pattern available for ${language}`);
  }

  return executeQuery(
    tree,
    languageInstance,
    fallbackPattern,
    language,
    options,
  );
}

/**
 * Extract symbols using official tags.scm when available
 *
 * This is the recommended method for symbol extraction as it uses
 * the official Tree-sitter query files for better accuracy.
 */
export function extractSymbolsFromTags(
  tree: Tree,
  languageInstance: Language,
  language: string,
): {
  definitions: TagDefinition[];
  references: TagReference[];
} {
  const result = executeTagsQuery(tree, languageInstance, language);

  if (!result) {
    return { definitions: [], references: [] };
  }

  const definitions: TagDefinition[] = [];
  const references: TagReference[] = [];

  for (const match of result.matches) {
    // Extract name capture
    const nameCapture = findCapture(match.captures, "name");
    if (!nameCapture) {
      continue;
    }

    // Check if it's a definition or reference
    const defCapture = findCaptureByPrefix(match.captures, "definition.");
    const refCapture = findCaptureByPrefix(match.captures, "reference.");
    const docCapture = findCapture(match.captures, "doc");

    if (defCapture) {
      const kind = getCaptureKind(defCapture.name, "definition.") as TagKind;
      definitions.push({
        name: nameCapture.node.text,
        kind,
        node: defCapture.node,
        nameNode: nameCapture.node,
        documentation: docCapture?.node.text,
      });
    } else if (refCapture) {
      const kind = getCaptureKind(refCapture.name, "reference.") as TagKind;
      references.push({
        name: nameCapture.node.text,
        kind,
        node: refCapture.node,
        nameNode: nameCapture.node,
      });
    }
  }

  return { definitions, references };
}

/**
 * Tag definition kinds from official tags.scm
 */
export type TagKind =
  | "function"
  | "method"
  | "class"
  | "module"
  | "interface"
  | "constant"
  | "type"
  | "call";

/**
 * A symbol definition extracted from tags.scm
 */
export interface TagDefinition {
  name: string;
  kind: TagKind;
  node: ASTNode;
  nameNode: ASTNode;
  documentation?: string;
}

/**
 * A symbol reference extracted from tags.scm
 */
export interface TagReference {
  name: string;
  kind: TagKind;
  node: ASTNode;
  nameNode: ASTNode;
}

/**
 * Find all functions in the code
 * Prefers official tags.scm when available
 */
export function findFunctions(
  tree: Tree,
  languageInstance: Language,
  language: string,
  options: QueryOptions = {},
): ASTNode[] {
  // Try official tags.scm first if preferOfficial is true or default
  if (options.preferOfficial !== false && hasOfficialTags(language)) {
    const { definitions } = extractSymbolsFromTags(
      tree,
      languageInstance,
      language,
    );
    return definitions
      .filter((d) => d.kind === "function" || d.kind === "method")
      .map((d) => d.node);
  }

  // Fall back to preset patterns
  try {
    const result = executePresetQuery(
      tree,
      languageInstance,
      language,
      "functions",
      options,
    );

    return extractNodes(result.matches, [
      "function.definition",
      "method.definition",
      "function.declaration",
    ]);
  } catch {
    return [];
  }
}

/**
 * Find all classes/structs in the code
 * Prefers official tags.scm when available
 */
export function findClasses(
  tree: Tree,
  languageInstance: Language,
  language: string,
  options: QueryOptions = {},
): ASTNode[] {
  // Try official tags.scm first
  if (options.preferOfficial !== false && hasOfficialTags(language)) {
    const { definitions } = extractSymbolsFromTags(
      tree,
      languageInstance,
      language,
    );
    return definitions
      .filter(
        (d) =>
          d.kind === "class" || d.kind === "interface" || d.kind === "module",
      )
      .map((d) => d.node);
  }

  // Fall back to preset patterns
  try {
    const result = executePresetQuery(
      tree,
      languageInstance,
      language,
      "classes",
      options,
    );

    return extractNodes(result.matches, [
      "class.definition",
      "struct.definition",
      "impl.definition",
    ]);
  } catch {
    return [];
  }
}

/**
 * Find all imports in the code
 */
export function findImports(
  tree: Tree,
  languageInstance: Language,
  language: string,
  options: QueryOptions = {},
): ASTNode[] {
  try {
    const result = executePresetQuery(
      tree,
      languageInstance,
      language,
      "imports",
      options,
    );

    return deduplicateNodes(result.matches, [
      "import.statement",
      "include.statement",
    ]);
  } catch {
    return [];
  }
}

/**
 * Find all exports in the code
 */
export function findExports(
  tree: Tree,
  languageInstance: Language,
  language: string,
  options: QueryOptions = {},
): ASTNode[] {
  try {
    const result = executePresetQuery(
      tree,
      languageInstance,
      language,
      "exports",
      options,
    );

    return deduplicateNodes(result.matches, [
      "export.statement",
      "export.function",
      "export.class",
      "export.type",
    ]);
  } catch {
    return [];
  }
}

/**
 * Find all comments in the code
 */
export function findComments(
  tree: Tree,
  languageInstance: Language,
  language: string,
  options: QueryOptions = {},
): ASTNode[] {
  try {
    const result = executePresetQuery(
      tree,
      languageInstance,
      language,
      "comments",
      options,
    );

    return extractNodes(result.matches, ["comment", "comment.block"]);
  } catch {
    return [];
  }
}

/**
 * Find all string literals in the code
 */
export function findStrings(
  tree: Tree,
  languageInstance: Language,
  language: string,
  options: QueryOptions = {},
): ASTNode[] {
  try {
    const result = executePresetQuery(
      tree,
      languageInstance,
      language,
      "strings",
      options,
    );

    return extractNodes(result.matches, [
      "string",
      "string.template",
      "string.raw",
    ]);
  } catch {
    return [];
  }
}

/**
 * Get function name from a function node
 */
export function getFunctionName(funcNode: ASTNode): string | undefined {
  // Look in fields first
  if (funcNode.fields?.name) {
    const nameNode = funcNode.fields.name;
    if (!Array.isArray(nameNode)) {
      return nameNode.text;
    }
  }

  // Look in children for identifier
  if (funcNode.children) {
    for (const child of funcNode.children) {
      if (
        child.type === "identifier" ||
        child.type === "property_identifier" ||
        child.type === "field_identifier"
      ) {
        return child.text;
      }
      // Recursive for function_declarator
      if (child.type === "function_declarator") {
        return getFunctionName(child);
      }
    }
  }

  return undefined;
}

/**
 * Get class name from a class node
 */
export function getClassName(classNode: ASTNode): string | undefined {
  // Look in fields first
  if (classNode.fields?.name) {
    const nameNode = classNode.fields.name;
    if (!Array.isArray(nameNode)) {
      return nameNode.text;
    }
  }

  // Look in children for identifier
  if (classNode.children) {
    for (const child of classNode.children) {
      if (child.type === "identifier" || child.type === "type_identifier") {
        return child.text;
      }
    }
  }

  return undefined;
}
