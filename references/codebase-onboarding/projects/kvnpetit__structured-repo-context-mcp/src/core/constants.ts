/**
 * Core constants used across modules
 */

/**
 * Keywords to skip when extracting names from AST nodes
 * Used in symbol extraction to filter out language keywords
 */
export const SKIP_KEYWORDS = new Set([
  // Function keywords
  "function",
  "func",
  "fn",
  "def",
  "fun",
  "async",
  "export",
  "public",
  "private",
  "protected",
  "static",
  "abstract",
  "override",
  "final",
  "let",
  "const",
  "var",
  // Class keywords
  "class",
  "struct",
  "interface",
  "trait",
  "object",
  "enum",
  "type",
  "module",
  "namespace",
  "protocol",
  "extension",
  "impl",
]);

/**
 * Default chunk size for text splitting fallback
 */
export const DEFAULT_CHUNK_SIZE = 1000;

/**
 * Default chunk overlap for text splitting fallback
 */
export const DEFAULT_CHUNK_OVERLAP = 200;
