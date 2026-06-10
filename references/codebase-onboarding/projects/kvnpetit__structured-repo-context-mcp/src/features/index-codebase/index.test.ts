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
import { execute, indexCodebaseSchema } from "@features/index-codebase";
import * as embeddings from "@core/embeddings";

// Mock the entire embeddings module
vi.mock("@core/embeddings");

describe("indexCodebaseSchema", () => {
  test("applies default directory", () => {
    const result = indexCodebaseSchema.safeParse({});
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.directory).toBe(".");
    }
  });

  test("validates valid input", () => {
    const result = indexCodebaseSchema.safeParse({
      directory: "/test/dir",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.directory).toBe("/test/dir");
    }
  });

  test("validates optional fields", () => {
    const result = indexCodebaseSchema.safeParse({
      directory: "/test/dir",
      force: true,
      concurrency: 4,
      exclude: ["*.log"],
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.force).toBe(true);
      expect(result.data.exclude).toEqual(["*.log"]);
    }
  });

  test("applies defaults", () => {
    const result = indexCodebaseSchema.safeParse({
      directory: "/test/dir",
    });
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.force).toBe(false);
      expect(result.data.exclude).toEqual([]);
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
  let mockClear: Mock;
  let mockAddChunks: Mock;

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "index-test-"));
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
    mockExists = vi.fn().mockReturnValue(false);
    mockConnect = vi.fn().mockResolvedValue(undefined);
    mockClose = vi.fn().mockResolvedValue(undefined);
    mockClear = vi.fn().mockResolvedValue(undefined);
    mockAddChunks = vi.fn().mockResolvedValue(undefined);

    vi.mocked(embeddings.createOllamaClient).mockReturnValue({
      healthCheck: mockHealthCheck,
      embedBatch: mockEmbedBatch,
    } as unknown as embeddings.OllamaClient);

    vi.mocked(embeddings.createVectorStore).mockReturnValue({
      exists: mockExists,
      connect: mockConnect,
      close: mockClose,
      clear: mockClear,
      addChunks: mockAddChunks,
    } as unknown as embeddings.VectorStore);

    vi.mocked(embeddings.chunkFile).mockImplementation(
      async (filePath: string, content: string) =>
        Promise.resolve([
          {
            id: "chunk_1",
            content,
            filePath,
            language: "typescript",
            startLine: 1,
            endLine: 1,
          },
        ]),
    );

    // Mock enrichChunksFromFile to return enriched chunks
    vi.mocked(embeddings.enrichChunksFromFile).mockImplementation(
      async (chunks) =>
        Promise.resolve(
          chunks.map((chunk) => ({
            ...chunk,
            enrichedContent: chunk.content,
            containedSymbols: [],
            wasEnriched: false,
          })),
        ),
    );

    vi.mocked(embeddings.shouldIndexFile).mockImplementation(
      (filePath: string) =>
        filePath.endsWith(".ts") || filePath.endsWith(".js"),
    );
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  test("returns error for non-existent directory", async () => {
    const result = await execute({
      directory: "/nonexistent/path",
      force: false,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("Directory not found");
  });

  test("returns message for empty directory", async () => {
    const result = await execute({
      directory: tempDir,
      force: false,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(true);
    expect(result.message).toContain("No indexable files found");
  });

  test("indexes TypeScript files", async () => {
    // Create test files
    fs.writeFileSync(
      path.join(tempDir, "test.ts"),
      'export function hello() { return "world"; }',
    );

    const result = await execute({
      directory: tempDir,
      force: false,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(true);
    expect(result.data).toHaveProperty("filesIndexed", 1);
    expect(result.data).toHaveProperty("chunksCreated");
  });

  test("excludes specified patterns", async () => {
    // Create files
    fs.writeFileSync(path.join(tempDir, "included.ts"), "export const x = 1;");
    fs.mkdirSync(path.join(tempDir, "excluded"));
    fs.writeFileSync(
      path.join(tempDir, "excluded", "skip.ts"),
      "export const y = 2;",
    );

    const result = await execute({
      directory: tempDir,
      force: false,
      concurrency: 4,
      exclude: ["excluded"],
    });

    expect(result.success).toBe(true);
    expect(result.data).toHaveProperty("filesIndexed", 1);
  });

  test("excludes patterns from .gitignore", async () => {
    // Create .gitignore with node_modules
    fs.writeFileSync(path.join(tempDir, ".gitignore"), "node_modules\n");

    // Create files
    fs.writeFileSync(path.join(tempDir, "main.ts"), 'import x from "pkg";');
    fs.mkdirSync(path.join(tempDir, "node_modules"));
    fs.writeFileSync(
      path.join(tempDir, "node_modules", "pkg.ts"),
      "export default 1;",
    );

    const result = await execute({
      directory: tempDir,
      force: false,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(true);
    expect(result.data).toHaveProperty("filesIndexed", 1);
  });

  test("excludes hidden folders starting with dot", async () => {
    // Create files
    fs.writeFileSync(path.join(tempDir, "main.ts"), "export const x = 1;");
    fs.mkdirSync(path.join(tempDir, ".hidden"));
    fs.writeFileSync(
      path.join(tempDir, ".hidden", "secret.ts"),
      "export default 1;",
    );

    const result = await execute({
      directory: tempDir,
      force: false,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(true);
    expect(result.data).toHaveProperty("filesIndexed", 1);
  });

  test("returns error when Ollama health check fails", async () => {
    mockHealthCheck.mockResolvedValue({
      ok: false,
      error: "Ollama unavailable",
    });

    const result = await execute({
      directory: tempDir,
      force: false,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("Ollama unavailable");
  });

  test("returns error when Ollama health check fails without message", async () => {
    mockHealthCheck.mockResolvedValue({ ok: false });

    const result = await execute({
      directory: tempDir,
      force: false,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("Ollama is not available");
  });

  test("returns error when index exists and force is false", async () => {
    mockExists.mockReturnValue(true);

    const result = await execute({
      directory: tempDir,
      force: false,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("Index already exists");
  });

  test("clears existing index when force is true", async () => {
    mockExists.mockReturnValue(true);
    fs.writeFileSync(path.join(tempDir, "test.ts"), "export const x = 1;");

    const result = await execute({
      directory: tempDir,
      force: true,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(true);
    expect(mockClear).toHaveBeenCalled();
  });

  test("handles file processing errors", async () => {
    fs.writeFileSync(path.join(tempDir, "test.ts"), "export const x = 1;");

    vi.mocked(embeddings.chunkFile).mockRejectedValueOnce(
      new Error("Parse error"),
    );

    const result = await execute({
      directory: tempDir,
      force: false,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(true);
    const data = result.data as { errors: string[] };
    expect(data.errors.length).toBeGreaterThan(0);
    expect(data.errors[0]).toContain("Error processing");
  });

  test("handles embedding batch errors", async () => {
    fs.writeFileSync(path.join(tempDir, "test.ts"), "export const x = 1;");

    mockEmbedBatch.mockRejectedValueOnce(new Error("Embedding failed"));

    const result = await execute({
      directory: tempDir,
      force: false,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(true);
    const data = result.data as { errors: string[] };
    expect(data.errors.length).toBeGreaterThan(0);
    expect(data.errors[0]).toContain("Embedding batch error");
  });

  test("reports message with errors when partial success", async () => {
    fs.writeFileSync(path.join(tempDir, "test1.ts"), "export const a = 1;");
    fs.writeFileSync(path.join(tempDir, "test2.ts"), "export const b = 2;");

    vi.mocked(embeddings.chunkFile)
      .mockResolvedValueOnce([
        {
          id: "1",
          content: "a",
          filePath: "test1.ts",
          language: "typescript",
          startLine: 1,
          endLine: 1,
        },
      ])
      .mockRejectedValueOnce(new Error("Parse error"));

    const result = await execute({
      directory: tempDir,
      force: false,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(true);
    expect(result.message).toContain("with");
    expect(result.message).toContain("errors");
  });

  test("handles global indexing errors", async () => {
    fs.writeFileSync(path.join(tempDir, "test.ts"), "export const x = 1;");

    mockConnect.mockRejectedValueOnce(new Error("Connection failed"));

    const result = await execute({
      directory: tempDir,
      force: false,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("Indexing failed");
    expect(result.error).toContain("Connection failed");
  });

  test("handles non-Error exceptions in file processing", async () => {
    fs.writeFileSync(path.join(tempDir, "test.ts"), "export const x = 1;");

    vi.mocked(embeddings.chunkFile).mockRejectedValueOnce("string error");

    const result = await execute({
      directory: tempDir,
      force: false,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(true);
    const data = result.data as { errors: string[] };
    expect(data.errors[0]).toContain("string error");
  });

  test("handles non-Error exceptions in embedding batch", async () => {
    fs.writeFileSync(path.join(tempDir, "test.ts"), "export const x = 1;");

    mockEmbedBatch.mockRejectedValueOnce("embedding string error");

    const result = await execute({
      directory: tempDir,
      force: false,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(true);
    const data = result.data as { errors: string[] };
    expect(data.errors[0]).toContain("embedding string error");
  });

  test("handles non-Error exceptions in global catch", async () => {
    fs.writeFileSync(path.join(tempDir, "test.ts"), "export const x = 1;");

    mockConnect.mockRejectedValueOnce("connection string error");

    const result = await execute({
      directory: tempDir,
      force: false,
      concurrency: 4,
      exclude: [],
    });

    expect(result.success).toBe(false);
    expect(result.error).toContain("connection string error");
  });
});
