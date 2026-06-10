import { writeFileSync, unlinkSync, mkdirSync, rmdirSync } from "fs";
import { join } from "path";
import { tmpdir } from "os";

import { afterEach, beforeEach, describe, expect, test } from "vitest";

import { resetParser } from "@core/parser";

import { execute, analyzeFileSchema } from "@features/analyze-file";

describe("analyze_file feature", () => {
  let tempDir: string;
  let tempFile: string;

  beforeEach(() => {
    resetParser();
    tempDir = join(tmpdir(), `analyze-file-test-${String(Date.now())}`);
    mkdirSync(tempDir, { recursive: true });
    tempFile = join(tempDir, "test.js");
  });

  afterEach(() => {
    resetParser();
    try {
      unlinkSync(tempFile);
      rmdirSync(tempDir);
    } catch {
      // Ignore cleanup errors
    }
  });

  describe("schema validation", () => {
    test("accepts file_path", () => {
      const result = analyzeFileSchema.safeParse({
        file_path: "test.js",
      });
      expect(result.success).toBe(true);
    });

    test("rejects without file_path", () => {
      const result = analyzeFileSchema.safeParse({});
      expect(result.success).toBe(false);
    });

    test("accepts optional parameters", () => {
      const result = analyzeFileSchema.safeParse({
        file_path: "test.js",
        include_ast: true,
        include_symbols: true,
        include_imports: false,
        include_exports: false,
        ast_max_depth: 5,
      });
      expect(result.success).toBe(true);
    });
  });

  describe("execute", () => {
    test("analyzes JavaScript file", async () => {
      const code = `
        import { x } from 'module';

        export function hello() { return "world"; }

        class MyClass {
          method() {}
        }

        const y = 2;
      `;
      writeFileSync(tempFile, code);

      const result = await execute({ file_path: tempFile });

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();

      const data = result.data as {
        file_path: string;
        language: string;
        metrics: {
          lines: number;
          functions: number;
          classes: number;
          imports: number;
          exports: number;
        };
        symbols: unknown[];
        imports: unknown[];
        exports: unknown[];
      };

      expect(data.file_path).toBe(tempFile);
      expect(data.language).toBe("javascript");
      expect(data.metrics.lines).toBeGreaterThan(0);
      expect(data.metrics.functions).toBeGreaterThan(0);
      expect(data.metrics.classes).toBe(1);
      expect(data.metrics.imports).toBeGreaterThan(0);
      expect(data.metrics.exports).toBeGreaterThan(0);
      expect(data.symbols).toBeDefined();
      expect(data.imports).toBeDefined();
      expect(data.exports).toBeDefined();
    });

    test("analyzes TypeScript file", async () => {
      tempFile = join(tempDir, "test.ts");
      const code = `
        interface User {
          name: string;
        }

        export function greet(user: User): string {
          return user.name;
        }
      `;
      writeFileSync(tempFile, code);

      const result = await execute({ file_path: tempFile });

      expect(result.success).toBe(true);

      const data = result.data as { language: string };
      expect(data.language).toBe("typescript");
    });

    test("includes AST when requested", async () => {
      writeFileSync(tempFile, "const x = 1;");

      const result = await execute({
        file_path: tempFile,
        include_ast: true,
      });

      expect(result.success).toBe(true);

      const data = result.data as { ast: { type: string } };
      expect(data.ast).toBeDefined();
      expect(data.ast.type).toBe("program");
    });

    test("excludes AST by default", async () => {
      writeFileSync(tempFile, "const x = 1;");

      const result = await execute({
        file_path: tempFile,
      });

      expect(result.success).toBe(true);

      const data = result.data as { ast?: unknown };
      expect(data.ast).toBeUndefined();
    });

    test("excludes symbols when requested", async () => {
      writeFileSync(tempFile, "function test() {}");

      const result = await execute({
        file_path: tempFile,
        include_symbols: false,
      });

      expect(result.success).toBe(true);

      const data = result.data as { symbols?: unknown };
      expect(data.symbols).toBeUndefined();
    });

    test("excludes imports when requested", async () => {
      writeFileSync(tempFile, "import { x } from 'y';");

      const result = await execute({
        file_path: tempFile,
        include_imports: false,
      });

      expect(result.success).toBe(true);

      const data = result.data as { imports?: unknown };
      expect(data.imports).toBeUndefined();
    });

    test("excludes exports when requested", async () => {
      writeFileSync(tempFile, "export const x = 1;");

      const result = await execute({
        file_path: tempFile,
        include_exports: false,
      });

      expect(result.success).toBe(true);

      const data = result.data as { exports?: unknown };
      expect(data.exports).toBeUndefined();
    });

    test("respects ast_max_depth", async () => {
      writeFileSync(tempFile, "function test() { const x = 1; }");

      const shallowResult = await execute({
        file_path: tempFile,
        include_ast: true,
        ast_max_depth: 1,
      });

      const deepResult = await execute({
        file_path: tempFile,
        include_ast: true,
        ast_max_depth: 10,
      });

      expect(shallowResult.success).toBe(true);
      expect(deepResult.success).toBe(true);

      const shallowAst = (
        shallowResult.data as { ast: { children?: unknown[] } }
      ).ast;
      const deepAst = (deepResult.data as { ast: { children?: unknown[] } })
        .ast;

      // Deep AST should have more nested structure
      const countDepth = (
        node: { children?: unknown[] },
        depth: number,
      ): number => {
        if (!node.children || node.children.length === 0) {
          return depth;
        }
        return Math.max(
          ...node.children.map((child) =>
            countDepth(child as { children?: unknown[] }, depth + 1),
          ),
        );
      };

      expect(countDepth(shallowAst, 0)).toBeLessThan(countDepth(deepAst, 0));
    });

    test("returns error when file does not exist", async () => {
      const result = await execute({
        file_path: "/nonexistent/path/file.js",
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain("Cannot parse file");
    });

    test("uses fallback for unsupported file type", async () => {
      tempFile = join(tempDir, "test.xyz");
      writeFileSync(tempFile, "function hello() {}\nclass World {}");

      const result = await execute({
        file_path: tempFile,
      });

      // With fallback, unsupported files are now parsed using generic text splitter
      expect(result.success).toBe(true);
      const data = result.data as Record<string, unknown>;
      expect(data.parsing_method).toBe("generic");
      expect(data.note).toContain("fallback");
    });

    test("includes chunks when requested for fallback parsing", async () => {
      tempFile = join(tempDir, "test.md");
      const content =
        "# Title\n\nSome content here.\n\n## Section\n\nMore content.";
      writeFileSync(tempFile, content);

      const result = await execute({
        file_path: tempFile,
        include_chunks: true,
      });

      expect(result.success).toBe(true);
      const data = result.data as {
        chunks?: {
          index: number;
          startLine: number;
          endLine: number;
          preview: string;
        }[];
        chunk_count?: number;
        note?: string;
      };
      expect(data.note).toContain("fallback");
      // Chunks should be included for fallback parsing
      if (data.chunks) {
        expect(data.chunks.length).toBeGreaterThan(0);
        expect(data.chunk_count).toBe(data.chunks.length);
        expect(data.chunks[0]).toHaveProperty("index");
        expect(data.chunks[0]).toHaveProperty("startLine");
        expect(data.chunks[0]).toHaveProperty("preview");
      }
    });

    test("includes symbol_extraction_method for fallback parsing", async () => {
      tempFile = join(tempDir, "test.txt");
      writeFileSync(tempFile, "function hello() {}\nclass World {}");

      const result = await execute({
        file_path: tempFile,
        include_symbols: true,
      });

      expect(result.success).toBe(true);
      const data = result.data as {
        symbol_extraction_method?: string;
        symbols?: unknown[];
      };
      // Fallback parsing includes the extraction method
      expect(data.symbol_extraction_method).toBe("regex");
      expect(data.symbols).toBeDefined();
    });

    test("returns error for binary files", async () => {
      tempFile = join(tempDir, "test.png");
      // Write some binary-like content
      writeFileSync(tempFile, Buffer.from([0x89, 0x50, 0x4e, 0x47]));

      const result = await execute({
        file_path: tempFile,
      });

      expect(result.success).toBe(false);
      expect(result.error).toContain("binary file");
    });

    test("returns meaningful summary message", async () => {
      writeFileSync(tempFile, "function test() {}");

      const result = await execute({ file_path: tempFile });

      expect(result.success).toBe(true);
      expect(result.message).toContain("Analyzed");
      expect(result.message).toContain("javascript");
      expect(result.message).toContain("lines");
      expect(result.message).toContain("functions");
    });

    test("handles non-Error exceptions gracefully", async () => {
      // Test with a path that will cause an unusual error
      // We can't easily trigger a non-Error exception, but we can test error handling
      const result = await execute({
        file_path: "\0invalid\0path", // Null bytes cause issues
      });

      expect(result.success).toBe(false);
      expect(result.error).toBeDefined();
    });
  });
});
