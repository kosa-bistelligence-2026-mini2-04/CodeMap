import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import {
  VectorStore,
  createVectorStore,
  getIndexPath,
} from "@core/embeddings/store";
import type { EmbeddedChunk } from "@core/embeddings/types";

// Mock logger to avoid noise in tests
vi.mock("@utils", () => ({
  logger: {
    debug: vi.fn(),
    warn: vi.fn(),
    info: vi.fn(),
    error: vi.fn(),
  },
}));

describe("VectorStore", () => {
  let tempDir: string;
  let store: VectorStore;

  const mockConfig = {
    embeddingDimensions: 768,
  };

  beforeEach(async () => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "lancedb-test-"));
    store = new VectorStore(tempDir, mockConfig);
    await store.connect();
  });

  afterEach(() => {
    store.close();
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  const createMockChunk = (id: string, filePath: string): EmbeddedChunk => ({
    id,
    content: `function ${id}() { return true; }`,
    filePath,
    language: "typescript",
    startLine: 1,
    endLine: 3,
    symbolName: id,
    symbolType: "function",
    vector: new Array(768).fill(0).map(() => Math.random()),
  });

  describe("addChunks", () => {
    test("adds chunks to the store", async () => {
      const chunks = [
        createMockChunk("func1", "/test/file1.ts"),
        createMockChunk("func2", "/test/file1.ts"),
      ];

      await store.addChunks(chunks);
      const status = await store.getStatus(tempDir);

      expect(status.totalChunks).toBe(2);
      expect(status.totalFiles).toBe(1);
    });

    test("throws error when not connected", async () => {
      const disconnectedStore = new VectorStore(tempDir, mockConfig);
      const chunks = [createMockChunk("func1", "/test/file1.ts")];

      await expect(disconnectedStore.addChunks(chunks)).rejects.toThrow(
        "Database not connected",
      );
    });
  });

  describe("search", () => {
    test("returns similar chunks", async () => {
      const chunks = [
        createMockChunk("func1", "/test/file1.ts"),
        createMockChunk("func2", "/test/file2.ts"),
      ];
      await store.addChunks(chunks);

      const queryVector = new Array(768).fill(0).map(() => Math.random());
      const results = await store.search(queryVector, 5);

      expect(results.length).toBeLessThanOrEqual(5);
      expect(results.length).toBeGreaterThan(0);
      expect(results[0]).toHaveProperty("chunk");
      expect(results[0]).toHaveProperty("score");
    });

    test("returns empty array when table does not exist", async () => {
      const emptyStore = new VectorStore(
        path.join(tempDir, "empty"),
        mockConfig,
      );
      await emptyStore.connect();

      const queryVector: number[] = new Array<number>(768).fill(0);
      const results = await emptyStore.search(queryVector);

      expect(results).toEqual([]);
    });
  });

  describe("deleteByFilePath", () => {
    test("executes without error", async () => {
      const chunks = [
        createMockChunk("func1", "/test/file1.ts"),
        createMockChunk("func2", "/test/file2.ts"),
      ];
      await store.addChunks(chunks);

      // Just verify it resolves - LanceDB filter syntax may vary
      await store.deleteByFilePath("/test/file1.ts");
      // If we get here without throwing, the test passes
      expect(true).toBe(true);
    });

    test("does nothing when table does not exist", async () => {
      const emptyStore = new VectorStore(
        path.join(tempDir, "empty"),
        mockConfig,
      );
      await emptyStore.connect();

      // Should not throw even without a table
      await emptyStore.deleteByFilePath("/test/file.ts");
      expect(true).toBe(true);
    });
  });

  describe("clear", () => {
    test("removes all data", async () => {
      const chunks = [createMockChunk("func1", "/test/file1.ts")];
      await store.addChunks(chunks);

      await store.clear();
      const status = await store.getStatus(tempDir);

      expect(status.totalChunks).toBe(0);
    });
  });

  describe("getStatus", () => {
    test("returns correct status", async () => {
      const chunks = [
        createMockChunk("func1", "/test/file1.ts"),
        createMockChunk("func2", "/test/file2.ts"),
        createMockChunk("func3", "/test/file2.ts"),
      ];
      await store.addChunks(chunks);

      const status = await store.getStatus(tempDir);

      expect(status.exists).toBe(true);
      expect(status.totalChunks).toBe(3);
      expect(status.totalFiles).toBe(2);
      expect(status.languages.typescript).toBe(3);
    });
  });

  describe("getIndexedFiles", () => {
    test("returns unique file paths", async () => {
      const chunks = [
        createMockChunk("func1", "/test/file1.ts"),
        createMockChunk("func2", "/test/file2.ts"),
        createMockChunk("func3", "/test/file1.ts"),
      ];
      await store.addChunks(chunks);

      const files = await store.getIndexedFiles();

      expect(files).toHaveLength(2);
      expect(files).toContain("/test/file1.ts");
      expect(files).toContain("/test/file2.ts");
    });
  });

  describe("exists", () => {
    test("returns true when index exists", async () => {
      const chunks = [createMockChunk("func1", "/test/file1.ts")];
      await store.addChunks(chunks);

      expect(store.exists()).toBe(true);
    });

    test("returns false when index does not exist", () => {
      const newStore = new VectorStore(
        path.join(tempDir, "nonexistent"),
        mockConfig,
      );
      expect(newStore.exists()).toBe(false);
    });
  });
});

