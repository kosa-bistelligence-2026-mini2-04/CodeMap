import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import {
  clearCrossFileCache,
  getCrossFileCacheStats,
  resolveCrossFileContext,
} from "@core/embeddings/crossfile";
import type { Import } from "@core/ast/types";

// Mock logger
vi.mock("@utils", () => ({
  logger: {
    debug: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    error: vi.fn(),
  },
}));

describe("crossfile", () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "crossfile-test-"));
    clearCrossFileCache();
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
    clearCrossFileCache();
  });

  const createFile = (relativePath: string, content: string): string => {
    const fullPath = path.join(tempDir, relativePath);
    const dir = path.dirname(fullPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(fullPath, content);
    return fullPath;
  };

  describe("resolveCrossFileContext", () => {
    test("resolves relative imports", async () => {
      // Create a file with exported function
      createFile(
        "utils/helpers.ts",
        `export function formatDate(date: Date): string {
  return date.toISOString();
}

export function parseDate(str: string): Date {
  return new Date(str);
}`,
      );

      // Create the main file
      const mainFile = createFile(
        "src/index.ts",
        `import { formatDate } from "../utils/helpers";`,
      );

      const imports: Import[] = [
        {
          source: "../utils/helpers",
          names: [{ name: "formatDate" }],
          start: { line: 1, column: 0, offset: 0 },
          end: { line: 1, column: 50, offset: 50 },
        },
      ];

      const context = await resolveCrossFileContext(imports, mainFile, {
        projectRoot: tempDir,
      });

      expect(context.resolvedImports).toHaveLength(1);
      expect(context.resolvedImports[0]?.resolvedPath).not.toBeNull();
      expect(context.resolvedImports[0]?.symbols.length).toBeGreaterThan(0);
    });

    test("resolves path aliases", async () => {
      // Create a file with exported function
      createFile(
        "src/core/parser.ts",
        `export function parseCode(code: string): object {
  return { parsed: true };
}`,
      );

      // Create the main file
      const mainFile = createFile(
        "src/features/search.ts",
        `import { parseCode } from "@core/parser";`,
      );

      const imports: Import[] = [
        {
          source: "@core/parser",
          names: [{ name: "parseCode" }],
          start: { line: 1, column: 0, offset: 0 },
          end: { line: 1, column: 50, offset: 50 },
        },
      ];

      const context = await resolveCrossFileContext(imports, mainFile, {
        projectRoot: tempDir,
        pathAliases: { "@core": "src/core" },
      });

      expect(context.resolvedImports).toHaveLength(1);
      expect(context.resolvedImports[0]?.resolvedPath).toContain("parser.ts");
    });

    test("resolves index files", async () => {
      // Create index file
      createFile("src/utils/index.ts", `export function helper(): void {}`);

      const mainFile = createFile(
        "src/main.ts",
        `import { helper } from "./utils";`,
      );

      const imports: Import[] = [
        {
          source: "./utils",
          names: [{ name: "helper" }],
          start: { line: 1, column: 0, offset: 0 },
          end: { line: 1, column: 40, offset: 40 },
        },
      ];

      const context = await resolveCrossFileContext(imports, mainFile, {
        projectRoot: tempDir,
      });

      expect(context.resolvedImports[0]?.resolvedPath).toContain("index.ts");
    });

    test("skips external packages", async () => {
      const mainFile = createFile("src/main.ts", `import { z } from "zod";`);

      const imports: Import[] = [
        {
          source: "zod",
          names: [{ name: "z" }],
          start: { line: 1, column: 0, offset: 0 },
          end: { line: 1, column: 30, offset: 30 },
        },
      ];

      const context = await resolveCrossFileContext(imports, mainFile, {
        projectRoot: tempDir,
      });

      expect(context.resolvedImports[0]?.resolvedPath).toBeNull();
    });

    test("handles namespace imports", async () => {
      createFile(
        "lib.ts",
        `export function a(): void {}
export function b(): void {}
export const c = 1;`,
      );

      const mainFile = createFile("main.ts", `import * as lib from "./lib";`);

      const imports: Import[] = [
        {
          source: "./lib",
          names: [],
          isNamespace: true,
          start: { line: 1, column: 0, offset: 0 },
          end: { line: 1, column: 35, offset: 35 },
        },
      ];

      const context = await resolveCrossFileContext(imports, mainFile, {
        projectRoot: tempDir,
      });

      // Should include all exported symbols
      expect(context.resolvedImports[0]?.symbols.length).toBeGreaterThan(0);
    });

    test("limits number of imports", async () => {
      // Create multiple files
      for (let i = 0; i < 15; i++) {
        createFile(
          `lib${String(i)}.ts`,
          `export function fn${String(i)}(): void {}`,
        );
      }

      const mainFile = createFile("main.ts", "");

      const imports: Import[] = Array.from({ length: 15 }, (_, i) => ({
        source: `./lib${String(i)}`,
        names: [{ name: `fn${String(i)}` }],
        start: { line: 1, column: 0, offset: 0 },
        end: { line: 1, column: 30, offset: 30 },
      }));

      const context = await resolveCrossFileContext(imports, mainFile, {
        projectRoot: tempDir,
        maxImports: 5,
      });

      expect(context.resolvedImports).toHaveLength(5);
    });

    test("builds summary of imported symbols", async () => {
      createFile(
        "utils.ts",
        `export function formatDate(date: Date): string {
  return date.toISOString();
}`,
      );

      const mainFile = createFile(
        "main.ts",
        `import { formatDate } from "./utils";`,
      );

      const imports: Import[] = [
        {
          source: "./utils",
          names: [{ name: "formatDate" }],
          start: { line: 1, column: 0, offset: 0 },
          end: { line: 1, column: 45, offset: 45 },
        },
      ];

      const context = await resolveCrossFileContext(imports, mainFile, {
        projectRoot: tempDir,
      });

      expect(context.importedSymbolsSummary).toContain("formatDate");
      expect(context.importedSymbolsSummary).toContain("./utils");
    });

    test("handles unresolvable imports gracefully", async () => {
      const mainFile = createFile(
        "main.ts",
        `import { foo } from "./nonexistent";`,
      );

      const imports: Import[] = [
        {
          source: "./nonexistent",
          names: [{ name: "foo" }],
          start: { line: 1, column: 0, offset: 0 },
          end: { line: 1, column: 40, offset: 40 },
        },
      ];

      const context = await resolveCrossFileContext(imports, mainFile, {
        projectRoot: tempDir,
      });

      expect(context.resolvedImports[0]?.resolvedPath).toBeNull();
      expect(context.resolvedImports[0]?.symbols).toHaveLength(0);
    });
  });

  describe("cache management", () => {
    test("clearCrossFileCache clears the cache", async () => {
      createFile("lib.ts", `export function fn(): void {}`);
      const mainFile = createFile("main.ts", `import { fn } from "./lib";`);

      const imports: Import[] = [
        {
          source: "./lib",
          names: [{ name: "fn" }],
          start: { line: 1, column: 0, offset: 0 },
          end: { line: 1, column: 30, offset: 30 },
        },
      ];

      await resolveCrossFileContext(imports, mainFile, {
        projectRoot: tempDir,
      });

      const statsBefore = getCrossFileCacheStats();
      expect(statsBefore.files).toBeGreaterThan(0);

      clearCrossFileCache();

      const statsAfter = getCrossFileCacheStats();
      expect(statsAfter.files).toBe(0);
    });

    test("getCrossFileCacheStats returns cache info", async () => {
      createFile("a.ts", `export const a = 1;`);
      createFile("b.ts", `export const b = 2;`);
      const mainFile = createFile(
        "main.ts",
        `import { a } from "./a"; import { b } from "./b";`,
      );

      const imports: Import[] = [
        {
          source: "./a",
          names: [{ name: "a" }],
          start: { line: 1, column: 0, offset: 0 },
          end: { line: 1, column: 25, offset: 25 },
        },
        {
          source: "./b",
          names: [{ name: "b" }],
          start: { line: 1, column: 26, offset: 26 },
          end: { line: 1, column: 51, offset: 51 },
        },
      ];

      await resolveCrossFileContext(imports, mainFile, {
        projectRoot: tempDir,
      });

      const stats = getCrossFileCacheStats();
      expect(stats.files).toBe(2);
      expect(stats.entries).toHaveLength(2);
    });
  });
});
