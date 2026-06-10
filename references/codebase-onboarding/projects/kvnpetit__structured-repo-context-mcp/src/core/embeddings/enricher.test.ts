import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import type { CodeChunk } from "@core/embeddings/types";

// Use vi.hoisted to define mocks before they're used in the hoisted vi.mock calls
const {
  mockExtractSymbols,
  mockExtractImports,
  mockExtractExports,
  mockParseCode,
} = vi.hoisted(() => ({
  mockExtractSymbols: vi.fn(),
  mockExtractImports: vi.fn(),
  mockExtractExports: vi.fn(),
  mockParseCode: vi.fn(),
}));

// Mock modules BEFORE importing the enricher
vi.mock("@core/parser", () => ({
  parseCode: mockParseCode,
}));

vi.mock("@core/symbols", () => ({
  extractSymbols: mockExtractSymbols,
  extractImports: mockExtractImports,
  extractExports: mockExtractExports,
}));

// Now import the enricher (uses mocked modules)
import {
  clearASTCache,
  enrichChunk,
  enrichChunks,
  enrichChunksFromFile,
  getASTCacheStats,
} from "@core/embeddings/enricher";

// Default mock data
const defaultSymbolsResult = {
  symbols: [
    {
      name: "execute",
      type: "function",
      start: { line: 5, column: 0, offset: 50 },
      end: { line: 15, column: 1, offset: 200 },
      signature: "async function execute(input: SearchCodeInput)",
    },
    {
      name: "searchCodeFeature",
      type: "constant",
      start: { line: 20, column: 0, offset: 250 },
      end: { line: 25, column: 1, offset: 350 },
    },
  ],
  summary: {
    functions: 1,
    constants: 1,
    classes: 0,
    variables: 0,
    interfaces: 0,
    types: 0,
    enums: 0,
    methods: 0,
    properties: 0,
    total: 2,
  },
};

const defaultImports = [
  {
    source: "zod",
    names: [{ name: "z" }],
    start: { line: 1, column: 0, offset: 0 },
    end: { line: 1, column: 20, offset: 20 },
  },
  {
    source: "@features/types",
    names: [{ name: "Feature" }, { name: "FeatureResult" }],
    start: { line: 2, column: 0, offset: 21 },
    end: { line: 2, column: 45, offset: 65 },
  },
];

const defaultExports = [
  {
    name: "searchCodeSchema",
    isDefault: false,
    start: { line: 10, column: 0, offset: 100 },
    end: { line: 10, column: 30, offset: 130 },
  },
  {
    name: "execute",
    isDefault: false,
    start: { line: 15, column: 0, offset: 150 },
    end: { line: 15, column: 25, offset: 175 },
  },
  {
    name: "searchCodeFeature",
    isDefault: false,
    start: { line: 25, column: 0, offset: 300 },
    end: { line: 25, column: 35, offset: 335 },
  },
];

function setupDefaultMocks(): void {
  mockParseCode.mockResolvedValue({
    tree: { rootNode: { type: "program" } },
    language: "typescript",
    parser: {},
    languageInstance: {},
  });

  mockExtractSymbols.mockReturnValue(defaultSymbolsResult);
  mockExtractImports.mockReturnValue(defaultImports);
  mockExtractExports.mockReturnValue(defaultExports);
}

beforeEach(() => {
  clearASTCache();
  vi.clearAllMocks();
  setupDefaultMocks();
});

afterEach(() => {
  clearASTCache();
});

describe("enrichChunk", () => {
  const sampleChunk: CodeChunk = {
    id: "chunk_123",
    content:
      "export async function execute(input) { return { success: true }; }",
    filePath: "/src/features/search-code/index.ts",
    language: "typescript",
    startLine: 5,
    endLine: 15,
  };

  const sampleContent = `
import { z } from "zod";
import type { Feature, FeatureResult } from "@features/types";

export async function execute(input) {
  return { success: true };
}

export const searchCodeFeature = {
  name: "search_code",
};
`.trim();

  test("enriches chunk with all metadata", async () => {
    const result = await enrichChunk(sampleChunk, sampleContent);

    expect(result.wasEnriched).toBe(true);
    expect(result.enrichedContent).toContain("File:");
    expect(result.enrichedContent).toContain("Language: typescript");
    expect(result.enrichedContent).toContain("Symbols:");
    expect(result.enrichedContent).toContain("Imports:");
    expect(result.enrichedContent).toContain("Exports:");
    expect(result.enrichedContent).toContain("---");
    expect(result.enrichedContent).toContain(sampleChunk.content);
  });

  test("includes file path in enriched content", async () => {
    const result = await enrichChunk(sampleChunk, sampleContent);

    expect(result.enrichedContent).toContain(
      "File: /src/features/search-code/index.ts",
    );
  });

  test("includes language in enriched content", async () => {
    const result = await enrichChunk(sampleChunk, sampleContent);

    expect(result.enrichedContent).toContain("Language: typescript");
  });

  test("extracts symbols in chunk range", async () => {
    const result = await enrichChunk(sampleChunk, sampleContent);

    // The execute function should be in the range (lines 5-15)
    expect(result.containedSymbols).toContainEqual(
      expect.objectContaining({ name: "execute", type: "function" }),
    );
  });

  test("includes imports in enriched content", async () => {
    const result = await enrichChunk(sampleChunk, sampleContent);

    expect(result.enrichedContent).toContain("Imports:");
    expect(result.enrichedContent).toContain("zod");
  });

  test("includes exports in enriched content", async () => {
    const result = await enrichChunk(sampleChunk, sampleContent);

    expect(result.enrichedContent).toContain("Exports:");
    expect(result.enrichedContent).toContain("searchCodeSchema");
  });
});

