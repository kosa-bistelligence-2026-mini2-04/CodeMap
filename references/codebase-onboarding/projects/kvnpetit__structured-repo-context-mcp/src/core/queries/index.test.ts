import { afterEach, beforeEach, describe, expect, test } from "vitest";

import { parseCode, resetParser } from "@core/parser";
import {
  executePresetQuery,
  executeQuery,
  findClasses,
  findComments,
  findExports,
  findFunctions,
  findImports,
  findStrings,
  getAvailablePresets,
  getClassName,
  getFunctionName,
  getQueryPattern,
  getQuerySupportedLanguages,
  isPresetAvailable,
} from "@core/queries";

describe("Query Patterns", () => {
  test("getQueryPattern returns pattern for fallback language/preset", () => {
    // TypeScript has a fallback pattern for functions
    const pattern = getQueryPattern("typescript", "functions");
    expect(pattern).toBeDefined();
    expect(pattern).toContain("function_declaration");

    // Bash has a fallback pattern for functions
    const bashPattern = getQueryPattern("bash", "functions");
    expect(bashPattern).toBeDefined();
    expect(bashPattern).toContain("function_definition");
  });

  test("getQueryPattern returns undefined for language using official tags.scm", () => {
    // JavaScript uses official tags.scm, no fallback pattern
    const pattern = getQueryPattern("javascript", "functions");
    expect(pattern).toBeUndefined();
  });

  test("getQueryPattern returns undefined for unknown language", () => {
    const pattern = getQueryPattern("unknown", "functions");
    expect(pattern).toBeUndefined();
  });

  test("isPresetAvailable checks correctly for fallback patterns", () => {
    // TypeScript has a fallback pattern
    expect(isPresetAvailable("typescript", "functions")).toBe(true);
    // Bash has a fallback pattern
    expect(isPresetAvailable("bash", "functions")).toBe(true);
    // Unknown language has no patterns
    expect(isPresetAvailable("unknown", "functions")).toBe(false);
  });

  test("getAvailablePresets returns presets for language with official tags", () => {
    // JavaScript uses official tags.scm which provides functions, classes, plus generic patterns
    const presets = getAvailablePresets("javascript");
    expect(presets).toContain("functions");
    expect(presets).toContain("classes");
    expect(presets).toContain("imports");
    expect(presets).toContain("exports");
  });

  test("getQuerySupportedLanguages returns fallback languages", () => {
    // This returns languages with FALLBACK_PATTERNS, not all languages
    const languages = getQuerySupportedLanguages();
    expect(languages).toContain("typescript"); // Has incomplete official tags, needs fallback
    expect(languages).toContain("bash"); // No official tags
    expect(languages).toContain("json"); // No official tags
    expect(languages).toContain("yaml"); // No official tags
    // Languages with complete official tags are NOT in FALLBACK_PATTERNS
    expect(languages).not.toContain("python");
    expect(languages).not.toContain("go");
    expect(languages).not.toContain("rust");
  });
});

describe("Query Execution - JavaScript", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("executePresetQuery finds functions", async () => {
    const code = `
      function hello() { return "world"; }
      const greet = (name) => "Hello " + name;
    `;
    const result = await parseCode(code, { language: "javascript" });

    const queryResult = executePresetQuery(
      result.tree,
      result.languageInstance,
      "javascript",
      "functions",
    );

    expect(queryResult.count).toBeGreaterThan(0);
    expect(queryResult.matches.length).toBeGreaterThan(0);
  });

  test("executePresetQuery respects maxMatches", async () => {
    const code = `
      function a() {}
      function b() {}
      function c() {}
    `;
    const result = await parseCode(code, { language: "javascript" });

    const queryResult = executePresetQuery(
      result.tree,
      result.languageInstance,
      "javascript",
      "functions",
      { maxMatches: 1 },
    );

    expect(queryResult.count).toBe(1);
  });

  test("executeQuery throws for invalid query", async () => {
    const code = `const x = 1;`;
    const result = await parseCode(code, { language: "javascript" });

    expect(() =>
      executeQuery(
        result.tree,
        result.languageInstance,
        "(invalid_pattern @x",
        "javascript",
      ),
    ).toThrow("Invalid query");
  });

  test("executePresetQuery works with preset name", async () => {
    const code = `class MyClass { method() {} }`;
    const result = await parseCode(code, { language: "javascript" });

    const queryResult = executePresetQuery(
      result.tree,
      result.languageInstance,
      "javascript",
      "classes",
    );

    expect(queryResult.count).toBeGreaterThan(0);
  });

  test("executePresetQuery throws for unknown preset", async () => {
    const code = `const x = 1;`;
    const result = await parseCode(code, { language: "javascript" });

    expect(() =>
      executePresetQuery(
        result.tree,
        result.languageInstance,
        "unknown_lang",
        "functions",
      ),
    ).toThrow("No 'functions' query pattern available");
  });
});

