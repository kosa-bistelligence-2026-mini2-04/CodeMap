import {
  afterEach,
  beforeEach,
  describe,
  expect,
  test,
  vi,
  type Mock,
} from "vitest";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { execute, searchCodeSchema } from "@features/search-code";
import * as embeddings from "@core/embeddings";

// Mock the embeddings module
vi.mock("@core/embeddings");

describe("searchCodeSchema", () => {
  test("validates required fields", () => {
    const result = searchCodeSchema.safeParse({});
    expect(result.success).toBe(false);
  });

  test("validates valid input", () => {
    const result = searchCodeSchema.safeParse({
      query: "parse AST",
      directory: "/test/dir",
    });
    expect(result.success).toBe(true);
  });

  test("validates query is not empty", () => {
    const result = searchCodeSchema.safeParse({
      query: "",
      directory: "/test/dir",
    });
    expect(result.success).toBe(false);
  });

  test("validates limit is positive integer", () => {
    const result = searchCodeSchema.safeParse({
      query: "test",
      directory: "/test/dir",
      limit: -1,
    });
    expect(result.success).toBe(false);
  });

  test("validates threshold range", () => {
    const valid = searchCodeSchema.safeParse({
      query: "test",
      directory: "/test/dir",
      threshold: 1.5,
    });
    expect(valid.success).toBe(true);

    const invalid = searchCodeSchema.safeParse({
      query: "test",
      directory: "/test/dir",
      threshold: 3,
    });
    expect(invalid.success).toBe(false);
  });

  test("applies defaults", () => {
    const result = searchCodeSchema.safeParse({
      query: "test",
      directory: "/test/dir",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.limit).toBe(10);
      expect(result.data.mode).toBe("hybrid");
      expect(result.data.includeCallContext).toBe(true);
    }
  });

  test("validates mode enum values", () => {
    const validModes = ["vector", "fts", "hybrid"];
    for (const mode of validModes) {
      const result = searchCodeSchema.safeParse({
        query: "test",
        directory: "/test/dir",
        mode,
      });
      expect(result.success).toBe(true);
    }

    const invalidResult = searchCodeSchema.safeParse({
      query: "test",
      directory: "/test/dir",
      mode: "invalid",
    });
    expect(invalidResult.success).toBe(false);
  });
});

