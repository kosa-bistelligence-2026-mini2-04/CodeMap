/**
 * Fallback SCM query patterns for languages without official tags.scm
 */

export type QueryPreset =
  | "functions"
  | "classes"
  | "imports"
  | "exports"
  | "comments"
  | "strings"
  | "variables"
  | "types";

const GENERIC_PATTERNS: Partial<Record<QueryPreset, string>> = {
  comments: `[(comment) @comment]`,
  strings: `[(string) @string (template_string) @string]`,
  imports: `(import_statement) @import.statement`,
  exports: `(export_statement) @export.statement`,
  variables: `[
    (variable_declaration (variable_declarator name: (identifier) @variable.name) @variable.declaration)
    (lexical_declaration (variable_declarator name: (identifier) @variable.name) @variable.declaration)
  ]`,
  types: `[
    (type_alias_declaration name: (type_identifier) @type.alias) @type.definition
    (enum_declaration name: (identifier) @enum.name) @enum.definition
  ]`,
};

export const FALLBACK_PATTERNS: Record<
  string,
  Partial<Record<QueryPreset, string>>
> = {
  typescript: {
    functions: `[
      (function_declaration name: (identifier) @function.name) @function.definition
      (method_definition name: (property_identifier) @function.name) @function.definition
      (lexical_declaration (variable_declarator name: (identifier) @function.name value: [(arrow_function) (function_expression)]) @function.definition)
    ]`,
  },
  json: { strings: `[(string) @string]` },
  yaml: {
    strings: `[(string_scalar) @string (double_quote_scalar) @string (single_quote_scalar) @string]`,
    comments: `[(comment) @comment]`,
  },
  toml: { strings: `[(string) @string]`, comments: `[(comment) @comment]` },
  bash: {
    functions: `(function_definition name: (word) @function.name) @function.definition`,
    comments: `[(comment) @comment]`,
    strings: `[(string) @string (raw_string) @string]`,
    variables: `(variable_assignment name: (variable_name) @variable.name) @variable.declaration`,
  },
  html: {
    strings: `[(attribute_value) @string (quoted_attribute_value) @string]`,
    comments: `[(comment) @comment]`,
  },
  css: {
    comments: `[(comment) @comment]`,
    strings: `[(string_value) @string]`,
  },
  scala: {
    functions: `(function_definition (identifier) @function.name) @function.definition`,
    classes: `[
      (class_definition (identifier) @class.name) @class.definition
      (object_definition (identifier) @class.name) @class.definition
      (trait_definition (identifier) @class.name) @class.definition
    ]`,
    comments: `[(comment) @comment]`,
    strings: `[(string) @string]`,
  },
  swift: {
    functions: `[
      (function_declaration (simple_identifier) @function.name) @function.definition
      (init_declaration) @function.definition
    ]`,
    classes: `[
      (class_declaration (type_identifier) @class.name) @class.definition
      (protocol_declaration (type_identifier) @class.name) @class.definition
    ]`,
    comments: `[(comment) @comment (multiline_comment) @comment]`,
    strings: `[(line_string_literal) @string]`,
  },
  ocaml: {
    functions: `(value_definition (let_binding (value_name) @function.name)) @function.definition`,
    classes: `[
      (type_definition (type_binding (type_constructor) @class.name)) @class.definition
      (module_definition (module_binding (module_name) @class.name)) @class.definition
    ]`,
    comments: `[(comment) @comment]`,
    strings: `[(string) @string]`,
  },
  svelte: {
    comments: `[(comment) @comment]`,
    strings: `[(attribute_value) @string (quoted_attribute_value) @string]`,
  },
};

export function getQueryPattern(
  language: string,
  preset: QueryPreset,
): string | undefined {
  return FALLBACK_PATTERNS[language]?.[preset] ?? GENERIC_PATTERNS[preset];
}

export function isPresetAvailable(
  language: string,
  preset: QueryPreset,
): boolean {
  return getQueryPattern(language, preset) !== undefined;
}

export function getAvailablePresets(
  language: string,
  hasOfficialTagsFile = false,
): QueryPreset[] {
  const presets: QueryPreset[] = hasOfficialTagsFile
    ? ["functions", "classes"]
    : [];
  const allPresets: QueryPreset[] = [
    "functions",
    "classes",
    "imports",
    "exports",
    "comments",
    "strings",
    "variables",
    "types",
  ];

  for (const preset of allPresets) {
    if (!presets.includes(preset) && isPresetAvailable(language, preset)) {
      presets.push(preset);
    }
  }
  return presets;
}

export function getQuerySupportedLanguages(): string[] {
  return Object.keys(FALLBACK_PATTERNS);
}
