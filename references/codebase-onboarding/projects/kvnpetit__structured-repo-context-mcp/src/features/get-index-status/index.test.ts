import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { execute, getIndexStatusSchema } from "@features/get-index-status";
import * as embeddings from "@core/embeddings";

// Mock the embeddings module
vi.mock("@core/embeddings");

describe("getIndexStatusSchema", () => {
  test("applies default directory", () => {
    const result = getIndexStatusSchema.safeParse({});
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.directory).toBe(".");
    }
  });

  test("validates valid input", () => {
    const result = getIndexStatusSchema.safeParse({
      directory: "/test/dir",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.directory).toBe("/test/dir");
    }
  });
});

describe("execute", () => {
  let tempDir: string;

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "status-test-"));
    vi.clearAllMocks();

    // Setup mocks
    vi.mocked(embeddings.createVectorStore).mockReturnValue({
      exists: vi.fn().mockReturnValue(true),
      connect: vi.fn().mockResolvedValue(undefined),
      close: vi.fn().mockResolvedValue(undefined),
      getStatus: vi.fn().mockResolvedValue({
        directory: "/test/dir",
        indexPath: "/test/dir/.src-index",
        exists: true,
        totalChunks: 100,
        totalFiles: 10,
        languages: {
          typescript: 60,
          javascript: 30,
          python: 10,
        },
      }),
    } as unknown as embeddings.VectorStore);

    vi.mocked(embeddings.getIndexPath).mockImplementation((dir: string) =>
      path.join(dir, ".src-index"),
    );
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  test("returns error for non-existent directory", async () => {
    const result = await execute({
      directory: "/nonexistent/path",
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("Directory not found");
  });

  test("returns status for non-indexed directory", async () => {
    // Create a temp dir without an index
    const noIndexDir = fs.mkdtempSync(path.join(os.tmpdir(), "no-index-"));

    const result = await execute({
      directory: noIndexDir,
    });

    expect(result.success).toBe(true);
    expect(result.message).toContain("No index found");
    expect(result.data).toHaveProperty("exists", false);

    fs.rmSync(noIndexDir, { recursive: true, force: true });
  });

  test("returns status for indexed directory", async () => {
    // Create mock index directory
    const indexDir = path.join(tempDir, ".src-index");
    fs.mkdirSync(indexDir);

    const result = await execute({
      directory: tempDir,
    });

    expect(result.success).toBe(true);
    expect(result.data).toHaveProperty("totalChunks");
    expect(result.data).toHaveProperty("totalFiles");
    expect(result.data).toHaveProperty("languages");
  });

  test("includes language breakdown in message", async () => {
    // Create mock index directory
    const indexDir = path.join(tempDir, ".src-index");
    fs.mkdirSync(indexDir);

    const result = await execute({
      directory: tempDir,
    });

    expect(result.success).toBe(true);
    expect(result.message).toContain("typescript");
    expect(result.message).toContain("javascript");
    expect(result.message).toContain("python");
  });

  test("handles errors when reading index status", async () => {
    // Create mock index directory
    const indexDir = path.join(tempDir, ".src-index");
    fs.mkdirSync(indexDir);

    // Override mock to throw error
    const { createVectorStore } = await import("@core/embeddings");
    vi.mocked(createVectorStore).mockReturnValueOnce({
      exists: vi.fn().mockReturnValue(true),
      connect: vi.fn().mockRejectedValue(new Error("Connection failed")),
      close: vi.fn(),
      getStatus: vi.fn(),
    } as unknown as ReturnType<typeof createVectorStore>);

    const result = await execute({
      directory: tempDir,
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("Failed to read index status");
    expect(result.error).toContain("Connection failed");
  });

  test("handles non-Error exceptions", async () => {
    const indexDir = path.join(tempDir, ".src-index");
    fs.mkdirSync(indexDir);

    const { createVectorStore } = await import("@core/embeddings");
    vi.mocked(createVectorStore).mockReturnValueOnce({
      exists: vi.fn().mockReturnValue(true),
      connect: vi.fn().mockRejectedValue("string error"),
      close: vi.fn(),
      getStatus: vi.fn(),
    } as unknown as ReturnType<typeof createVectorStore>);

    const result = await execute({
      directory: tempDir,
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("string error");
  });
});
