import { existsSync } from "fs";
import * as path from "path";
import { afterEach, describe, expect, test, vi } from "vitest";

import {
  assetExists,
  clearAssetsDirCache,
  getAssetPath,
  getAssetsDir,
  loadJsonConfig,
} from "@core/utils";

describe("Assets Utilities", () => {
  afterEach(() => {
    clearAssetsDirCache();
    vi.restoreAllMocks();
  });

  describe("getAssetsDir", () => {
    test("returns valid assets directory", () => {
      const dir = getAssetsDir();
      expect(dir).toBeDefined();
      expect(typeof dir).toBe("string");
      expect(existsSync(dir)).toBe(true);
    });

    test("returns cached value on subsequent calls", () => {
      const dir1 = getAssetsDir();
      const dir2 = getAssetsDir();
      expect(dir1).toBe(dir2);
    });

    test("clearAssetsDirCache resets the cache", () => {
      const dir1 = getAssetsDir();
      clearAssetsDirCache();
      const dir2 = getAssetsDir();
      // Both should be valid even after clearing
      expect(dir1).toBe(dir2);
    });
  });

  describe("loadJsonConfig", () => {
    test("loads valid JSON config from assets", () => {
      const config = loadJsonConfig<{ treesitter: object }>("languages.json", {
        treesitter: {},
      });
      expect(config).toBeDefined();
      expect(config.treesitter).toBeDefined();
    });

    test("returns default value for non-existent file", () => {
      const defaultValue = { foo: "bar" };
      const config = loadJsonConfig("non-existent-file.json", defaultValue);
      expect(config).toEqual(defaultValue);
    });
  });

  describe("getAssetPath", () => {
    test("returns path within assets directory", () => {
      const path = getAssetPath("languages.json");
      expect(path).toContain("assets");
      expect(path).toContain("languages.json");
    });

    test("handles multiple segments", () => {
      const path = getAssetPath("queries", "javascript", "tags.scm");
      expect(path).toContain("queries");
      expect(path).toContain("javascript");
      expect(path).toContain("tags.scm");
    });
  });

  describe("assetExists", () => {
    test("returns true for existing asset", () => {
      expect(assetExists("languages.json")).toBe(true);
    });

    test("returns false for non-existent asset", () => {
      expect(assetExists("non-existent-file.xyz")).toBe(false);
    });

    test("handles nested paths", () => {
      expect(assetExists("queries", "javascript", "tags.scm")).toBe(true);
      expect(assetExists("queries", "nonexistent", "file.scm")).toBe(false);
    });
  });
});

describe("getAssetsDir fallback behavior", () => {
  afterEach(() => {
    clearAssetsDirCache();
    vi.restoreAllMocks();
  });

  test("returns fallback path when no assets directory exists", async () => {
    // Mock fs module with existsSync always returning false
    vi.doMock("fs", () => ({
      existsSync: () => false,
      readFileSync: () => "{}",
    }));

    // Clear and re-import to get fresh module
    vi.resetModules();
    const { getAssetsDir: freshGetAssetsDir, clearAssetsDirCache: freshClear } =
      await import("@core/utils/assets");

    const dir = freshGetAssetsDir();
    // When no paths exist, it falls back to process.cwd() + "assets"
    expect(dir).toBe(path.join(process.cwd(), "assets"));

    freshClear();
    vi.doUnmock("fs");
    vi.resetModules();
  });
});

describe("getAssetsDir ESM/CJS handling", () => {
  afterEach(() => {
    clearAssetsDirCache();
    vi.restoreAllMocks();
  });

  test("handles ESM context when __dirname is undefined", () => {
    // This test verifies the ESM branch where __dirname is not defined
    // The module uses import.meta.url as fallback
    // In the test environment, this branch may or may not be hit depending on
    // how the module is loaded, but we can verify it doesn't throw
    clearAssetsDirCache();
    const dir = getAssetsDir();
    expect(dir).toBeDefined();
    expect(typeof dir).toBe("string");
  });

  test("handles multiple possible paths correctly", async () => {
    // Test that the function tries multiple paths
    let callCount = 0;
    vi.doMock("fs", () => ({
      existsSync: (p: string) => {
        callCount++;
        // Return true only for the third path (process.cwd() + "assets")
        return p.includes(process.cwd());
      },
      readFileSync: () => "{}",
    }));

    vi.resetModules();
    const { getAssetsDir: freshGetAssetsDir, clearAssetsDirCache: freshClear } =
      await import("@core/utils/assets");

    const dir = freshGetAssetsDir();
    expect(dir).toBeDefined();
    // Should have checked at least one path
    expect(callCount).toBeGreaterThan(0);

    freshClear();
    vi.doUnmock("fs");
    vi.resetModules();
  });
});

describe("loadJsonConfig edge cases", () => {
  afterEach(() => {
    clearAssetsDirCache();
    vi.restoreAllMocks();
  });

  test("returns default value when JSON is invalid", async () => {
    vi.doMock("fs", () => ({
      existsSync: () => true,
      readFileSync: () => "{ invalid json }",
    }));

    vi.resetModules();
    const {
      loadJsonConfig: freshLoadJsonConfig,
      clearAssetsDirCache: freshClear,
    } = await import("@core/utils/assets");

    const defaultValue = { fallback: true };
    const config = freshLoadJsonConfig("test.json", defaultValue);
    expect(config).toEqual(defaultValue);

    freshClear();
    vi.doUnmock("fs");
    vi.resetModules();
  });
});
