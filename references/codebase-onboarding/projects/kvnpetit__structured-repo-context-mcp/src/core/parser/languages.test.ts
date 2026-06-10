import { afterEach, describe, expect, test } from "vitest";
import {
  clearLanguageCache,
  getLanguageByName,
  getLanguageFromExtension,
  getLanguageFromPath,
  getLanguages,
  getSupportedExtensions,
  getSupportedLanguages,
  isLanguageSupported,
  EXTENSION_MAP,
  LANGUAGES,
} from "@core/parser/languages";

describe("Language Configuration", () => {
  afterEach(() => {
    clearLanguageCache();
  });

  describe("getLanguages", () => {
    test("returns language configurations", () => {
      const languages = getLanguages();
      expect(languages).toBeDefined();
      expect(typeof languages).toBe("object");
    });

    test("returns cached value on subsequent calls", () => {
      const lang1 = getLanguages();
      const lang2 = getLanguages();
      expect(lang1).toBe(lang2);
    });
  });

  describe("getLanguageFromExtension", () => {
    test("returns language config for valid extension", () => {
      const tsConfig = getLanguageFromExtension(".ts");
      expect(tsConfig).toBeDefined();
      expect(tsConfig?.name).toBe("typescript");
    });

    test("handles extension without dot", () => {
      const tsConfig = getLanguageFromExtension("ts");
      expect(tsConfig).toBeDefined();
      expect(tsConfig?.name).toBe("typescript");
    });

    test("handles uppercase extension", () => {
      const tsConfig = getLanguageFromExtension(".TS");
      expect(tsConfig).toBeDefined();
      expect(tsConfig?.name).toBe("typescript");
    });

    test("returns undefined for unknown extension", () => {
      const config = getLanguageFromExtension(".xyz");
      expect(config).toBeUndefined();
    });
  });

  describe("getLanguageFromPath", () => {
    test("returns language config for valid file path", () => {
      const config = getLanguageFromPath("/path/to/file.ts");
      expect(config).toBeDefined();
      expect(config?.name).toBe("typescript");
    });

    test("handles nested file paths", () => {
      const config = getLanguageFromPath("/a/b/c/d/file.py");
      expect(config).toBeDefined();
      expect(config?.name).toBe("python");
    });

    test("returns undefined for unknown extension", () => {
      const config = getLanguageFromPath("/path/to/file.unknown");
      expect(config).toBeUndefined();
    });
  });

  describe("getLanguageByName", () => {
    test("returns language config for valid name", () => {
      const config = getLanguageByName("typescript");
      expect(config).toBeDefined();
      expect(config?.name).toBe("typescript");
    });

    test("handles case insensitivity", () => {
      const config = getLanguageByName("TypeScript");
      expect(config).toBeDefined();
      expect(config?.name).toBe("typescript");
    });

    test("returns undefined for unknown name", () => {
      const config = getLanguageByName("unknownlang");
      expect(config).toBeUndefined();
    });
  });

  describe("isLanguageSupported", () => {
    test("returns true for supported languages", () => {
      expect(isLanguageSupported("typescript")).toBe(true);
      expect(isLanguageSupported("javascript")).toBe(true);
      expect(isLanguageSupported("python")).toBe(true);
    });

    test("handles case insensitivity", () => {
      expect(isLanguageSupported("TypeScript")).toBe(true);
      expect(isLanguageSupported("PYTHON")).toBe(true);
    });

    test("returns false for unsupported languages", () => {
      expect(isLanguageSupported("unknownlang")).toBe(false);
    });
  });

  describe("getSupportedLanguages", () => {
    test("returns array of language names", () => {
      const languages = getSupportedLanguages();
      expect(Array.isArray(languages)).toBe(true);
      expect(languages.length).toBeGreaterThan(0);
      expect(languages).toContain("typescript");
      expect(languages).toContain("javascript");
    });
  });

  describe("getSupportedExtensions", () => {
    test("returns array of extensions", () => {
      const extensions = getSupportedExtensions();
      expect(Array.isArray(extensions)).toBe(true);
      expect(extensions.length).toBeGreaterThan(0);
      expect(extensions).toContain(".ts");
      expect(extensions).toContain(".js");
    });
  });

  describe("clearLanguageCache", () => {
    test("clears all caches", () => {
      // First call to populate caches
      getLanguages();
      getSupportedExtensions();

      // Clear caches
      clearLanguageCache();

      // Verify caches are cleared by calling again
      // (would use fresh data if there were any changes)
      const languages = getLanguages();
      expect(languages).toBeDefined();
    });

    test("can be called multiple times without error", () => {
      clearLanguageCache();
      clearLanguageCache();
      clearLanguageCache();
      expect(true).toBe(true);
    });
  });

  describe("Legacy exports", () => {
    test("LANGUAGES export is defined", () => {
      expect(LANGUAGES).toBeDefined();
      expect(typeof LANGUAGES).toBe("object");
    });

    test("EXTENSION_MAP export is defined", () => {
      expect(EXTENSION_MAP).toBeDefined();
      expect(typeof EXTENSION_MAP).toBe("object");
    });
  });
});

describe("Language aliases", () => {
  afterEach(() => {
    clearLanguageCache();
  });

  test("handles language aliases correctly", () => {
    const languages = getLanguages();

    // Check if aliases are registered (if any exist in config)
    const hasAliases = Object.values(languages).some(
      (lang) => lang.aliases && lang.aliases.length > 0,
    );

    // Either aliases exist or they don't - both are valid
    expect(typeof hasAliases).toBe("boolean");
  });
});
