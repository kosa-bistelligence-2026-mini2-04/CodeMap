import { describe, expect, test } from "vitest";

import {
  clearConfigCache,
  getSeparators,
  getTextSplitterLanguage,
  isTextSplitterLanguage,
  splitCode,
} from "@core/fallback";

// ============================================================
// TEST DATA
// ============================================================

const SUPPORTED_LANGUAGES = [
  "javascript",
  "typescript",
  "python",
  "go",
  "rust",
  "java",
];
const DIRECT_LANGUAGES = ["js", "cpp", "html"];
const GENERIC_LANGUAGES = ["json", "yaml", "bash", "vue", "dockerfile"];
const UNSUPPORTED_LANGUAGES = ["unknown", "brainfuck"];

const CODE_SAMPLES = {
  javascript: `
function hello() {
  return "world";
}

function greet(name) {
  return "Hello " + name;
}

class MyClass {
  constructor() {
    this.value = 1;
  }

  method() {
    return this.value;
  }
}`.trim(),

  python: `
def hello():
    return "world"

def greet(name):
    return f"Hello {name}"

class MyClass:
    def __init__(self):
        self.value = 1`.trim(),

  json: `{
  "name": "test",
  "version": "1.0.0"
}`,
};

// ============================================================
// LANGUAGE DETECTION
// ============================================================

describe("Text Splitter Fallback", () => {
  describe("isTextSplitterLanguage", () => {
    test.each(SUPPORTED_LANGUAGES)("returns true for %s", (lang) => {
      expect(isTextSplitterLanguage(lang)).toBe(true);
    });

    test.each(DIRECT_LANGUAGES)("returns true for direct name %s", (lang) => {
      expect(isTextSplitterLanguage(lang)).toBe(true);
    });

    test.each(GENERIC_LANGUAGES)("returns true for generic %s", (lang) => {
      expect(isTextSplitterLanguage(lang)).toBe(true);
    });

    test.each(UNSUPPORTED_LANGUAGES)("returns false for %s", (lang) => {
      expect(isTextSplitterLanguage(lang)).toBe(false);
    });
  });

  describe("getTextSplitterLanguage", () => {
    test.each([
      ["javascript", "js"],
      ["typescript", "js"],
      ["python", "python"],
      ["c", "cpp"],
      ["markdown", "markdown"],
    ])("maps %s to %s", (input, expected) => {
      expect(getTextSplitterLanguage(input)).toBe(expected);
    });

    test.each([
      ["cpp", "cpp"],
      ["html", "html"],
      ["latex", "latex"],
    ])("returns %s directly (in supported list)", (lang, expected) => {
      expect(getTextSplitterLanguage(lang)).toBe(expected);
    });

    test.each(GENERIC_LANGUAGES)("returns undefined for generic %s", (lang) => {
      expect(getTextSplitterLanguage(lang)).toBeUndefined();
    });

    test("returns undefined for unsupported language", () => {
      expect(getTextSplitterLanguage("unknown")).toBeUndefined();
    });
  });

  // ============================================================
  // CACHE MANAGEMENT
  // ============================================================

  describe("clearConfigCache", () => {
    test("clears cache without throwing", () => {
      expect(() => {
        clearConfigCache();
      }).not.toThrow();
      expect(() => {
        clearConfigCache();
      }).not.toThrow();
    });

    test("config reloads correctly after clear", () => {
      clearConfigCache();
      expect(isTextSplitterLanguage("javascript")).toBe(true);
      expect(getTextSplitterLanguage("javascript")).toBe("js");
    });
  });

  // ============================================================
  // SEPARATORS
  // ============================================================

  describe("getSeparators", () => {
    test("returns function/class separators for JavaScript", () => {
      const seps = getSeparators("javascript");
      expect(seps).toContain("\nfunction ");
      expect(seps).toContain("\nclass ");
      expect(seps.length).toBeGreaterThan(5);
    });

    test("returns def/class separators for Python", () => {
      const seps = getSeparators("python");
      expect(seps).toContain("\ndef ");
      expect(seps).toContain("\nclass ");
    });

    test.each(["json", "unknown"])("returns empty array for %s", (lang) => {
      expect(getSeparators(lang)).toEqual([]);
    });
  });

  // ============================================================
  // CODE SPLITTING
  // ============================================================

  describe("splitCode", () => {
    test("splits JavaScript code into chunks", async () => {
      const result = await splitCode(CODE_SAMPLES.javascript, "javascript", {
        chunkSize: 100,
        chunkOverlap: 20,
      });

      expect(result).toMatchObject({
        method: "text-splitter",
        language: "javascript",
      });
      expect(result.chunks.length).toBeGreaterThan(0);
      expect(result.count).toBe(result.chunks.length);
    });

    test("chunks have correct structure", async () => {
      const result = await splitCode(
        "function test() { return 1; }",
        "javascript",
      );

      expect(result.chunks.length).toBeGreaterThan(0);

      const firstChunk = result.chunks[0];
      expect(firstChunk).toBeDefined();
      expect(firstChunk).toHaveProperty("content");
      expect(firstChunk).toHaveProperty("startLine");
      expect(firstChunk).toHaveProperty("endLine");
      expect(firstChunk).toHaveProperty("index");

      if (firstChunk) {
        expect(firstChunk.startLine).toBeGreaterThanOrEqual(1);
      }
    });

    test("splits Python code correctly", async () => {
      const result = await splitCode(CODE_SAMPLES.python, "python", {
        chunkSize: 80,
        chunkOverlap: 10,
      });

      expect(result.language).toBe("python");
      expect(result.chunks.length).toBeGreaterThan(0);
    });

    test("works with generic language (JSON)", async () => {
      const result = await splitCode(CODE_SAMPLES.json, "json");

      expect(result).toMatchObject({
        method: "text-splitter",
        language: "json",
      });
      expect(result.chunks.length).toBeGreaterThan(0);
    });

    test("works with unsupported language", async () => {
      const result = await splitCode(CODE_SAMPLES.javascript, "unknown-lang");

      expect(result.method).toBe("text-splitter");
      expect(result.chunks.length).toBeGreaterThan(0);
    });

    test("calculates line numbers correctly", async () => {
      const code = "line 1\nline 2\nline 3\nline 4\nline 5";
      const result = await splitCode(code, "text", {
        chunkSize: 20,
        chunkOverlap: 0,
      });

      expect(result.chunks.length).toBeGreaterThan(0);
      expect(result.chunks[0]?.startLine).toBe(1);
    });
  });
});