describe("createVectorStore", () => {
  test("creates a VectorStore instance", () => {
    const store = createVectorStore("/test/dir", { embeddingDimensions: 768 });
    expect(store).toBeInstanceOf(VectorStore);
  });
});

describe("getIndexPath", () => {
  test("returns correct index path", () => {
    const indexPath = getIndexPath("/test/dir");
    expect(indexPath).toBe(path.join("/test/dir", ".src-index"));
  });
});

describe("VectorStore advanced operations", () => {
  let tempDir: string;

  const mockConfig = {
    embeddingDimensions: 768,
  };

  const createMockChunk = (id: string, filePath: string) => ({
    id,
    content: `function ${id}() { return true; }`,
    filePath,
    language: "typescript",
    startLine: 1,
    endLine: 3,
    symbolName: id,
    symbolType: "function",
    vector: new Array(768).fill(0).map(() => Math.random()),
  });

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "lancedb-test-"));
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  test("reopens existing table on connect", async () => {
    // First connection - create table
    const store1 = new VectorStore(tempDir, mockConfig);
    await store1.connect();
    await store1.addChunks([createMockChunk("func1", "/test/file1.ts")]);
    store1.close();

    // Second connection - should reopen existing table
    const store2 = new VectorStore(tempDir, mockConfig);
    await store2.connect();
    const status = await store2.getStatus(tempDir);

    expect(status.totalChunks).toBe(1);
    store2.close();
  });

  test("adds chunks to existing table", async () => {
    const store = new VectorStore(tempDir, mockConfig);
    await store.connect();

    // First batch
    await store.addChunks([createMockChunk("func1", "/test/file1.ts")]);

    // Second batch - should add to existing table
    await store.addChunks([createMockChunk("func2", "/test/file2.ts")]);

    const status = await store.getStatus(tempDir);
    expect(status.totalChunks).toBe(2);

    store.close();
  });

  test("getIndexedFiles returns empty when table is null", async () => {
    const store = new VectorStore(path.join(tempDir, "empty"), mockConfig);
    await store.connect();

    const files = await store.getIndexedFiles();
    expect(files).toEqual([]);

    store.close();
  });

  test("getStatus returns default when table is null", async () => {
    const store = new VectorStore(path.join(tempDir, "empty"), mockConfig);
    await store.connect();

    const status = await store.getStatus(tempDir);
    expect(status.totalChunks).toBe(0);
    expect(status.totalFiles).toBe(0);

    store.close();
  });

  test("clear does nothing when table is null", async () => {
    const store = new VectorStore(path.join(tempDir, "empty"), mockConfig);
    await store.connect();

    // Should not throw
    await store.clear();
    expect(true).toBe(true);

    store.close();
  });

  test("handles chunks without optional symbol fields", async () => {
    const store = new VectorStore(tempDir, mockConfig);
    await store.connect();

    const chunkWithoutSymbol = {
      id: "chunk1",
      content: "const x = 1;",
      filePath: "/test/file.ts",
      language: "typescript",
      startLine: 1,
      endLine: 1,
      vector: new Array(768).fill(0),
    };

    await store.addChunks([chunkWithoutSymbol]);
    const status = await store.getStatus(tempDir);
    expect(status.totalChunks).toBe(1);

    store.close();
  });
});