describe("Query Execution - TypeScript", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("finds TypeScript functions", async () => {
    const code = `
      function greet(name: string): string { return name; }
      const add = (a: number, b: number): number => a + b;
    `;
    const result = await parseCode(code, { language: "typescript" });

    const queryResult = executePresetQuery(
      result.tree,
      result.languageInstance,
      "typescript",
      "functions",
    );

    expect(queryResult.count).toBeGreaterThan(0);
  });

  test("finds TypeScript interfaces", async () => {
    const code = `
      interface User { name: string; age: number; }
      type Config = { debug: boolean };
    `;
    const result = await parseCode(code, { language: "typescript" });

    const queryResult = executePresetQuery(
      result.tree,
      result.languageInstance,
      "typescript",
      "types",
    );

    expect(queryResult.count).toBeGreaterThan(0);
  });
});

describe("Query Execution - Python", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("finds Python functions", async () => {
    const code = `
def hello():
    return "world"

def greet(name):
    return f"Hello {name}"
    `;
    const result = await parseCode(code, { language: "python" });

    const queryResult = executePresetQuery(
      result.tree,
      result.languageInstance,
      "python",
      "functions",
    );

    expect(queryResult.count).toBeGreaterThan(0);
  });

  test("finds Python classes", async () => {
    const code = `
class MyClass:
    def method(self):
        pass
    `;
    const result = await parseCode(code, { language: "python" });

    const queryResult = executePresetQuery(
      result.tree,
      result.languageInstance,
      "python",
      "classes",
    );

    expect(queryResult.count).toBeGreaterThan(0);
  });
});

