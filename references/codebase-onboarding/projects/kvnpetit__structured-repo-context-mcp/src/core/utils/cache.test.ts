import { afterEach, describe, expect, test, vi } from "vitest";

import {
  clearAllCaches,
  clearCache,
  getRegisteredCaches,
  registerCache,
  unregisterCache,
} from "@core/utils";

describe("Cache Utilities", () => {
  afterEach(() => {
    // Clean up any registered test caches
    for (const name of getRegisteredCaches()) {
      if (name.startsWith("test:")) {
        unregisterCache(name);
      }
    }
  });

  describe("registerCache", () => {
    test("registers a cache clear function", () => {
      const clearFn = vi.fn();
      registerCache("test:cache1", clearFn);

      expect(getRegisteredCaches()).toContain("test:cache1");
    });

    test("overwrites existing cache with same name", () => {
      const clearFn1 = vi.fn();
      const clearFn2 = vi.fn();

      registerCache("test:cache2", clearFn1);
      registerCache("test:cache2", clearFn2);

      clearCache("test:cache2");

      expect(clearFn1).not.toHaveBeenCalled();
      expect(clearFn2).toHaveBeenCalled();
    });
  });

  describe("unregisterCache", () => {
    test("removes a registered cache", () => {
      const clearFn = vi.fn();
      registerCache("test:cache3", clearFn);

      expect(getRegisteredCaches()).toContain("test:cache3");

      unregisterCache("test:cache3");

      expect(getRegisteredCaches()).not.toContain("test:cache3");
    });

    test("does nothing for non-existent cache", () => {
      unregisterCache("test:non-existent");
      // Should not throw
    });
  });

  describe("clearCache", () => {
    test("clears a specific cache", () => {
      const clearFn = vi.fn();
      registerCache("test:cache4", clearFn);

      const result = clearCache("test:cache4");

      expect(result).toBe(true);
      expect(clearFn).toHaveBeenCalledOnce();
    });

    test("returns false for non-existent cache", () => {
      const result = clearCache("test:non-existent");
      expect(result).toBe(false);
    });
  });

  describe("clearAllCaches", () => {
    test("clears all registered caches", () => {
      const clearFn1 = vi.fn();
      const clearFn2 = vi.fn();

      registerCache("test:cache5", clearFn1);
      registerCache("test:cache6", clearFn2);

      clearAllCaches();

      expect(clearFn1).toHaveBeenCalledOnce();
      expect(clearFn2).toHaveBeenCalledOnce();
    });
  });

  describe("getRegisteredCaches", () => {
    test("returns array of cache names", () => {
      const names = getRegisteredCaches();
      expect(Array.isArray(names)).toBe(true);
    });

    test("includes all registered caches", () => {
      registerCache("test:cache7", vi.fn());
      registerCache("test:cache8", vi.fn());

      const names = getRegisteredCaches();

      expect(names).toContain("test:cache7");
      expect(names).toContain("test:cache8");
    });
  });
});