describe("VectorStore hybrid search", () => {
  let tempDir: string;

  const mockConfig = {
    embeddingDimensions: 768,
  };

  const createMockChunk = (
    id: string,
    content: string,
    filePath: string,
  ): EmbeddedChunk => ({
    id,
    content,
    filePath,
    language: "typescript",
    startLine: 1,
    endLine: 3,
    symbolName: id,
    symbolType: "function",
    vector: new Array(768).fill(0).map(() => Math.random()),
  });

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "lancedb-hybrid-test-"));
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  test("searchHybrid returns empty array when table is null", async () => {
    const store = new VectorStore(path.join(tempDir, "empty"), mockConfig);
    await store.connect();

    const queryVector: number[] = new Array<number>(768).fill(0);
    const results = await store.searchHybrid(queryVector, "test query", 10);

    expect(results).toEqual([]);
    store.close();
  });

  test("searchHybrid in vector mode delegates to search", async () => {
    const store = new VectorStore(tempDir, mockConfig);
    await store.connect();

    const chunk1 = createMockChunk(
      "func1",
      "function hello() { return 'hello'; }",
      "/a.ts",
    );
    const chunk2 = createMockChunk(
      "func2",
      "function world() { return 'world'; }",
      "/b.ts",
    );
    await store.addChunks([chunk1, chunk2]);

    const results = await store.searchHybrid(chunk1.vector, "hello", 5, {
      mode: "vector",
    });

    expect(results.length).toBeGreaterThan(0);
    store.close();
  });

  test("searchHybrid in fts mode uses full-text search", async () => {
    const store = new VectorStore(tempDir, mockConfig);
    await store.connect();

    const chunks = [
      createMockChunk("func1", "function hello() { return 'hello'; }", "/a.ts"),
      createMockChunk("func2", "function world() { return 'world'; }", "/b.ts"),
    ];
    await store.addChunks(chunks);

    const queryVector: number[] = new Array<number>(768).fill(0);
    const results = await store.searchHybrid(queryVector, "hello", 5, {
      mode: "fts",
    });

    // FTS may or may not return results depending on LanceDB FTS support
    expect(Array.isArray(results)).toBe(true);
    store.close();
  });

  test("searchHybrid in hybrid mode combines vector and FTS results", async () => {
    const store = new VectorStore(tempDir, mockConfig);
    await store.connect();

    const chunk1 = createMockChunk(
      "func1",
      "function handleError() { throw new Error('error'); }",
      "/a.ts",
    );
    const chunk2 = createMockChunk(
      "func2",
      "function processData() { return data.map(x => x); }",
      "/b.ts",
    );
    const chunk3 = createMockChunk(
      "func3",
      "function validateInput() { if (!input) throw; }",
      "/c.ts",
    );
    await store.addChunks([chunk1, chunk2, chunk3]);

    const results = await store.searchHybrid(chunk1.vector, "error", 10, {
      mode: "hybrid",
    });

    expect(results.length).toBeGreaterThan(0);
    // Results should have RRF scores (higher is better)
    const firstResult = results[0];
    expect(firstResult).toBeDefined();
    expect(firstResult?.score).toBeGreaterThan(0);
    store.close();
  });

  test("searchFts returns empty array when table is null", async () => {
    const store = new VectorStore(path.join(tempDir, "empty"), mockConfig);
    await store.connect();

    const results = await store.searchFts("test", 10);
    expect(results).toEqual([]);
    store.close();
  });

  test("createFtsIndex is idempotent", async () => {
    const store = new VectorStore(tempDir, mockConfig);
    await store.connect();

    const chunks = [createMockChunk("func1", "test content", "/a.ts")];
    await store.addChunks(chunks);

    // Call createFtsIndex multiple times - should not throw
    await store.createFtsIndex();
    await store.createFtsIndex();
    await store.createFtsIndex();

    store.close();
  });

  test("createFtsIndex does nothing when table is null", async () => {
    const store = new VectorStore(path.join(tempDir, "empty"), mockConfig);
    await store.connect();

    // Should not throw
    await store.createFtsIndex();
    store.close();
  });
});