describe("enrichChunksFromFile", () => {
  const chunks: CodeChunk[] = [
    {
      id: "chunk_1",
      content: "import { z } from 'zod';",
      filePath: "/src/test.ts",
      language: "typescript",
      startLine: 1,
      endLine: 3,
    },
    {
      id: "chunk_2",
      content: "export async function execute() {}",
      filePath: "/src/test.ts",
      language: "typescript",
      startLine: 5,
      endLine: 15,
    },
    {
      id: "chunk_3",
      content: "export const feature = {};",
      filePath: "/src/test.ts",
      language: "typescript",
      startLine: 20,
      endLine: 25,
    },
  ];

  const content = chunks.map((c) => c.content).join("\n\n");

  test("enriches all chunks from same file efficiently", async () => {
    const results = await enrichChunksFromFile(chunks, content);

    expect(results).toHaveLength(3);
    results.forEach((result) => {
      expect(result.wasEnriched).toBe(true);
      expect(result.enrichedContent).toContain("File:");
    });

    // Parser should only be called once (for efficiency)
    expect(mockParseCode).toHaveBeenCalledTimes(1);
  });

  test("handles empty chunks array", async () => {
    const results = await enrichChunksFromFile([], content);

    expect(results).toEqual([]);
  });

  test("returns basic enrichment when first chunk has no filePath", async () => {
    const badChunks: CodeChunk[] = [
      {
        id: "chunk_1",
        content: "test",
        filePath: "",
        language: "typescript",
        startLine: 1,
        endLine: 1,
      },
    ];

    const results = await enrichChunksFromFile(badChunks, content);

    expect(results[0]?.wasEnriched).toBe(false);
    // Should still have basic header
    expect(results[0]?.enrichedContent).toContain("File:");
    expect(results[0]?.enrichedContent).toContain("Language:");
  });
});

describe("enrichChunks", () => {
  const chunksFromMultipleFiles: CodeChunk[] = [
    {
      id: "chunk_a1",
      content: "const a = 1;",
      filePath: "/src/file-a.ts",
      language: "typescript",
      startLine: 1,
      endLine: 1,
    },
    {
      id: "chunk_b1",
      content: "const b = 2;",
      filePath: "/src/file-b.ts",
      language: "typescript",
      startLine: 1,
      endLine: 1,
    },
    {
      id: "chunk_a2",
      content: "function a() {}",
      filePath: "/src/file-a.ts",
      language: "typescript",
      startLine: 5,
      endLine: 10,
    },
  ];

  const fileContents = new Map([
    ["/src/file-a.ts", "const a = 1;\n\nfunction a() {}"],
    ["/src/file-b.ts", "const b = 2;"],
  ]);

  test("enriches chunks from multiple files", async () => {
    const results = await enrichChunks(chunksFromMultipleFiles, fileContents);

    expect(results).toHaveLength(3);
    results.forEach((result) => {
      expect(result.wasEnriched).toBe(true);
    });
  });

  test("preserves original order of chunks", async () => {
    const results = await enrichChunks(chunksFromMultipleFiles, fileContents);

    expect(results[0]?.id).toBe("chunk_a1");
    expect(results[1]?.id).toBe("chunk_b1");
    expect(results[2]?.id).toBe("chunk_a2");
  });

  test("handles missing file content with basic enrichment", async () => {
    const partialContents = new Map([
      ["/src/file-a.ts", "const a = 1;"],
      // file-b.ts is missing
    ]);

    const results = await enrichChunks(
      chunksFromMultipleFiles,
      partialContents,
    );

    expect(results).toHaveLength(3);
    // file-a chunks should be enriched
    expect(results[0]?.wasEnriched).toBe(true);
    // file-b chunk should have basic enrichment (missing content)
    expect(results[1]?.wasEnriched).toBe(false);
    expect(results[1]?.enrichedContent).toContain("File:");
  });
});

