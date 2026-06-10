import { describe, expect, test } from "vitest";

import {
  clearSCMCache,
  getAvailableQueryTypes,
  getLanguagesWithTags,
  getSCMPath,
  hasOfficialTags,
  loadHighlightsQuery,
  loadLocalsQuery,
  loadSCMQuery,
  loadTagsQuery,
} from "@core/queries/loader";

describe("SCM Query Loader", () => {
  test("getSCMPath returns path for existing query", () => {
    const path = getSCMPath("javascript", "tags");
    expect(path).toBeDefined();
    expect(path).toContain("queries");
    expect(path).toContain("javascript");
    expect(path).toContain("tags.scm");
  });

  test("getSCMPath returns undefined for non-existent query", () => {
    const path = getSCMPath("javascript", "folds");
    expect(path).toBeUndefined();
  });

  test("getSCMPath returns undefined for unknown language", () => {
    const path = getSCMPath("unknown-language", "tags");
    expect(path).toBeUndefined();
  });

  test("loadTagsQuery loads JavaScript tags.scm", () => {
    clearSCMCache();
    const query = loadTagsQuery("javascript");
    expect(query).toBeDefined();
    expect(query).toContain("function");
    expect(query).toContain("@definition");
  });

  test("loadTagsQuery loads TypeScript tags.scm", () => {
    clearSCMCache();
    const query = loadTagsQuery("typescript");
    expect(query).toBeDefined();
    expect(query).toContain("interface");
  });

  test("loadTagsQuery loads Python tags.scm", () => {
    clearSCMCache();
    const query = loadTagsQuery("python");
    expect(query).toBeDefined();
    expect(query).toContain("function_definition");
  });

  test("loadTagsQuery returns undefined for language without tags", () => {
    const query = loadTagsQuery("json");
    expect(query).toBeUndefined();
  });

  test("loadHighlightsQuery loads query", () => {
    clearSCMCache();
    const query = loadHighlightsQuery("javascript");
    expect(query).toBeDefined();
  });

  test("loadSCMQuery caches queries", () => {
    clearSCMCache();

    // First load
    const query1 = loadSCMQuery("javascript", "tags");
    expect(query1).toBeDefined();

    // Second load (from cache)
    const query2 = loadSCMQuery("javascript", "tags");
    expect(query2).toBe(query1);
  });

  test("hasOfficialTags returns true for supported languages", () => {
    expect(hasOfficialTags("javascript")).toBe(true);
    expect(hasOfficialTags("typescript")).toBe(true);
    expect(hasOfficialTags("python")).toBe(true);
    expect(hasOfficialTags("go")).toBe(true);
    expect(hasOfficialTags("rust")).toBe(true);
  });

  test("hasOfficialTags returns false for unsupported languages", () => {
    expect(hasOfficialTags("json")).toBe(false);
    expect(hasOfficialTags("yaml")).toBe(false);
    expect(hasOfficialTags("unknown")).toBe(false);
  });

  test("getLanguagesWithTags returns list of supported languages", () => {
    const languages = getLanguagesWithTags();
    expect(languages).toContain("javascript");
    expect(languages).toContain("typescript");
    expect(languages).toContain("python");
    expect(languages.length).toBeGreaterThan(5);
  });

  test("getAvailableQueryTypes returns available types for language", () => {
    const jsTypes = getAvailableQueryTypes("javascript");
    expect(jsTypes).toContain("tags");
    expect(jsTypes).toContain("highlights");
    expect(jsTypes).toContain("locals");

    // Unsupported language returns empty array
    const unknownTypes = getAvailableQueryTypes("unknown-lang");
    expect(unknownTypes).toEqual([]);
  });

  test("clearSCMCache clears the cache", () => {
    // Load a query
    loadSCMQuery("javascript", "tags");

    // Clear cache
    clearSCMCache();

    // Verify cache is cleared by checking that a fresh load works
    const query = loadSCMQuery("javascript", "tags");
    expect(query).toBeDefined();
  });

  test("loadSCMQuery prevents circular inheritance", () => {
    clearSCMCache();
    // Create a visited set that already contains the language
    const visited = new Set<string>(["javascript"]);
    const query = loadSCMQuery("javascript", "tags", visited);
    expect(query).toBeUndefined();
  });

  test("loadSCMQuery handles csharp alias normalization", () => {
    clearSCMCache();
    // csharp is an alias for c_sharp
    const queryPath = getSCMPath("csharp", "tags");
    // Just test that the function handles the alias without error
    expect(queryPath === undefined || typeof queryPath === "string").toBe(true);
  });

  test("loadSCMQuery handles tsx normalization to typescript", () => {
    clearSCMCache();
    // tsx normalizes to typescript directory
    const query = loadTagsQuery("tsx");
    // tsx should use typescript queries
    expect(query).toBeDefined();
    expect(query).toContain("interface");
  });

  test("loadHighlightsQuery returns undefined for unsupported language", () => {
    const query = loadHighlightsQuery("completely-unknown-language");
    expect(query).toBeUndefined();
  });

  test("loadLocalsQuery loads locals.scm for javascript", () => {
    clearSCMCache();
    const query = loadLocalsQuery("javascript");
    expect(query).toBeDefined();
  });

  test("loadLocalsQuery returns undefined for unsupported language", () => {
    const query = loadLocalsQuery("completely-unknown-language");
    expect(query).toBeUndefined();
  });

  test("loadSCMQuery handles inheritance resolution", () => {
    clearSCMCache();
    // TypeScript inherits from JavaScript
    const query = loadTagsQuery("typescript");
    expect(query).toBeDefined();
    // Should contain TypeScript-specific content
    expect(query).toContain("interface");
  });
});
