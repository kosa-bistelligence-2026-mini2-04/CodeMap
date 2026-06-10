import { afterEach, beforeEach, describe, expect, test } from "vitest";

import { resetParser } from "@core/parser";

import { execute, listSymbolsSchema } from "@features/list-symbols";

describe("list_symbols feature", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  describe("schema validation", () => {
    test("accepts content with language", () => {
      const result = listSymbolsSchema.safeParse({
        content: "function test() {}",
        language: "javascript",
      });
      expect(result.success).toBe(true);
    });

    test("accepts file_path", () => {
      const result = listSymbolsSchema.safeParse({
        file_path: "test.js",
      });
      expect(result.success).toBe(true);
    });

    test("rejects without content or file_path", () => {
      const result = listSymbolsSchema.safeParse({
        language: "javascript",
      });
      expect(result.success).toBe(false);
    });

    test("accepts types filter", () => {
      const result = listSymbolsSchema.safeParse({
        content: "function test() {}",
        language: "javascript",
        types: ["function", "class"],
      });
      expect(result.success).toBe(true);
    });
  });

  describe("execute", () => {
    test("extracts JavaScript symbols", async () => {
      const result = await execute({
        content: `
          function hello() { return "world"; }
          class MyClass {
            method() {}
          }
          const x = 1;
        `,
        language: "javascript",
      });

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();

      const data = result.data as {
        symbols: { name: string; type: string }[];
        summary: { total: number; functions: number; classes: number };
        language: string;
      };

      expect(data.language).toBe("javascript");
      expect(data.summary.total).toBeGreaterThan(0);
      expect(data.summary.functions).toBeGreaterThan(0);
      expect(data.summary.classes).toBe(1);
    });

    test("extracts TypeScript symbols including interfaces", async () => {
      const result = await execute({
        content: `
          interface User {
            name: string;
            age: number;
          }

          type Config = { debug: boolean };

          function greet(user: User): string {
            return user.name;
          }
        `,
        language: "typescript",
      });

      expect(result.success).toBe(true);

      const data = result.data as {
        summary: { interfaces: number; types: number; functions: number };
      };

      expect(data.summary.interfaces).toBe(1);
      expect(data.summary.types).toBe(1);
      expect(data.summary.functions).toBeGreaterThan(0);
    });

    test("extracts Python symbols", async () => {
      const result = await execute({
        content: `
def hello():
    return "world"

class MyClass:
    def method(self):
        pass
        `,
        language: "python",
      });

      expect(result.success).toBe(true);

      const data = result.data as {
        summary: { functions: number; classes: number };
      };

      expect(data.summary.functions).toBeGreaterThan(0);
      expect(data.summary.classes).toBe(1);
    });

    test("filters by symbol type", async () => {
      const result = await execute({
        content: `
          function hello() {}
          class MyClass {}
          const x = 1;
        `,
        language: "javascript",
        types: ["function"],
      });

      expect(result.success).toBe(true);

      const data = result.data as {
        symbols: { type: string }[];
      };

      // Should only have function symbols
      expect(data.symbols.every((s) => s.type === "function")).toBe(true);
    });

    test("filters by multiple types", async () => {
      const result = await execute({
        content: `
          function hello() {}
          class MyClass {}
          const x = 1;
        `,
        language: "javascript",
        types: ["function", "class"],
      });

      expect(result.success).toBe(true);

      const data = result.data as {
        symbols: { type: string }[];
      };

      // Should have only function or class symbols
      expect(
        data.symbols.every((s) => s.type === "function" || s.type === "class"),
      ).toBe(true);
    });

    test("includes symbol location information", async () => {
      const result = await execute({
        content: "function hello() {}",
        language: "javascript",
      });

      expect(result.success).toBe(true);

      const data = result.data as {
        symbols: {
          name: string;
          start: { line: number; column: number };
          end: { line: number; column: number };
        }[];
      };

      expect(data.symbols.length).toBeGreaterThan(0);
      const symbol = data.symbols[0];
      expect(symbol).toBeDefined();
      expect(symbol?.start).toBeDefined();
      expect(symbol?.start.line).toBe(1);
      expect(symbol?.end).toBeDefined();
    });

    test("returns error for unsupported language", async () => {
      const result = await execute({
        content: "some code",
        language: "unsupported",
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain("Unsupported language");
    });

    test("returns error when file does not exist", async () => {
      const result = await execute({
        file_path: "/nonexistent/path/file.js",
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain("Failed to read file");
    });
  });
});
