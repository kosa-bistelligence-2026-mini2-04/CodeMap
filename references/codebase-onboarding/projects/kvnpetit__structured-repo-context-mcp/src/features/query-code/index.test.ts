import { afterEach, beforeEach, describe, expect, test } from "vitest";

import { resetParser } from "@core/parser";

import { execute, queryCodeSchema } from "@features/query-code";

describe("query_code feature", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  describe("schema validation", () => {
    test("accepts content with preset", () => {
      const result = queryCodeSchema.safeParse({
        content: "function test() {}",
        language: "javascript",
        preset: "functions",
      });
      expect(result.success).toBe(true);
    });

    test("accepts content with query", () => {
      const result = queryCodeSchema.safeParse({
        content: "function test() {}",
        language: "javascript",
        query: "(function_declaration) @func",
      });
      expect(result.success).toBe(true);
    });

    test("rejects without content or file_path", () => {
      const result = queryCodeSchema.safeParse({
        language: "javascript",
        preset: "functions",
      });
      expect(result.success).toBe(false);
    });

    test("rejects without query or preset", () => {
      const result = queryCodeSchema.safeParse({
        content: "function test() {}",
        language: "javascript",
      });
      expect(result.success).toBe(false);
    });
  });

  describe("execute with presets", () => {
    test("finds functions with preset", async () => {
      const result = await execute({
        content: `
          function hello() { return "world"; }
          const greet = (name) => "Hello " + name;
        `,
        language: "javascript",
        preset: "functions",
      });

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();

      const data = result.data as { count: number; matches: unknown[] };
      expect(data.count).toBeGreaterThan(0);
      expect(data.matches.length).toBeGreaterThan(0);
    });

    test("finds classes with preset", async () => {
      const result = await execute({
        content: `
          class MyClass {
            method() {}
          }
          class AnotherClass {}
        `,
        language: "javascript",
        preset: "classes",
      });

      expect(result.success).toBe(true);

      const data = result.data as { count: number };
      expect(data.count).toBe(2);
    });

    test("finds imports with preset", async () => {
      const result = await execute({
        content: `
          import { x } from 'module';
          import y from 'other';
        `,
        language: "javascript",
        preset: "imports",
      });

      expect(result.success).toBe(true);

      const data = result.data as { count: number };
      expect(data.count).toBeGreaterThan(0);
    });

    test("finds exports with preset", async () => {
      const result = await execute({
        content: `
          export const x = 1;
          export function hello() {}
        `,
        language: "javascript",
        preset: "exports",
      });

      expect(result.success).toBe(true);

      const data = result.data as { count: number };
      expect(data.count).toBeGreaterThan(0);
    });

    test("finds comments with preset", async () => {
      const result = await execute({
        content: `
          // Line comment
          const x = 1;
          /* Block comment */
        `,
        language: "javascript",
        preset: "comments",
      });

      expect(result.success).toBe(true);

      const data = result.data as { count: number };
      expect(data.count).toBe(2);
    });

    test("finds strings with preset", async () => {
      const result = await execute({
        content: `
          const a = "hello";
          const b = 'world';
        `,
        language: "javascript",
        preset: "strings",
      });

      expect(result.success).toBe(true);

      const data = result.data as { count: number };
      expect(data.count).toBe(2);
    });
  });

  describe("execute with custom query", () => {
    test("executes custom query", async () => {
      const result = await execute({
        content: "const x = 1; const y = 2;",
        language: "javascript",
        query: "(lexical_declaration) @decl",
      });

      expect(result.success).toBe(true);

      const data = result.data as { count: number };
      expect(data.count).toBe(2);
    });

    test("returns error for invalid query", async () => {
      const result = await execute({
        content: "const x = 1;",
        language: "javascript",
        query: "(invalid_pattern @x",
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain("Invalid query");
    });
  });

  describe("execute options", () => {
    test("respects max_matches", async () => {
      const result = await execute({
        content: `
          function a() {}
          function b() {}
          function c() {}
        `,
        language: "javascript",
        preset: "functions",
        max_matches: 1,
      });

      expect(result.success).toBe(true);

      const data = result.data as { count: number };
      expect(data.count).toBe(1);
    });
  });

  describe("language support", () => {
    test("works with TypeScript", async () => {
      const result = await execute({
        content: `
          interface User { name: string; }
          function greet(user: User): string { return user.name; }
        `,
        language: "typescript",
        preset: "functions",
      });

      expect(result.success).toBe(true);
    });

    test("works with Python", async () => {
      const result = await execute({
        content: `
def hello():
    return "world"

def greet(name):
    return f"Hello {name}"
        `,
        language: "python",
        preset: "functions",
      });

      expect(result.success).toBe(true);

      const data = result.data as { count: number };
      expect(data.count).toBeGreaterThan(0);
    });

    test("returns error for unsupported language", async () => {
      // JSON is not supported for tree-sitter parsing
      const result = await execute({
        content: '{"key": "value"}',
        language: "json",
        preset: "functions",
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain("Unsupported language");
    });
  });

  describe("error handling", () => {
    test("returns error when file not found", async () => {
      const result = await execute({
        file_path: "/non/existent/file.js",
        preset: "functions",
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain("Failed to read file");
    });

    test("returns error for query execution failure", async () => {
      // Using a preset that exists but the query pattern fails for JS
      const result = await execute({
        content: "const x = 1;",
        language: "javascript",
        preset: "types", // types preset pattern doesn't work well with JS
      });

      // Should fail during query execution
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });

    test("returns error for unavailable preset on language", async () => {
      // Svelte doesn't have functions preset in its available presets
      const result = await execute({
        content: "<script>let x = 1;</script>",
        language: "svelte",
        preset: "functions",
      });

      // Either fails because preset unavailable or query fails
      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });
  });

  describe("message formatting", () => {
    test("shows singular match for count of 1", async () => {
      const result = await execute({
        content: "function hello() {}",
        language: "javascript",
        preset: "functions",
        max_matches: 1,
      });

      expect(result.success).toBe(true);
      expect(result.message).toContain("1 match");
      expect(result.message).not.toContain("1 matches");
    });

    test("shows plural matches for count > 1", async () => {
      const result = await execute({
        content: `
          function a() {}
          function b() {}
        `,
        language: "javascript",
        preset: "functions",
      });

      expect(result.success).toBe(true);
      expect(result.message).toContain("matches");
    });
  });
});