describe("execute", () => {
  let tempDir: string;
  let mockHealthCheck: Mock;
  let mockEmbed: Mock;
  let mockExists: Mock;
  let mockConnect: Mock;
  let mockClose: Mock;
  let mockSearchHybrid: Mock;

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "search-test-"));
    vi.clearAllMocks();

    // Setup mocks
    mockHealthCheck = vi.fn().mockResolvedValue({ ok: true });
    mockEmbed = vi
      .fn()
      .mockResolvedValue(new Array(768).fill(0).map(() => Math.random()));
    mockExists = vi.fn().mockReturnValue(true);
    mockConnect = vi.fn().mockResolvedValue(undefined);
    mockClose = vi.fn().mockResolvedValue(undefined);
    mockSearchHybrid = vi.fn().mockResolvedValue([
      {
        chunk: {
          id: "chunk_1",
          content: 'function hello() { return "world"; }',
          filePath: "/test/file.ts",
          language: "typescript",
          startLine: 1,
          endLine: 3,
          symbolName: "hello",
          symbolType: "function",
        },
        score: 0.5,
      },
    ]);

    vi.mocked(embeddings.createOllamaClient).mockReturnValue({
      healthCheck: mockHealthCheck,
      embed: mockEmbed,
    } as unknown as embeddings.OllamaClient);

    vi.mocked(embeddings.createVectorStore).mockReturnValue({
      exists: mockExists,
      connect: mockConnect,
      close: mockClose,
      searchHybrid: mockSearchHybrid,
    } as unknown as embeddings.VectorStore);
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  test("returns error for non-existent directory", async () => {
    const result = await execute({
      query: "test query",
      directory: "/nonexistent/path",
      limit: 10,
      mode: "hybrid",
      includeCallContext: false,
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("Directory not found");
  });

  test("searches successfully with results", async () => {
    const result = await execute({
      query: "hello function",
      directory: tempDir,
      limit: 10,
      mode: "hybrid",
      includeCallContext: false,
    });

    expect(result.success).toBe(true);
    expect(result.data).toHaveProperty("results");
    expect(result.data).toHaveProperty("resultsCount");
    expect(result.message).toContain("Found");
  });

  test("includes query in output", async () => {
    const result = await execute({
      query: "specific query",
      directory: tempDir,
      limit: 5,
      mode: "hybrid",
      includeCallContext: false,
    });

    expect(result.success).toBe(true);
    expect(result.data).toHaveProperty("query", "specific query");
  });

  test("returns error when index does not exist", async () => {
    mockExists.mockReturnValue(false);

    const result = await execute({
      query: "test query",
      directory: tempDir,
      limit: 10,
      mode: "hybrid",
      includeCallContext: false,
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("No index found");
  });

  test("returns error when Ollama health check fails", async () => {
    mockHealthCheck.mockResolvedValue({
      ok: false,
      error: "Ollama not running",
    });

    const result = await execute({
      query: "test query",
      directory: tempDir,
      limit: 10,
      mode: "hybrid",
      includeCallContext: false,
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("Ollama not running");
  });

  test("returns error when Ollama health check fails without message", async () => {
    mockHealthCheck.mockResolvedValue({ ok: false });

    const result = await execute({
      query: "test query",
      directory: tempDir,
      limit: 10,
      mode: "hybrid",
      includeCallContext: false,
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("Ollama is not available");
  });

  test("filters results by threshold in vector mode", async () => {
    mockSearchHybrid.mockResolvedValue([
      {
        chunk: {
          id: "1",
          content: "a",
          filePath: "/a.ts",
          language: "typescript",
          startLine: 1,
          endLine: 1,
        },
        score: 0.3,
      },
      {
        chunk: {
          id: "2",
          content: "b",
          filePath: "/b.ts",
          language: "typescript",
          startLine: 1,
          endLine: 1,
        },
        score: 0.8,
      },
    ]);

    const result = await execute({
      query: "test",
      directory: tempDir,
      limit: 10,
      threshold: 0.5,
      mode: "vector",
      includeCallContext: false,
    });

    expect(result.success).toBe(true);
    const data = result.data as { resultsCount: number };
    expect(data.resultsCount).toBe(1);
  });

  test("does not filter by threshold in hybrid mode", async () => {
    mockSearchHybrid.mockResolvedValue([
      {
        chunk: {
          id: "1",
          content: "a",
          filePath: "/a.ts",
          language: "typescript",
          startLine: 1,
          endLine: 1,
        },
        score: 0.3,
      },
      {
        chunk: {
          id: "2",
          content: "b",
          filePath: "/b.ts",
          language: "typescript",
          startLine: 1,
          endLine: 1,
        },
        score: 0.8,
      },
    ]);

    const result = await execute({
      query: "test",
      directory: tempDir,
      limit: 10,
      threshold: 0.5,
      mode: "hybrid",
      includeCallContext: false,
    });

    expect(result.success).toBe(true);
    const data = result.data as { resultsCount: number };
    // Both results should be returned in hybrid mode (threshold ignored)
    expect(data.resultsCount).toBe(2);
  });

  test("returns message when no results found", async () => {
    mockSearchHybrid.mockResolvedValue([]);

    const result = await execute({
      query: "nonexistent code",
      directory: tempDir,
      limit: 10,
      mode: "hybrid",
      includeCallContext: false,
    });

    expect(result.success).toBe(true);
    expect(result.message).toBe("No matching code found");
  });

  test("handles search errors", async () => {
    mockSearchHybrid.mockRejectedValue(new Error("Database error"));

    const result = await execute({
      query: "test query",
      directory: tempDir,
      limit: 10,
      mode: "hybrid",
      includeCallContext: false,
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("Search failed");
    expect(result.error).toContain("Database error");
  });

  test("handles non-Error exceptions", async () => {
    mockSearchHybrid.mockRejectedValue("string error");

    const result = await execute({
      query: "test query",
      directory: tempDir,
      limit: 10,
      mode: "hybrid",
      includeCallContext: false,
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("Search failed");
    expect(result.error).toContain("string error");
  });

  test("formats results without symbol info", async () => {
    mockSearchHybrid.mockResolvedValue([
      {
        chunk: {
          id: "chunk_1",
          content: "const x = 1;",
          filePath: "/test/file.ts",
          language: "typescript",
          startLine: 1,
          endLine: 1,
        },
        score: 0.5,
      },
    ]);

    const result = await execute({
      query: "test",
      directory: tempDir,
      limit: 10,
      mode: "hybrid",
      includeCallContext: false,
    });

    expect(result.success).toBe(true);
    expect(result.message).toContain("[typescript]");
    expect(result.message).not.toContain("(symbol:");
  });

  test("uses fts mode when specified", async () => {
    const result = await execute({
      query: "test query",
      directory: tempDir,
      limit: 10,
      mode: "fts",
      includeCallContext: false,
    });

    expect(result.success).toBe(true);
    expect(mockSearchHybrid).toHaveBeenCalledWith(
      expect.any(Array),
      "test query",
      10,
      { mode: "fts" },
    );
  });

  test("uses vector mode when specified", async () => {
    const result = await execute({
      query: "test query",
      directory: tempDir,
      limit: 10,
      mode: "vector",
      includeCallContext: false,
    });

    expect(result.success).toBe(true);
    expect(mockSearchHybrid).toHaveBeenCalledWith(
      expect.any(Array),
      "test query",
      10,
      { mode: "vector" },
    );
  });
});
