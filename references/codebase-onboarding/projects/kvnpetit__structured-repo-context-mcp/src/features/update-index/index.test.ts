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
import { execute, updateIndexSchema } from "@features/update-index";
import * as embeddings from "@core/embeddings";

// Mock the entire embeddings module
vi.mock("@core/embeddings");

describe("updateIndexSchema", () => {
  test("applies default directory", () => {
    const result = updateIndexSchema.safeParse({});
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.directory).toBe(".");
    }
  });

  test("validates valid input", () => {
    const result = updateIndexSchema.safeParse({
      directory: "/test/dir",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.directory).toBe("/test/dir");
    }
  });

  test("validates optional fields", () => {
    const result = updateIndexSchema.safeParse({
      directory: "/test/dir",
      dryRun: true,
      force: true,
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.dryRun).toBe(true);
      expect(result.data.force).toBe(true);
    }
  });

  test("applies defaults", () => {
    const result = updateIndexSchema.safeParse({
      directory: "/test/dir",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.dryRun).toBe(false);
      expect(result.data.force).toBe(false);
    }
  });
});

describe("execute", () => {
  let tempDir: string;
  let mockHealthCheck: Mock;
  let mockEmbedBatch: Mock;
  let mockExists: Mock;
  let mockConnect: Mock;
  let mockClose: Mock;
  let mockAddChunks: Mock;
  let mockGetIndexedFiles: Mock;
  let mockDeleteByFilePath: Mock;

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "update-index-test-"));
    vi.clearAllMocks();

    // Setup mocks
    mockHealthCheck = vi.fn().mockResolvedValue({ ok: true });
    mockEmbedBatch = vi
      .fn()
      .mockImplementation(async (texts: string[]) =>
        Promise.resolve(
          texts.map(() => new Array(768).fill(0).map(() => Math.random())),
        ),
      );
    mockExists = vi.fn().mockReturnValue(true);
    mockConnect = vi.fn().mockResolvedValue(undefined);
    mockClose = vi.fn().mockResolvedValue(undefined);
    mockAddChunks = vi.fn().mockResolvedValue(undefined);
    mockGetIndexedFiles = vi.fn().mockResolvedValue([]);
    mockDeleteByFilePath = vi.fn().mockResolvedValue(undefined);

    vi.mocked(embeddings.createOllamaClient).mockReturnValue({
      healthCheck: mockHealthCheck,
      embedBatch: mockEmbedBatch,
    } as unknown as embeddings.OllamaClient);

    vi.mocked(embeddings.createVectorStore).mockReturnValue({
      exists: mockExists,
      connect: mockConnect,
      close: mockClose,
      addChunks: mockAddChunks,
      getIndexedFiles: mockGetIndexedFiles,
      deleteByFilePath: mockDeleteByFilePath,
    } as unknown as embeddings.VectorStore);

    vi.mocked(embeddings.chunkFile).mockResolvedValue([
      {
        id: "chunk-1",
        content: "test content",
        filePath: "/test/file.ts",
        language: "typescript",
        startLine: 1,
        endLine: 10,
      },
    ]);

    vi.mocked(embeddings.enrichChunksFromFile).mockImplementation(
      async (chunks) =>
        Promise.resolve(
          chunks.map((c) => ({
            ...c,
            enrichedContent: c.content,
            containedSymbols: [],
            wasEnriched: true,
          })),
        ),
    );

    vi.mocked(embeddings.shouldIndexFile).mockReturnValue(true);
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
    vi.clearAllMocks();
  });

  test("returns error for non-existent directory", async () => {
    const result = await execute({
      directory: "/non/existent/directory",
      dryRun: false,
      force: false,
    });
    expect(result.success).toBe(false);
    expect(result.error).toContain("Directory not found");
  });

  test("returns error when index does not exist", async () => {
    mockExists.mockReturnValue(false);
    const result = await execute({
      directory: tempDir,
      dryRun: false,
      force: false,
    });
    expect(result.success).toBe(false);
    expect(result.error).toContain("No index found");
  });

  test("returns error when Ollama health check fails", async () => {
    mockHealthCheck.mockResolvedValue({
      ok: false,
      error: "Connection refused",
    });
    const result = await execute({
      directory: tempDir,
      dryRun: false,
      force: false,
    });
    expect(result.success).toBe(false);
    expect(result.error).toContain("Connection refused");
  });

  test("returns error when Ollama health check fails without message", async () => {
    mockHealthCheck.mockResolvedValue({ ok: false });
    const result = await execute({
      directory: tempDir,
      dryRun: false,
      force: false,
    });
    expect(result.success).toBe(false);
    expect(result.error).toContain("Ollama is not available");
  });

  test("dry run reports no changes when index is up to date", async () => {
    const result = await execute({
      directory: tempDir,
      dryRun: true,
      force: false,
    });
    expect(result.success).toBe(true);
    expect(result.message).toContain("up to date");
  });

  test("dry run detects new files", async () => {
    // Create a test file
    const testFile = path.join(tempDir, "test.ts");
    fs.writeFileSync(testFile, "const x = 1;");

    const result = await execute({
      directory: tempDir,
      dryRun: true,
      force: false,
    });

    expect(result.success).toBe(true);
    expect(result.message).toContain("add");
  });

  test("detects and removes deleted files", async () => {
    // Mock that a file exists in index but not on disk
    const deletedFile = path.join(tempDir, "deleted.ts");
    mockGetIndexedFiles.mockResolvedValue([deletedFile]);

    const result = await execute({
      directory: tempDir,
      dryRun: true,
      force: false,
    });

    expect(result.success).toBe(true);
    expect(result.message).toContain("remove");
  });

  test("processes new files successfully", async () => {
    // Create a test file
    const testFile = path.join(tempDir, "test.ts");
    fs.writeFileSync(testFile, "const x = 1;");

    const result = await execute({
      directory: tempDir,
      dryRun: false,
      force: false,
    });

    expect(result.success).toBe(true);
    expect(mockAddChunks).toHaveBeenCalled();
  });

  test("handles errors during file processing", async () => {
    // Create a test file
    const testFile = path.join(tempDir, "test.ts");
    fs.writeFileSync(testFile, "const x = 1;");

    vi.mocked(embeddings.chunkFile).mockRejectedValue(new Error("Parse error"));

    const result = await execute({
      directory: tempDir,
      dryRun: false,
      force: false,
    });

    expect(result.success).toBe(true);
    expect(result.data).toHaveProperty("errors");
  });

  test("handles general errors", async () => {
    mockConnect.mockRejectedValue(new Error("Connection failed"));

    const result = await execute({
      directory: tempDir,
      dryRun: false,
      force: false,
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("Update failed");
  });

  test("handles non-Error exceptions", async () => {
    mockConnect.mockRejectedValue("String error");

    const result = await execute({
      directory: tempDir,
      dryRun: false,
      force: false,
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("String error");
  });

  test("force flag ignores hash cache", async () => {
    // Create hash cache directory and file
    const indexDir = path.join(tempDir, ".src-index");
    fs.mkdirSync(indexDir, { recursive: true });
    const hashCachePath = path.join(indexDir, ".src-index-hashes.json");

    // Create a test file
    const testFile = path.join(tempDir, "test.ts");
    fs.writeFileSync(testFile, "const x = 1;");

    // Create hash cache with the same hash
    const content = fs.readFileSync(testFile, "utf-8");
    const crypto = await import("node:crypto");
    const hash = crypto
      .createHash("sha256")
      .update(content, "utf8")
      .digest("hex");
    fs.writeFileSync(hashCachePath, JSON.stringify({ [testFile]: hash }));

    // Also mock it as indexed
    mockGetIndexedFiles.mockResolvedValue([testFile]);

    // Without force, file should be unchanged
    const resultNoForce = await execute({
      directory: tempDir,
      dryRun: true,
      force: false,
    });
    expect(resultNoForce.success).toBe(true);
    expect(resultNoForce.message).toContain("up to date");

    // With force, file should be detected as modified
    const resultWithForce = await execute({
      directory: tempDir,
      dryRun: true,
      force: true,
    });
    expect(resultWithForce.success).toBe(true);
    // Force treats all indexed files as modified
  });

  test("removes deleted files from index", async () => {
    const deletedFile = path.join(tempDir, "deleted.ts");
    mockGetIndexedFiles.mockResolvedValue([deletedFile]);

    const result = await execute({
      directory: tempDir,
      dryRun: false,
      force: false,
    });

    expect(result.success).toBe(true);
    expect(mockDeleteByFilePath).toHaveBeenCalledWith(deletedFile);
  });
});