describe("clearASTCache", () => {
  test("clears the AST cache", async () => {
    const chunk: CodeChunk = {
      id: "chunk_1",
      content: "test",
      filePath: "/src/test.ts",
      language: "typescript",
      startLine: 1,
      endLine: 1,
    };

    // First call should populate cache
    await enrichChunk(chunk, "test content");

    const statsBefore = getASTCacheStats();
    expect(statsBefore.files).toBeGreaterThan(0);

    clearASTCache();

    const statsAfter = getASTCacheStats();
    expect(statsAfter.files).toBe(0);
    expect(statsAfter.entries).toEqual([]);
  });
});

describe("getASTCacheStats", () => {
  test("returns cache statistics", async () => {
    const stats = getASTCacheStats();
    expect(stats.files).toBe(0);
    expect(stats.entries).toEqual([]);

    // Populate cache
    const chunk: CodeChunk = {
      id: "chunk_1",
      content: "test",
      filePath: "/src/cached.ts",
      language: "typescript",
      startLine: 1,
      endLine: 1,
    };

    await enrichChunk(chunk, "test content");

    const statsAfter = getASTCacheStats();
    expect(statsAfter.files).toBe(1);
    expect(statsAfter.entries).toContain("/src/cached.ts");
  });
});

describe("enrichChunk edge cases", () => {
  const sampleChunk: CodeChunk = {
    id: "chunk_123",
    content: "const x = 1;",
    filePath: "/src/test.ts",
    language: "typescript",
    startLine: 1,
    endLine: 1,
  };

  test("handles chunk with no symbols in range", async () => {
    // Chunk at lines 1-1, but mock symbols are at lines 5-25
    const result = await enrichChunk(sampleChunk, "const x = 1;");

    expect(result.wasEnriched).toBe(true);
    // Symbols are outside this chunk's range
    expect(result.containedSymbols).toEqual([]);
  });

  test("handles chunk that spans multiple symbols", async () => {
    const wideChunk: CodeChunk = {
      id: "chunk_wide",
      content: "// lots of code",
      filePath: "/src/test.ts",
      language: "typescript",
      startLine: 1,
      endLine: 30,
    };

    const result = await enrichChunk(wideChunk, "// lots of code");

    expect(result.wasEnriched).toBe(true);
    // Should include both symbols since chunk spans lines 1-30
    expect(result.containedSymbols.length).toBe(2);
  });

  test("handles empty imports array", async () => {
    mockExtractImports.mockReturnValue([]);

    const result = await enrichChunk(sampleChunk, "const x = 1;");

    expect(result.wasEnriched).toBe(true);
    expect(result.enrichedContent).not.toContain("Imports:");
  });

  test("handles empty exports array", async () => {
    mockExtractExports.mockReturnValue([]);

    const result = await enrichChunk(sampleChunk, "const x = 1;");

    expect(result.wasEnriched).toBe(true);
    expect(result.enrichedContent).not.toContain("Exports:");
  });

  test("handles import with empty source", async () => {
    mockExtractImports.mockReturnValue([
      {
        source: "",
        names: [],
        start: { line: 1, column: 0, offset: 0 },
        end: { line: 1, column: 10, offset: 10 },
      },
    ]);

    const result = await enrichChunk(sampleChunk, "const x = 1;");

    expect(result.wasEnriched).toBe(true);
    // Empty import sources should be filtered out
    expect(result.enrichedContent).not.toContain("Imports:");
  });

  test("handles export with 'default' name", async () => {
    mockExtractExports.mockReturnValue([
      {
        name: "default",
        isDefault: true,
        start: { line: 1, column: 0, offset: 0 },
        end: { line: 1, column: 20, offset: 20 },
      },
    ]);

    const result = await enrichChunk(sampleChunk, "const x = 1;");

    expect(result.wasEnriched).toBe(true);
    // 'default' exports should be filtered out
    expect(result.enrichedContent).not.toContain("Exports:");
  });
});

describe("enrichChunk parser failure handling", () => {
  test("returns basic enrichment when parser fails", async () => {
    mockParseCode.mockRejectedValue(new Error("Parser error"));

    const chunk: CodeChunk = {
      id: "chunk_fail",
      content: "invalid syntax???",
      filePath: "/src/broken.xyz",
      language: "unknown",
      startLine: 1,
      endLine: 1,
    };

    const result = await enrichChunk(chunk, "invalid syntax???");

    expect(result.wasEnriched).toBe(false);
    // Should still have basic header with file path and language
    expect(result.enrichedContent).toContain("File: /src/broken.xyz");
    expect(result.enrichedContent).toContain("Language: unknown");
    expect(result.enrichedContent).toContain("---");
    expect(result.enrichedContent).toContain(chunk.content);
    expect(result.containedSymbols).toEqual([]);
  });
});

