/**
 * Core AST types for Tree-sitter parsing
 */

/**
 * Position in source code
 */
export interface Position {
  /** Line number (1-based) */
  line: number;
  /** Column number (0-based) */
  column: number;
  /** Byte offset in the source */
  offset: number;
}

/**
 * AST Node representation
 */
export interface ASTNode {
  /** Node type (e.g., function_declaration, class_definition) */
  type: string;
  /** Source text of this node */
  text: string;
  /** Start position */
  start: Position;
  /** End position */
  end: Position;
  /** Child nodes */
  children?: ASTNode[];
  /** Named fields (e.g., name, body, parameters) */
  fields?: Record<string, ASTNode | ASTNode[]>;
  /** Whether this is a named node */
  isNamed?: boolean;
}

/**
 * Symbol types that can be extracted from code
 */
export type SymbolType =
  | "function"
  | "class"
  | "variable"
  | "constant"
  | "interface"
  | "type"
  | "enum"
  | "method"
  | "property";

/**
 * Code symbol (function, class, variable, etc.)
 */
export interface Symbol {
  /** Symbol name */
  name: string;
  /** Symbol type */
  type: SymbolType;
  /** Start position */
  start: Position;
  /** End position */
  end: Position;
  /** Function/method signature (params and return type) */
  signature?: string;
  /** Modifiers (public, private, async, export, etc.) */
  modifiers?: string[];
  /** Documentation comment if present */
  documentation?: string;
}

/**
 * Import statement information
 */
export interface Import {
  /** Module/package being imported */
  source: string;
  /** Imported names (empty for side-effect imports) */
  names: ImportedName[];
  /** Whether this is a default import */
  isDefault?: boolean;
  /** Whether this is a namespace import (import * as X) */
  isNamespace?: boolean;
  /** Start position */
  start: Position;
  /** End position */
  end: Position;
}

/**
 * Single imported name
 */
export interface ImportedName {
  /** Original name in the module */
  name: string;
  /** Alias if renamed (import { x as y }) */
  alias?: string;
}

/**
 * Export statement information
 */
export interface Export {
  /** Exported name */
  name: string;
  /** Whether this is a default export */
  isDefault?: boolean;
  /** Whether this is a re-export (export { x } from 'y') */
  isReExport?: boolean;
  /** Source module for re-exports */
  source?: string;
  /** Start position */
  start: Position;
  /** End position */
  end: Position;
}

/**
 * Query match result
 */
export interface QueryMatch {
  /** Pattern index that matched */
  pattern: number;
  /** Captured nodes */
  captures: QueryCapture[];
}

/**
 * Single capture from a query
 */
export interface QueryCapture {
  /** Capture name (e.g., @function.name) */
  name: string;
  /** Captured AST node */
  node: ASTNode;
}

/**
 * File analysis result
 */
export interface FileAnalysis {
  /** File path */
  filePath: string;
  /** Detected language */
  language: string;
  /** Extracted symbols */
  symbols: Symbol[];
  /** Import statements */
  imports: Import[];
  /** Export statements */
  exports: Export[];
  /** Code metrics */
  metrics: CodeMetrics;
  /** Full AST (if requested) */
  ast?: ASTNode;
}

/**
 * Code metrics
 */
export interface CodeMetrics {
  /** Total lines */
  lines: number;
  /** Number of functions/methods */
  functions: number;
  /** Number of classes */
  classes: number;
  /** Number of imports */
  imports: number;
  /** Number of exports */
  exports: number;
}
