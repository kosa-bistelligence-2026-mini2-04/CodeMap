import { unlinkSync, writeFileSync } from "fs";
import { tmpdir } from "os";
import { join } from "path";
import { afterAll, beforeAll, describe, expect, test, vi } from "vitest";

import { hasContentSource, readContent } from "@features/utils";

describe("Content Utilities", () => {
  let tempFilePath: string;
  const testContent = "const x = 1;\nconst y = 2;";

  beforeAll(() => {
    tempFilePath = join(tmpdir(), `test-content-${String(Date.now())}.ts`);
    writeFileSync(tempFilePath, testContent);
  });

  afterAll(() => {
    try {
      unlinkSync(tempFilePath);
    } catch {
      // Ignore cleanup errors
    }
  });

  describe("readContent", () => {
    test("returns content when content string is provided", () => {
      const result = readContent(undefined, "test content");
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.content).toBe("test content");
      }
    });

    test("prefers content over file path when both provided", () => {
      const result = readContent(tempFilePath, "direct content");
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.content).toBe("direct content");
      }
    });

    test("reads content from file when only file path provided", () => {
      const result = readContent(tempFilePath);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.content).toBe(testContent);
      }
    });

    test("returns error for non-existent file", () => {
      const result = readContent("/non/existent/path.ts");
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toContain("Failed to read file");
      }
    });

    test("returns error when neither file path nor content provided", () => {
      const result = readContent();
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBe(
          "Either file_path or content must be provided",
        );
      }
    });

    test("handles empty string content", () => {
      const result = readContent(undefined, "");
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.content).toBe("");
      }
    });
  });

  describe("hasContentSource", () => {
    test("returns true when file path provided", () => {
      expect(hasContentSource("/some/path.ts")).toBe(true);
    });

    test("returns true when content provided", () => {
      expect(hasContentSource(undefined, "content")).toBe(true);
    });

    test("returns true when both provided", () => {
      expect(hasContentSource("/some/path.ts", "content")).toBe(true);
    });

    test("returns false when neither provided", () => {
      expect(hasContentSource()).toBe(false);
    });

    test("returns false when both undefined", () => {
      expect(hasContentSource(undefined, undefined)).toBe(false);
    });
  });
});

describe("Content Utilities - Error Handling", () => {
  test("handles non-Error thrown values", async () => {
    // Mock fs.readFileSync to throw a non-Error value
    vi.doMock("fs", () => ({
      readFileSync: () => {
        // eslint-disable-next-line @typescript-eslint/only-throw-error
        throw "string error"; // Throw a string instead of Error
      },
    }));

    vi.resetModules();
    const { readContent: freshReadContent } =
      await import("@features/utils/content");

    const result = freshReadContent("/some/path.ts");

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error).toContain("Failed to read file");
      expect(result.error).toContain("string error");
    }

    vi.doUnmock("fs");
    vi.resetModules();
  });

  test("handles thrown numbers", async () => {
    vi.doMock("fs", () => ({
      readFileSync: () => {
        // eslint-disable-next-line @typescript-eslint/only-throw-error
        throw 42; // Throw a number
      },
    }));

    vi.resetModules();
    const { readContent: freshReadContent } =
      await import("@features/utils/content");

    const result = freshReadContent("/some/path.ts");

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error).toContain("Failed to read file");
      expect(result.error).toContain("42");
    }

    vi.doUnmock("fs");
    vi.resetModules();
  });

  test("handles thrown objects", async () => {
    vi.doMock("fs", () => ({
      readFileSync: () => {
        // eslint-disable-next-line @typescript-eslint/only-throw-error
        throw { code: "EACCES", message: "Permission denied" };
      },
    }));

    vi.resetModules();
    const { readContent: freshReadContent } =
      await import("@features/utils/content");

    const result = freshReadContent("/some/path.ts");

    expect(result.success).toBe(false);
    if (!result.success) {
      expect(result.error).toContain("Failed to read file");
    }

    vi.doUnmock("fs");
    vi.resetModules();
  });
});
