/**
 * SCM Query file loader
 *
 * Loads official Tree-sitter .scm query files from local assets directory
 * Supports inheritance via `; inherits: lang1,lang2` directives
 */
import { existsSync, readFileSync } from "fs";
import { join } from "path";

import { assetExists, getAssetsDir, registerCache } from "@core/utils";

/**
 * Query type available in Tree-sitter grammars
 */
export type SCMQueryType =
  | "tags"
  | "highlights"
  | "locals"
  | "injections"
  | "indents"
  | "folds";

/**
 * Cache for loaded SCM queries (with inheritance resolved)
 */
const scmCache = new Map<string, string>();

/**
 * Supported languages with SCM query files
 */
const SUPPORTED_LANGUAGES = new Set([
  // Web & Frontend
  "javascript",
  "typescript",
  "tsx",
  "svelte",
  "html",
  // Systems Programming
  "c",
  "cpp",
  "rust",
  "go",
  "swift",
  // JVM Languages
  "java",
  "scala",
  "kotlin",
  // Scripting Languages
  "python",
  "ruby",
  "php",
  // .NET
  "csharp",
  "c_sharp",
  // Functional
  "ocaml",
  // Base/dependency languages (for inheritance)
  "_javascript",
  "_jsx",
  "_typescript",
  "ecma",
  "jsx",
]);

/**
 * Normalize language name for directory lookup
 */
function normalizeLanguageName(language: string): string {
  // Map aliases to directory names
  if (language === "csharp") {
    return "c_sharp";
  }
  if (language === "tsx") {
    return "typescript"; // TSX uses typescript queries
  }
  return language;
}

/**
 * Get the path to a .scm query file
 */
export function getSCMPath(
  language: string,
  queryType: SCMQueryType,
): string | undefined {
  const langDir = normalizeLanguageName(language);
  const relativePath = join("queries", langDir, `${queryType}.scm`);

  if (assetExists(relativePath)) {
    return join(getAssetsDir(), relativePath);
  }

  return undefined;
}

/**
 * Parse inherit directives from SCM content
 * Supports: `; inherits: lang1,lang2` and `; inherits lang1`
 */
function parseInherits(content: string): string[] {
  const inherits: string[] = [];
  // Normalize line endings (handle CRLF and CR)
  const normalizedContent = content.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  const lines = normalizedContent.split("\n");

  for (const line of lines) {
    const match = /^;\s*inherits:?\s+([^\s].*)$/.exec(line);
    if (match?.[1]) {
      const langs = match[1].split(",").map((l) => l.trim());
      inherits.push(...langs);
    }
  }

  return inherits;
}

/**
 * Remove inherit directives from SCM content
 */
function removeInheritDirectives(content: string): string {
  // Normalize line endings (handle CRLF and CR)
  const normalizedContent = content.replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  return normalizedContent
    .split("\n")
    .filter((line) => !/^;\s*inherits:?\s+/.exec(line))
    .join("\n");
}

/**
 * Load a raw .scm file without resolving inheritance
 */
function loadRawSCM(
  language: string,
  queryType: SCMQueryType,
): string | undefined {
  const assetsDir = getAssetsDir();
  const scmPath = join(assetsDir, "queries", language, `${queryType}.scm`);

  if (!existsSync(scmPath)) {
    return undefined;
  }

  try {
    return readFileSync(scmPath, "utf-8");
  } catch {
    return undefined;
  }
}

/**
 * Load a .scm query file for a language with inheritance resolved
 *
 * @param language - Language name (e.g., "javascript", "python")
 * @param queryType - Type of query (e.g., "tags", "highlights")
 * @param visited - Set of visited languages to prevent circular inheritance
 * @returns Query string or undefined if not found
 */
export function loadSCMQuery(
  language: string,
  queryType: SCMQueryType,
  visited = new Set<string>(),
): string | undefined {
  const cacheKey = `${language}:${queryType}`;

  // Check cache first
  if (scmCache.has(cacheKey)) {
    return scmCache.get(cacheKey);
  }

  // Prevent circular inheritance
  if (visited.has(language)) {
    return undefined;
  }
  visited.add(language);

  // Normalize language name for file lookup
  const langDir = normalizeLanguageName(language);
  const rawContent = loadRawSCM(langDir, queryType);

  if (!rawContent) {
    return undefined;
  }

  // Parse inherits directives
  const inherits = parseInherits(rawContent);
  const ownContent = removeInheritDirectives(rawContent).trim();

  // Load inherited content
  const inheritedParts: string[] = [];
  for (const inheritLang of inherits) {
    const inheritedContent = loadSCMQuery(inheritLang, queryType, visited);
    if (inheritedContent) {
      inheritedParts.push(inheritedContent);
    }
  }

  // Combine inherited content with own content
  const finalContent = [...inheritedParts, ownContent]
    .filter(Boolean)
    .join("\n\n");

  if (finalContent) {
    scmCache.set(cacheKey, finalContent);
  }

  return finalContent || undefined;
}

/**
 * Load tags.scm for symbol extraction
 */
export function loadTagsQuery(language: string): string | undefined {
  return loadSCMQuery(language, "tags");
}

/**
 * Load highlights.scm for syntax highlighting
 */
export function loadHighlightsQuery(language: string): string | undefined {
  return loadSCMQuery(language, "highlights");
}

/**
 * Load locals.scm for local variable scoping
 */
export function loadLocalsQuery(language: string): string | undefined {
  return loadSCMQuery(language, "locals");
}

/**
 * Check which query types are available for a language
 */
export function getAvailableQueryTypes(language: string): SCMQueryType[] {
  const types: SCMQueryType[] = [
    "tags",
    "highlights",
    "locals",
    "injections",
    "indents",
    "folds",
  ];

  return types.filter((type) => getSCMPath(language, type) !== undefined);
}

/**
 * Check if a language has official tags.scm
 */
export function hasOfficialTags(language: string): boolean {
  return getSCMPath(language, "tags") !== undefined;
}

/**
 * Get all languages with official tags.scm
 */
export function getLanguagesWithTags(): string[] {
  return Array.from(SUPPORTED_LANGUAGES).filter(hasOfficialTags);
}

/**
 * Clear the SCM cache
 */
export function clearSCMCache(): void {
  scmCache.clear();
}

// Register cache for centralized clearing
registerCache("queries:scm", clearSCMCache);
