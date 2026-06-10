import { afterEach, beforeEach, describe, expect, test } from "vitest";

import { resetParser } from "@core/parser";

import { execute, parseAstSchema } from "@features/parse-ast";

describe("parse_ast feature", () => {
  beforeEach(() => {
    resetParser();
  });

  afterEach(() => {
    resetParser();
  });

  describe("schema validation", () => {
    test("accepts content with language", () => {
      const result = parseAstSchema.safeParse({
        content: "const x = 1;",
        language: "javascript",
      });
      expect(result.success).toBe(true);
    });

    test("accepts file_path", () => {
      const result = parseAstSchema.safeParse({
        file_path: "test.js",
      });
      expect(result.success).toBe(true);
    });

    test("rejects when neither file_path nor content provided", () => {
      const result = parseAstSchema.safeParse({
        language: "javascript",
      });
      expect(result.success).toBe(false);
    });

    test("accepts max_depth parameter", () => {
      const result = parseAstSchema.safeParse({
        content: "const x = 1;",
        language: "javascript",
        max_depth: 3,
      });
      expect(result.success).toBe(true);
    });
  });

  describe("execute", () => {
    test("parses JavaScript content", async () => {
      const result = await execute({
        content: "const x = 1;",
        language: "javascript",
      });

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();

      const data = result.data as {
        language: string;
        root: { type: string };
        node_count: number;
      };
      expect(data.language).toBe("javascript");
      expect(data.root.type).toBe("program");
      expect(data.node_count).toBeGreaterThan(0);
    });

    test("parses TypeScript content", async () => {
      const result = await execute({
        content: "function greet(name: string): string { return name; }",
        language: "typescript",
      });

      expect(result.success).toBe(true);

      const data = result.data as { language: string };
      expect(data.language).toBe("typescript");
    });

    test("parses Python content", async () => {
      const result = await execute({
        content: 'def hello():\n    return "world"',
        language: "python",
      });

      expect(result.success).toBe(true);

      const data = result.data as { language: string };
      expect(data.language).toBe("python");
    });

    test("respects max_depth parameter", async () => {
      const code = "function test() { const x = 1; }";

      const shallowResult = await execute({
        content: code,
        language: "javascript",
        max_depth: 1,
      });

      const deepResult = await execute({
        content: code,
        language: "javascript",
        max_depth: 10,
      });

      expect(shallowResult.success).toBe(true);
      expect(deepResult.success).toBe(true);

      const shallowRoot = (
        shallowResult.data as { root: { children?: unknown[] } }
      ).root;
      const deepRoot = (deepResult.data as { root: { children?: unknown[] } })
        .root;

      // Shallow should have children but they shouldn't have deeply nested children
      const hasDeepChildren = (
        node: { children?: unknown[] },
        depth: number,
      ): boolean => {
        if (depth > 2) {
          return true;
        }
        if (!node.children) {
          return false;
        }
        return node.children.some((child) =>
          hasDeepChildren(child as { children?: unknown[] }, depth + 1),
        );
      };

      expect(hasDeepChildren(shallowRoot, 0)).toBe(false);
      expect(hasDeepChildren(deepRoot, 0)).toBe(true);
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

    test("auto-detects language from file path when content provided", async () => {
      const result = await execute({
        content: "const x = 1;",
        file_path: "test.js",
      });

      expect(result.success).toBe(true);
      const data = result.data as { language: string };
      expect(data.language).toBe("javascript");
    });
  });
});