describe("enrichChunks edge cases", () => {
  test("handles chunk with id not found in enriched results", async () => {
    const chunks: CodeChunk[] = [
      {
        id: "orphan_chunk",
        content: "orphan",
        filePath: "/src/file.ts",
        language: "typescript",
        startLine: 1,
        endLine: 1,
      },
    ];

    const results = await enrichChunks(
      chunks,
      new Map([["/src/file.ts", "orphan"]]),
    );

    expect(results).toHaveLength(1);
    expect(results[0]?.id).toBe("orphan_chunk");
  });

  test("handles empty file contents map with basic enrichment", async () => {
    const chunks: CodeChunk[] = [
      {
        id: "chunk_no_content",
        content: "no content available",
        filePath: "/src/missing.ts",
        language: "typescript",
        startLine: 1,
        endLine: 1,
      },
    ];

    const results = await enrichChunks(chunks, new Map());

    expect(results).toHaveLength(1);
    expect(results[0]?.wasEnriched).toBe(false);
    // Should still have basic header
    expect(results[0]?.enrichedContent).toContain("File:");
  });
});

describe("symbol range detection", () => {
  test("detects symbol that starts before chunk but ends inside", async () => {
    const chunk: CodeChunk = {
      id: "chunk_overlap_start",
      content: "middle of function",
      filePath: "/src/test.ts",
      language: "typescript",
      startLine: 10,
      endLine: 12,
    };

    // Symbol execute is at lines 5-15, so it overlaps with chunk at 10-12
    const result = await enrichChunk(chunk, "code");

    expect(result.containedSymbols).toContainEqual(
      expect.objectContaining({ name: "execute" }),
    );
  });

  test("detects symbol that starts inside chunk but ends after", async () => {
    const chunk: CodeChunk = {
      id: "chunk_overlap_end",
      content: "start of function",
      filePath: "/src/test.ts",
      language: "typescript",
      startLine: 3,
      endLine: 8,
    };

    // Symbol execute is at lines 5-15, so it overlaps with chunk at 3-8
    const result = await enrichChunk(chunk, "code");

    expect(result.containedSymbols).toContainEqual(
      expect.objectContaining({ name: "execute" }),
    );
  });

  test("detects symbol fully contained in chunk", async () => {
    const chunk: CodeChunk = {
      id: "chunk_full_contain",
      content: "whole symbol inside",
      filePath: "/src/test.ts",
      language: "typescript",
      startLine: 3,
      endLine: 18,
    };

    // Symbol execute is at lines 5-15, fully inside chunk at 3-18
    const result = await enrichChunk(chunk, "code");

    expect(result.containedSymbols).toContainEqual(
      expect.objectContaining({ name: "execute" }),
    );
  });

  test("does not detect symbol completely outside chunk", async () => {
    const chunk: CodeChunk = {
      id: "chunk_no_overlap",
      content: "no symbols here",
      filePath: "/src/test.ts",
      language: "typescript",
      startLine: 30,
      endLine: 35,
    };

    // Symbols are at lines 5-15 and 20-25, both outside chunk at 30-35
    const result = await enrichChunk(chunk, "code");

    expect(result.containedSymbols).toEqual([]);
  });
});

describe("AST cache behavior", () => {
  test("uses cached analysis for subsequent chunks from same file", async () => {
    const chunk1: CodeChunk = {
      id: "chunk_1",
      content: "const a = 1;",
      filePath: "/src/same-file.ts",
      language: "typescript",
      startLine: 1,
      endLine: 1,
    };

    const chunk2: CodeChunk = {
      id: "chunk_2",
      content: "const b = 2;",
      filePath: "/src/same-file.ts",
      language: "typescript",
      startLine: 5,
      endLine: 5,
    };

    await enrichChunk(chunk1, "const a = 1;");
    await enrichChunk(chunk2, "const b = 2;");

    // Parser should only be called once due to caching
    expect(mockParseCode).toHaveBeenCalledTimes(1);
  });

  test("parses different files separately", async () => {
    const chunk1: CodeChunk = {
      id: "chunk_1",
      content: "const a = 1;",
      filePath: "/src/file-a.ts",
      language: "typescript",
      startLine: 1,
      endLine: 1,
    };

    const chunk2: CodeChunk = {
      id: "chunk_2",
      content: "const b = 2;",
      filePath: "/src/file-b.ts",
      language: "typescript",
      startLine: 1,
      endLine: 1,
    };

    await enrichChunk(chunk1, "const a = 1;");
    await enrichChunk(chunk2, "const b = 2;");

    // Parser should be called twice (once per file)
    expect(mockParseCode).toHaveBeenCalledTimes(2);
  });
});