describe("Helper Functions", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("findFunctions extracts function nodes", async () => {
    const code = `
      function hello() {}
      const world = () => {};
    `;
    const result = await parseCode(code, { language: "javascript" });

    const functions = findFunctions(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(functions.length).toBeGreaterThan(0);
  });

  test("findClasses extracts class nodes", async () => {
    const code = `
      class A {}
      class B extends A {}
    `;
    const result = await parseCode(code, { language: "javascript" });

    const classes = findClasses(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(classes.length).toBe(2);
  });

  test("findImports extracts import nodes", async () => {
    const code = `
      import { x } from 'module';
      import y from 'other';
    `;
    const result = await parseCode(code, { language: "javascript" });

    const imports = findImports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(imports.length).toBe(2);
  });

  test("findExports extracts export nodes", async () => {
    const code = `
      export const x = 1;
      export function hello() {}
      export { y };
    `;
    const result = await parseCode(code, { language: "javascript" });

    const exports = findExports(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(exports.length).toBeGreaterThan(0);
  });

  test("findComments extracts comment nodes", async () => {
    const code = `
      // Line comment
      const x = 1;
      /* Block comment */
    `;
    const result = await parseCode(code, { language: "javascript" });

    const comments = findComments(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(comments.length).toBe(2);
  });

  test("findStrings extracts string nodes", async () => {
    const code = `
      const a = "hello";
      const b = 'world';
      const c = \`template\`;
    `;
    const result = await parseCode(code, { language: "javascript" });

    const strings = findStrings(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(strings.length).toBe(3);
  });
});

describe("Name Extraction", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  test("getFunctionName extracts function name", async () => {
    const code = `function myFunction() {}`;
    const result = await parseCode(code, { language: "javascript" });

    const functions = findFunctions(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(functions.length).toBeGreaterThan(0);
    const fn = functions[0];
    expect(fn).toBeDefined();
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion -- validated with expect().toBeDefined()
    const name = getFunctionName(fn!);
    expect(name).toBe("myFunction");
  });

  test("getFunctionName returns undefined for node without name", () => {
    const node = {
      type: "function_declaration",
      text: "function() {}",
      start: { line: 1, column: 0, offset: 0 },
      end: { line: 1, column: 13, offset: 13 },
      isNamed: true,
    };

    const name = getFunctionName(node);
    expect(name).toBeUndefined();
  });

  test("getFunctionName handles fields.name as array", () => {
    const node = {
      type: "function_declaration",
      text: "function test() {}",
      start: { line: 1, column: 0, offset: 0 },
      end: { line: 1, column: 18, offset: 18 },
      isNamed: true,
      fields: {
        name: [
          {
            type: "identifier",
            text: "test",
            start: { line: 1, column: 9, offset: 9 },
            end: { line: 1, column: 13, offset: 13 },
            isNamed: true,
          },
        ],
      },
    };

    // When name is array, should fall through to children
    const name = getFunctionName(node);
    expect(name).toBeUndefined();
  });

  test("getFunctionName finds property_identifier in children", () => {
    const node = {
      type: "method_definition",
      text: "myMethod() {}",
      start: { line: 1, column: 0, offset: 0 },
      end: { line: 1, column: 13, offset: 13 },
      isNamed: true,
      children: [
        {
          type: "property_identifier",
          text: "myMethod",
          start: { line: 1, column: 0, offset: 0 },
          end: { line: 1, column: 8, offset: 8 },
          isNamed: true,
        },
      ],
    };

    const name = getFunctionName(node);
    expect(name).toBe("myMethod");
  });

  test("getFunctionName finds field_identifier in children", () => {
    const node = {
      type: "method_definition",
      text: "myField() {}",
      start: { line: 1, column: 0, offset: 0 },
      end: { line: 1, column: 12, offset: 12 },
      isNamed: true,
      children: [
        {
          type: "field_identifier",
          text: "myField",
          start: { line: 1, column: 0, offset: 0 },
          end: { line: 1, column: 7, offset: 7 },
          isNamed: true,
        },
      ],
    };

    const name = getFunctionName(node);
    expect(name).toBe("myField");
  });

  test("getFunctionName recurses into function_declarator", () => {
    const node = {
      type: "function_definition",
      text: "void myFunc() {}",
      start: { line: 1, column: 0, offset: 0 },
      end: { line: 1, column: 16, offset: 16 },
      isNamed: true,
      children: [
        {
          type: "function_declarator",
          text: "myFunc()",
          start: { line: 1, column: 5, offset: 5 },
          end: { line: 1, column: 13, offset: 13 },
          isNamed: true,
          children: [
            {
              type: "identifier",
              text: "myFunc",
              start: { line: 1, column: 5, offset: 5 },
              end: { line: 1, column: 11, offset: 11 },
              isNamed: true,
            },
          ],
        },
      ],
    };

    const name = getFunctionName(node);
    expect(name).toBe("myFunc");
  });

  test("getClassName extracts class name", async () => {
    const code = `class MyClass {}`;
    const result = await parseCode(code, { language: "javascript" });

    const classes = findClasses(
      result.tree,
      result.languageInstance,
      "javascript",
    );

    expect(classes.length).toBe(1);
    const cls = classes[0];
    expect(cls).toBeDefined();
    // eslint-disable-next-line @typescript-eslint/no-non-null-assertion -- validated with expect().toBeDefined()
    const name = getClassName(cls!);
    expect(name).toBe("MyClass");
  });

  test("getClassName returns undefined for node without name", () => {
    const node = {
      type: "class_declaration",
      text: "class {}",
      start: { line: 1, column: 0, offset: 0 },
      end: { line: 1, column: 8, offset: 8 },
      isNamed: true,
    };

    const name = getClassName(node);
    expect(name).toBeUndefined();
  });

  test("getClassName handles fields.name as array", () => {
    const node = {
      type: "class_declaration",
      text: "class Test {}",
      start: { line: 1, column: 0, offset: 0 },
      end: { line: 1, column: 13, offset: 13 },
      isNamed: true,
      fields: {
        name: [
          {
            type: "identifier",
            text: "Test",
            start: { line: 1, column: 6, offset: 6 },
            end: { line: 1, column: 10, offset: 10 },
            isNamed: true,
          },
        ],
      },
    };

    // When name is array, should fall through to children
    const name = getClassName(node);
    expect(name).toBeUndefined();
  });

  test("getClassName finds type_identifier in children", () => {
    const node = {
      type: "class_declaration",
      text: "class MyType {}",
      start: { line: 1, column: 0, offset: 0 },
      end: { line: 1, column: 15, offset: 15 },
      isNamed: true,
      children: [
        {
          type: "type_identifier",
          text: "MyType",
          start: { line: 1, column: 6, offset: 6 },
          end: { line: 1, column: 12, offset: 12 },
          isNamed: true,
        },
      ],
    };

    const name = getClassName(node);
    expect(name).toBe("MyType");
  });
});
