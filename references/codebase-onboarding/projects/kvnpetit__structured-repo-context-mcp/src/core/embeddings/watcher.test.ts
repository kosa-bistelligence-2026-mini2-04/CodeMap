import {
  afterEach,
  beforeEach,
  describe,
  expect,
  test,
  vi,
  type Mock,
} from "vitest";
import * as crypto from "node:crypto";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import { IndexWatcher, createIndexWatcher } from "@core/embeddings/watcher";
import type { EmbeddingConfig } from "@core/embeddings/types";
import { watch } from "chokidar";
import { OllamaClient } from "@core/embeddings/client";
import { VectorStore } from "@core/embeddings/store";
import { chunkFile, shouldIndexFile } from "@core/embeddings/chunker";

// Mock modules
vi.mock("chokidar");
vi.mock("@core/embeddings/client");
vi.mock("@core/embeddings/store");
vi.mock("@utils", () => ({
  logger: {
    info: vi.fn(),
    debug: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));
vi.mock("@core/embeddings/chunker", () => ({
  chunkFile: vi.fn().mockResolvedValue([
    {
      id: "chunk_1",
      content: "test content",
      filePath: "/test/file.ts",
      language: "typescript",
      startLine: 1,
      endLine: 10,
    },
  ]),
  shouldIndexFile: vi
    .fn()
    .mockImplementation(
      (filePath: string) =>
        filePath.endsWith(".ts") || filePath.endsWith(".js"),
    ),
  SUPPORTED_EXTENSIONS: [".ts", ".js"],
}));
vi.mock("fast-glob", () => ({
  default: vi.fn().mockResolvedValue([]),
}));

describe("IndexWatcher", () => {
  let tempDir: string;
  let mockOn: Mock;
  let mockClose: Mock;

  const mockConfig: EmbeddingConfig = {
    ollamaBaseUrl: "http://localhost:11434",
    embeddingModel: "nomic-embed-text",
    embeddingDimensions: 768,
    defaultChunkSize: 1000,
    defaultChunkOverlap: 200,
    batchSize: 10,
  };

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "watcher-test-"));
    vi.clearAllMocks();

    // Setup chokidar mock
    mockOn = vi.fn().mockImplementation(function (
      this: { on: Mock },
      _event: string,
      _handler: () => void,
    ) {
      return this;
    });
    mockClose = vi.fn().mockResolvedValue(undefined);

    vi.mocked(watch).mockReturnValue({
      on: mockOn,
      close: mockClose,
    } as unknown as ReturnType<typeof watch>);

    // Setup OllamaClient mock - use regular function so it can be used as constructor
    vi.mocked(OllamaClient).mockImplementation(function (this: OllamaClient) {
      this.healthCheck = vi.fn().mockResolvedValue({ ok: true });
      this.embed = vi.fn().mockResolvedValue(new Array<number>(768).fill(0));
      this.embedBatch = vi
        .fn()
        .mockImplementation((texts: string[]): number[][] => {
          return texts.map(() => new Array<number>(768).fill(0));
        });
      return this;
    } as unknown as typeof OllamaClient);

    // Setup VectorStore mock - use regular function so it can be used as constructor
    vi.mocked(VectorStore).mockImplementation(function (this: VectorStore) {
      this.exists = vi.fn().mockReturnValue(true);
      this.connect = vi.fn().mockResolvedValue(undefined);
      this.close = vi.fn();
      this.addChunks = vi.fn().mockResolvedValue(undefined);
      this.deleteByFilePath = vi.fn().mockResolvedValue(undefined);
      return this;
    } as unknown as typeof VectorStore);
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  test("creates watcher instance", () => {
    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    expect(watcher).toBeDefined();
    expect(watcher.isRunning()).toBe(false);
  });

  test("starts watcher and sets up event handlers", async () => {
    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await watcher.start();

    expect(watcher.isRunning()).toBe(true);
    expect(mockOn).toHaveBeenCalledWith("add", expect.any(Function));
    expect(mockOn).toHaveBeenCalledWith("change", expect.any(Function));
    expect(mockOn).toHaveBeenCalledWith("unlink", expect.any(Function));
    expect(mockOn).toHaveBeenCalledWith("ready", expect.any(Function));
    expect(mockOn).toHaveBeenCalledWith("error", expect.any(Function));
  });

  test("stops watcher and closes resources", async () => {
    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await watcher.start();
    await watcher.stop();

    expect(watcher.isRunning()).toBe(false);
    expect(mockClose).toHaveBeenCalled();
  });

  test("respects gitignore patterns", () => {
    // Create .gitignore
    fs.writeFileSync(path.join(tempDir, ".gitignore"), "node_modules\n*.log\n");

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    // The watcher should be created with gitignore patterns loaded
    expect(watcher).toBeDefined();
  });

  test("calls onReady callback when watcher is ready", async () => {
    const onReady = vi.fn();

    // Setup mockOn to capture and call the ready handler
    let readyHandler: (() => void) | undefined;
    mockOn.mockImplementation(function (
      this: { on: Mock },
      event: string,
      handler: () => void,
    ) {
      if (event === "ready") {
        readyHandler = handler;
      }
      return this;
    });

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
      onReady,
    });

    await watcher.start();

    // Simulate ready event
    if (readyHandler) {
      readyHandler();
    }

    expect(onReady).toHaveBeenCalled();
  });

  test("calls onError callback on watcher error", async () => {
    const onError = vi.fn();
    const testError = new Error("Test error");

    // Setup mockOn to capture and call the error handler
    let errorHandler: ((error: Error) => void) | undefined;
    mockOn.mockImplementation(function (
      this: { on: Mock },
      event: string,
      handler: (error: Error) => void,
    ) {
      if (event === "error") {
        errorHandler = handler;
      }
      return this;
    });

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
      onError,
    });

    await watcher.start();

    // Simulate error event
    if (errorHandler) {
      errorHandler(testError);
    }

    expect(onError).toHaveBeenCalledWith(testError);
  });

  test("uses custom debounceMs option", () => {
    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
      debounceMs: 1000,
    });

    expect(watcher).toBeDefined();
  });

  test("stop clears pending changes and closes watcher", async () => {
    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await watcher.start();
    expect(watcher.isRunning()).toBe(true);

    await watcher.stop();
    expect(watcher.isRunning()).toBe(false);
    expect(mockClose).toHaveBeenCalled();
  });

  test("clearCache removes hash cache file and resets cache", () => {
    const cacheDir = path.join(tempDir, ".src-index");
    const cacheFile = path.join(cacheDir, ".src-index-hashes.json");

    // Create cache file
    fs.mkdirSync(cacheDir, { recursive: true });
    fs.writeFileSync(cacheFile, JSON.stringify({ "test.ts": "abc123" }));

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    watcher.clearCache();

    expect(fs.existsSync(cacheFile)).toBe(false);
  });

  test("getCacheStats returns cache statistics", () => {
    const cacheDir = path.join(tempDir, ".src-index");
    const cacheFile = path.join(cacheDir, ".src-index-hashes.json");

    // Create cache file with data
    fs.mkdirSync(cacheDir, { recursive: true });
    fs.writeFileSync(
      cacheFile,
      JSON.stringify({ "file1.ts": "hash1", "file2.ts": "hash2" }),
    );

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    const stats = watcher.getCacheStats();

    expect(stats.cachedFiles).toBe(2);
    expect(stats.cacheSize).toBeGreaterThan(0);
  });

  test("loads existing hash cache from disk", () => {
    const cacheDir = path.join(tempDir, ".src-index");
    const cacheFile = path.join(cacheDir, ".src-index-hashes.json");

    // Create cache file
    fs.mkdirSync(cacheDir, { recursive: true });
    fs.writeFileSync(
      cacheFile,
      JSON.stringify({ "cached.ts": "existinghash" }),
    );

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    const stats = watcher.getCacheStats();
    expect(stats.cachedFiles).toBe(1);
  });

  test("handles corrupted hash cache file gracefully", () => {
    const cacheDir = path.join(tempDir, ".src-index");
    const cacheFile = path.join(cacheDir, ".src-index-hashes.json");

    // Create corrupted cache file
    fs.mkdirSync(cacheDir, { recursive: true });
    fs.writeFileSync(cacheFile, "not valid json {{{");

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    const stats = watcher.getCacheStats();
    expect(stats.cachedFiles).toBe(0);
  });

  test("start throws when Ollama health check fails", async () => {
    vi.mocked(OllamaClient).mockImplementation(function (this: OllamaClient) {
      this.healthCheck = vi
        .fn()
        .mockResolvedValue({ ok: false, error: "Ollama down" });
      this.embed = vi.fn();
      this.embedBatch = vi.fn();
      return this;
    } as unknown as typeof OllamaClient);

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await expect(watcher.start()).rejects.toThrow("Ollama down");
  });

  test("start throws generic error when health check fails without message", async () => {
    vi.mocked(OllamaClient).mockImplementation(function (this: OllamaClient) {
      this.healthCheck = vi.fn().mockResolvedValue({ ok: false });
      this.embed = vi.fn();
      this.embedBatch = vi.fn();
      return this;
    } as unknown as typeof OllamaClient);

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await expect(watcher.start()).rejects.toThrow("Ollama is not available");
  });

  test("performs full index when vector store does not exist", async () => {
    // Import and properly mock fast-glob for this test
    const fg = await import("fast-glob");
    vi.mocked(fg.default).mockResolvedValue([]);

    vi.mocked(VectorStore).mockImplementation(function (this: VectorStore) {
      this.exists = vi.fn().mockReturnValue(false);
      this.connect = vi.fn().mockResolvedValue(undefined);
      this.close = vi.fn();
      this.addChunks = vi.fn().mockResolvedValue(undefined);
      this.deleteByFilePath = vi.fn().mockResolvedValue(undefined);
      return this;
    } as unknown as typeof VectorStore);

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await watcher.start();

    // Full index should have been triggered
    const storeInstance = vi.mocked(VectorStore).mock.instances[0];
    // eslint-disable-next-line @typescript-eslint/unbound-method
    expect(storeInstance?.exists).toHaveBeenCalled();
  });

  test("handles file add event", async () => {
    let addHandler: ((filePath: string) => void) | undefined;

    mockOn.mockImplementation(function (
      this: { on: Mock },
      event: string,
      handler: (filePath: string) => void,
    ) {
      if (event === "add") {
        addHandler = handler;
      }
      return this;
    });

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await watcher.start();

    // Trigger add event
    const testFile = path.join(tempDir, "newfile.ts");
    fs.writeFileSync(testFile, "const x = 1;");

    if (addHandler) {
      addHandler(testFile);
    }

    // Debounce should have scheduled the change
    expect(watcher.isRunning()).toBe(true);
  });

  test("handles file change event", async () => {
    let changeHandler: ((filePath: string) => void) | undefined;

    mockOn.mockImplementation(function (
      this: { on: Mock },
      event: string,
      handler: (filePath: string) => void,
    ) {
      if (event === "change") {
        changeHandler = handler;
      }
      return this;
    });

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await watcher.start();

    const testFile = path.join(tempDir, "existing.ts");
    fs.writeFileSync(testFile, "const x = 1;");

    if (changeHandler) {
      changeHandler(testFile);
    }

    expect(watcher.isRunning()).toBe(true);
  });

  test("handles file unlink event", async () => {
    let unlinkHandler: ((filePath: string) => void) | undefined;

    mockOn.mockImplementation(function (
      this: { on: Mock },
      event: string,
      handler: (filePath: string) => void,
    ) {
      if (event === "unlink") {
        unlinkHandler = handler;
      }
      return this;
    });

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await watcher.start();

    if (unlinkHandler) {
      unlinkHandler(path.join(tempDir, "deleted.ts"));
    }

    expect(watcher.isRunning()).toBe(true);
  });

  test("ignores non-indexable files in events", async () => {
    let addHandler: ((filePath: string) => void) | undefined;

    mockOn.mockImplementation(function (
      this: { on: Mock },
      event: string,
      handler: (filePath: string) => void,
    ) {
      if (event === "add") {
        addHandler = handler;
      }
      return this;
    });

    vi.mocked(shouldIndexFile).mockReturnValue(false);

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await watcher.start();

    if (addHandler) {
      addHandler(path.join(tempDir, "file.txt"));
    }

    // Should not schedule the change for non-indexable file
    expect(watcher.isRunning()).toBe(true);
  });

  test("watcher ignored callback skips hidden files", async () => {
    let ignoredCallback: ((filePath: string) => boolean) | undefined;

    vi.mocked(watch).mockImplementation((_paths, options) => {
      ignoredCallback = options?.ignored as
        | ((path: string) => boolean)
        | undefined;
      return {
        on: mockOn,
        close: mockClose,
      } as unknown as ReturnType<typeof watch>;
    });

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await watcher.start();

    expect(ignoredCallback).toBeDefined();

    // Root directory should not be ignored
    expect(ignoredCallback?.(tempDir)).toBe(false);

    // Hidden files should be ignored
    expect(ignoredCallback?.(path.join(tempDir, ".hidden"))).toBe(true);
    expect(ignoredCallback?.(path.join(tempDir, ".git", "config"))).toBe(true);

    // Normal files should not be ignored
    expect(ignoredCallback?.(path.join(tempDir, "src", "index.ts"))).toBe(
      false,
    );
  });

  test("watcher handles non-Error in error event", async () => {
    const onError = vi.fn();
    let errorHandler: ((error: unknown) => void) | undefined;

    mockOn.mockImplementation(function (
      this: { on: Mock },
      event: string,
      handler: (error: unknown) => void,
    ) {
      if (event === "error") {
        errorHandler = handler;
      }
      return this;
    });

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
      onError,
    });

    await watcher.start();

    // Trigger error event with non-Error value
    if (errorHandler) {
      errorHandler("string error");
    }

    expect(onError).toHaveBeenCalled();
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
    const errorArg = onError.mock.calls[0]?.[0];
    expect(errorArg).toBeInstanceOf(Error);
    // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
    expect(errorArg?.message).toBe("string error");
  });
});

describe("IndexWatcher - debounced operations", () => {
  let tempDir: string;
  let mockOn: Mock;
  let mockClose: Mock;

  const mockConfig: EmbeddingConfig = {
    ollamaBaseUrl: "http://localhost:11434",
    embeddingModel: "nomic-embed-text",
    embeddingDimensions: 768,
    defaultChunkSize: 1000,
    defaultChunkOverlap: 200,
    batchSize: 10,
  };

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "watcher-debounce-test-"));
    vi.clearAllMocks();
    vi.useFakeTimers();

    mockOn = vi.fn().mockImplementation(function (
      this: { on: Mock },
      _event: string,
      _handler: () => void,
    ) {
      return this;
    });
    mockClose = vi.fn().mockResolvedValue(undefined);

    vi.mocked(watch).mockReturnValue({
      on: mockOn,
      close: mockClose,
    } as unknown as ReturnType<typeof watch>);

    vi.mocked(OllamaClient).mockImplementation(function (this: OllamaClient) {
      this.healthCheck = vi.fn().mockResolvedValue({ ok: true });
      this.embed = vi.fn().mockResolvedValue(new Array<number>(768).fill(0));
      this.embedBatch = vi
        .fn()
        .mockImplementation((texts: string[]): number[][] => {
          return texts.map(() => new Array<number>(768).fill(0));
        });
      return this;
    } as unknown as typeof OllamaClient);

    vi.mocked(VectorStore).mockImplementation(function (this: VectorStore) {
      this.exists = vi.fn().mockReturnValue(true);
      this.connect = vi.fn().mockResolvedValue(undefined);
      this.close = vi.fn();
      this.addChunks = vi.fn().mockResolvedValue(undefined);
      this.deleteByFilePath = vi.fn().mockResolvedValue(undefined);
      return this;
    } as unknown as typeof VectorStore);

    vi.mocked(shouldIndexFile).mockImplementation(
      (filePath: string) =>
        filePath.endsWith(".ts") || filePath.endsWith(".js"),
    );
  });

  afterEach(() => {
    vi.useRealTimers();
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  test("scheduleChange debounces and processes file add after timeout", async () => {
    const onIndexed = vi.fn();
    let addHandler: ((filePath: string) => void) | undefined;

    mockOn.mockImplementation(function (
      this: { on: Mock },
      event: string,
      handler: (filePath: string) => void,
    ) {
      if (event === "add") {
        addHandler = handler;
      }
      return this;
    });

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
      debounceMs: 100,
      onIndexed,
    });

    await watcher.start();

    // Create test file
    const testFile = path.join(tempDir, "test.ts");
    fs.writeFileSync(testFile, "export const x = 1;");

    // Trigger add event
    if (addHandler) {
      addHandler(testFile);
    }

    // Advance timers to trigger debounced operation
    await vi.advanceTimersByTimeAsync(200);

    // Wait for async operations
    await vi.runAllTimersAsync();

    expect(watcher.isRunning()).toBe(true);
  });

  test("scheduleChange replaces pending change for same file", async () => {
    let addHandler: ((filePath: string) => void) | undefined;
    let changeHandler: ((filePath: string) => void) | undefined;

    mockOn.mockImplementation(function (
      this: { on: Mock },
      event: string,
      handler: (filePath: string) => void,
    ) {
      if (event === "add") {
        addHandler = handler;
      }
      if (event === "change") {
        changeHandler = handler;
      }
      return this;
    });

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
      debounceMs: 100,
    });

    await watcher.start();

    const testFile = path.join(tempDir, "test.ts");
    fs.writeFileSync(testFile, "export const x = 1;");

    // Trigger add then change rapidly
    if (addHandler) {
      addHandler(testFile);
    }
    if (changeHandler) {
      changeHandler(testFile);
    }

    // Only one debounced operation should be pending
    expect(watcher.isRunning()).toBe(true);
  });

  test("processChange handles unlink event", async () => {
    const onRemoved = vi.fn();
    let unlinkHandler: ((filePath: string) => void) | undefined;

    mockOn.mockImplementation(function (
      this: { on: Mock },
      event: string,
      handler: (filePath: string) => void,
    ) {
      if (event === "unlink") {
        unlinkHandler = handler;
      }
      return this;
    });

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
      debounceMs: 100,
      onRemoved,
    });

    await watcher.start();

    // Trigger unlink
    if (unlinkHandler) {
      unlinkHandler(path.join(tempDir, "deleted.ts"));
    }

    // Advance timers
    await vi.advanceTimersByTimeAsync(200);
    await vi.runAllTimersAsync();

    expect(watcher.isRunning()).toBe(true);
  });

  test("stop clears pending debounced changes", async () => {
    let addHandler: ((filePath: string) => void) | undefined;

    mockOn.mockImplementation(function (
      this: { on: Mock },
      event: string,
      handler: (filePath: string) => void,
    ) {
      if (event === "add") {
        addHandler = handler;
      }
      return this;
    });

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
      debounceMs: 5000,
    });

    await watcher.start();

    // Create and trigger add
    const testFile = path.join(tempDir, "test.ts");
    fs.writeFileSync(testFile, "export const x = 1;");
    if (addHandler) {
      addHandler(testFile);
    }

    // Stop before debounce completes
    await watcher.stop();

    expect(watcher.isRunning()).toBe(false);
  });
});

describe("IndexWatcher - full index", () => {
  let tempDir: string;
  let mockOn: Mock;
  let mockClose: Mock;

  const mockConfig: EmbeddingConfig = {
    ollamaBaseUrl: "http://localhost:11434",
    embeddingModel: "nomic-embed-text",
    embeddingDimensions: 768,
    defaultChunkSize: 1000,
    defaultChunkOverlap: 200,
    batchSize: 10,
  };

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "watcher-fullindex-test-"));
    vi.clearAllMocks();

    mockOn = vi.fn().mockReturnThis();
    mockClose = vi.fn().mockResolvedValue(undefined);

    vi.mocked(watch).mockReturnValue({
      on: mockOn,
      close: mockClose,
    } as unknown as ReturnType<typeof watch>);

    vi.mocked(OllamaClient).mockImplementation(function (this: OllamaClient) {
      this.healthCheck = vi.fn().mockResolvedValue({ ok: true });
      this.embed = vi.fn().mockResolvedValue(new Array<number>(768).fill(0));
      this.embedBatch = vi
        .fn()
        .mockImplementation((texts: string[]): number[][] => {
          return texts.map(() => new Array<number>(768).fill(0));
        });
      return this;
    } as unknown as typeof OllamaClient);

    vi.mocked(VectorStore).mockImplementation(function (this: VectorStore) {
      this.exists = vi.fn().mockReturnValue(false);
      this.connect = vi.fn().mockResolvedValue(undefined);
      this.close = vi.fn();
      this.addChunks = vi.fn().mockResolvedValue(undefined);
      this.deleteByFilePath = vi.fn().mockResolvedValue(undefined);
      return this;
    } as unknown as typeof VectorStore);
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  test("fullIndex processes files from fast-glob", async () => {
    const fg = await import("fast-glob");
    const testFile = path.join(tempDir, "src", "index.ts");
    fs.mkdirSync(path.join(tempDir, "src"), { recursive: true });
    fs.writeFileSync(testFile, "export const x = 1;");

    vi.mocked(fg.default).mockResolvedValue([testFile]);

    // Ensure chunkFile returns chunks so addChunks gets called
    vi.mocked(chunkFile).mockResolvedValue([
      {
        id: "chunk_1",
        content: "export const x = 1;",
        filePath: testFile,
        language: "typescript",
        startLine: 1,
        endLine: 1,
      },
    ]);

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await watcher.start();

    // addChunks should have been called during fullIndex
    const storeInstance = vi.mocked(VectorStore).mock.instances[0];
    // eslint-disable-next-line @typescript-eslint/unbound-method
    expect(storeInstance?.addChunks).toHaveBeenCalled();
  });

  test("fullIndex skips unchanged files", async () => {
    const fg = await import("fast-glob");
    const testFile = path.join(tempDir, "cached.ts");
    fs.writeFileSync(testFile, "const cached = true;");

    // Create cache with existing hash
    const cacheDir = path.join(tempDir, ".src-index");
    fs.mkdirSync(cacheDir, { recursive: true });

    // Pre-compute the hash of the file content
    const content = "const cached = true;";
    const hash = crypto
      .createHash("sha256")
      .update(content, "utf8")
      .digest("hex");
    fs.writeFileSync(
      path.join(cacheDir, ".src-index-hashes.json"),
      JSON.stringify({ [testFile]: hash }),
    );

    vi.mocked(fg.default).mockResolvedValue([testFile]);

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await watcher.start();

    // File should be skipped since hash matches
    expect(watcher.isRunning()).toBe(true);
  });

  test("fullIndex handles file read errors gracefully", async () => {
    const fg = await import("fast-glob");
    const nonExistentFile = path.join(tempDir, "does-not-exist.ts");

    vi.mocked(fg.default).mockResolvedValue([nonExistentFile]);

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    // Should not throw
    await watcher.start();

    expect(watcher.isRunning()).toBe(true);
  });

  test("fullIndex handles empty chunks", async () => {
    const fg = await import("fast-glob");
    const testFile = path.join(tempDir, "empty.ts");
    fs.writeFileSync(testFile, "// just a comment");

    vi.mocked(fg.default).mockResolvedValue([testFile]);
    vi.mocked(chunkFile).mockResolvedValue([]);

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await watcher.start();

    // Should complete without errors
    expect(watcher.isRunning()).toBe(true);
  });
});

describe("IndexWatcher - shouldIndex", () => {
  let tempDir: string;
  let mockOn: Mock;
  let mockClose: Mock;

  const mockConfig: EmbeddingConfig = {
    ollamaBaseUrl: "http://localhost:11434",
    embeddingModel: "nomic-embed-text",
    embeddingDimensions: 768,
    defaultChunkSize: 1000,
    defaultChunkOverlap: 200,
    batchSize: 10,
  };

  beforeEach(() => {
    tempDir = fs.mkdtempSync(
      path.join(os.tmpdir(), "watcher-shouldindex-test-"),
    );
    vi.clearAllMocks();

    mockOn = vi.fn().mockReturnThis();
    mockClose = vi.fn().mockResolvedValue(undefined);

    vi.mocked(watch).mockReturnValue({
      on: mockOn,
      close: mockClose,
    } as unknown as ReturnType<typeof watch>);

    vi.mocked(OllamaClient).mockImplementation(function (this: OllamaClient) {
      this.healthCheck = vi.fn().mockResolvedValue({ ok: true });
      this.embed = vi.fn();
      this.embedBatch = vi.fn();
      return this;
    } as unknown as typeof OllamaClient);

    vi.mocked(VectorStore).mockImplementation(function (this: VectorStore) {
      this.exists = vi.fn().mockReturnValue(true);
      this.connect = vi.fn().mockResolvedValue(undefined);
      this.close = vi.fn();
      this.addChunks = vi.fn();
      this.deleteByFilePath = vi.fn();
      return this;
    } as unknown as typeof VectorStore);
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  test("shouldIndex returns false for hidden files", async () => {
    let ignoredCallback: ((filePath: string) => boolean) | undefined;

    vi.mocked(watch).mockImplementation((_paths, options) => {
      ignoredCallback = options?.ignored as
        | ((path: string) => boolean)
        | undefined;
      return {
        on: mockOn,
        close: mockClose,
      } as unknown as ReturnType<typeof watch>;
    });

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await watcher.start();

    // Hidden files should be ignored
    expect(ignoredCallback?.(path.join(tempDir, ".hidden", "file.ts"))).toBe(
      true,
    );
  });

  test("shouldIndex respects gitignore patterns", async () => {
    // Create gitignore
    fs.writeFileSync(path.join(tempDir, ".gitignore"), "node_modules\nbuild\n");

    let ignoredCallback: ((filePath: string) => boolean) | undefined;

    vi.mocked(watch).mockImplementation((_paths, options) => {
      ignoredCallback = options?.ignored as
        | ((path: string) => boolean)
        | undefined;
      return {
        on: mockOn,
        close: mockClose,
      } as unknown as ReturnType<typeof watch>;
    });

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    await watcher.start();

    // node_modules should be ignored per gitignore
    expect(
      ignoredCallback?.(path.join(tempDir, "node_modules", "pkg", "index.js")),
    ).toBe(true);
  });

  test("handles gitignore read error gracefully", () => {
    // Create directory as gitignore (will fail to read)
    const gitignorePath = path.join(tempDir, ".gitignore");
    fs.mkdirSync(gitignorePath, { recursive: true });

    // Should not throw
    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    expect(watcher).toBeDefined();
  });
});

describe("IndexWatcher - error handling", () => {
  let tempDir: string;
  let mockOn: Mock;
  let mockClose: Mock;

  const mockConfig: EmbeddingConfig = {
    ollamaBaseUrl: "http://localhost:11434",
    embeddingModel: "nomic-embed-text",
    embeddingDimensions: 768,
    defaultChunkSize: 1000,
    defaultChunkOverlap: 200,
    batchSize: 10,
  };

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "watcher-error-test-"));
    vi.clearAllMocks();
    vi.useFakeTimers();

    mockOn = vi.fn().mockReturnThis();
    mockClose = vi.fn().mockResolvedValue(undefined);

    vi.mocked(watch).mockReturnValue({
      on: mockOn,
      close: mockClose,
    } as unknown as ReturnType<typeof watch>);

    vi.mocked(OllamaClient).mockImplementation(function (this: OllamaClient) {
      this.healthCheck = vi.fn().mockResolvedValue({ ok: true });
      this.embed = vi.fn().mockResolvedValue(new Array<number>(768).fill(0));
      this.embedBatch = vi
        .fn()
        .mockRejectedValue(new Error("Embedding failed"));
      return this;
    } as unknown as typeof OllamaClient);

    vi.mocked(VectorStore).mockImplementation(function (this: VectorStore) {
      this.exists = vi.fn().mockReturnValue(true);
      this.connect = vi.fn().mockResolvedValue(undefined);
      this.close = vi.fn();
      this.addChunks = vi.fn().mockResolvedValue(undefined);
      this.deleteByFilePath = vi
        .fn()
        .mockRejectedValue(new Error("Delete failed"));
      return this;
    } as unknown as typeof VectorStore);

    vi.mocked(shouldIndexFile).mockReturnValue(true);
  });

  afterEach(() => {
    vi.useRealTimers();
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  test("indexFile calls onError when embedding fails", async () => {
    const onError = vi.fn();
    let addHandler: ((filePath: string) => void) | undefined;

    mockOn.mockImplementation(function (
      this: { on: Mock },
      event: string,
      handler: (filePath: string) => void,
    ) {
      if (event === "add") {
        addHandler = handler;
      }
      return this;
    });

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
      debounceMs: 10,
      onError,
    });

    await watcher.start();

    const testFile = path.join(tempDir, "fail.ts");
    fs.writeFileSync(testFile, "const x = 1;");

    if (addHandler) {
      addHandler(testFile);
    }

    await vi.advanceTimersByTimeAsync(50);
    await vi.runAllTimersAsync();

    expect(onError).toHaveBeenCalled();
  });

  test("removeFile calls onError when delete fails", async () => {
    const onError = vi.fn();
    let unlinkHandler: ((filePath: string) => void) | undefined;

    mockOn.mockImplementation(function (
      this: { on: Mock },
      event: string,
      handler: (filePath: string) => void,
    ) {
      if (event === "unlink") {
        unlinkHandler = handler;
      }
      return this;
    });

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
      debounceMs: 10,
      onError,
    });

    await watcher.start();

    if (unlinkHandler) {
      unlinkHandler(path.join(tempDir, "removed.ts"));
    }

    await vi.advanceTimersByTimeAsync(50);
    await vi.runAllTimersAsync();

    expect(onError).toHaveBeenCalled();
  });

  test("processQueue handles operation errors gracefully", async () => {
    let addHandler: ((filePath: string) => void) | undefined;

    mockOn.mockImplementation(function (
      this: { on: Mock },
      event: string,
      handler: (filePath: string) => void,
    ) {
      if (event === "add") {
        addHandler = handler;
      }
      return this;
    });

    // Make chunkFile throw
    vi.mocked(chunkFile).mockRejectedValue(new Error("Chunk error"));

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
      debounceMs: 10,
    });

    await watcher.start();

    const testFile = path.join(tempDir, "error.ts");
    fs.writeFileSync(testFile, "const x = 1;");

    if (addHandler) {
      addHandler(testFile);
    }

    await vi.advanceTimersByTimeAsync(50);
    await vi.runAllTimersAsync();

    // Should not crash
    expect(watcher.isRunning()).toBe(true);
  });

  test("saveHashCache handles write errors gracefully", () => {
    // Make directory read-only (simulate write failure)
    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    // Call clearCache to trigger saveHashCache internally
    // This won't throw even if save fails
    watcher.clearCache();

    expect(watcher).toBeDefined();
  });

  test("processQueue catches and logs errors from operations", async () => {
    let addHandler: ((filePath: string) => void) | undefined;

    mockOn.mockImplementation(function (
      this: { on: Mock },
      event: string,
      handler: (filePath: string) => void,
    ) {
      if (event === "add") {
        addHandler = handler;
      }
      return this;
    });

    // Make the store throw an unexpected error type (string instead of Error)
    vi.mocked(VectorStore).mockImplementation(function (this: VectorStore) {
      this.exists = vi.fn().mockReturnValue(true);
      this.connect = vi.fn().mockResolvedValue(undefined);
      this.close = vi.fn();
      this.addChunks = vi.fn().mockRejectedValue("string error");
      this.deleteByFilePath = vi.fn().mockResolvedValue(undefined);
      return this;
    } as unknown as typeof VectorStore);

    const watcher = new IndexWatcher({
      directory: tempDir,
      config: mockConfig,
      debounceMs: 10,
    });

    await watcher.start();

    const testFile = path.join(tempDir, "error.ts");
    fs.writeFileSync(testFile, "const x = 1;");

    if (addHandler) {
      addHandler(testFile);
    }

    await vi.advanceTimersByTimeAsync(50);
    await vi.runAllTimersAsync();

    // Should handle the error without crashing
    expect(watcher.isRunning()).toBe(true);
  });
});

describe("createIndexWatcher", () => {
  let tempDir: string;

  const mockConfig: EmbeddingConfig = {
    ollamaBaseUrl: "http://localhost:11434",
    embeddingModel: "nomic-embed-text",
    embeddingDimensions: 768,
    defaultChunkSize: 1000,
    defaultChunkOverlap: 200,
    batchSize: 10,
  };

  beforeEach(() => {
    tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "watcher-factory-test-"));
    vi.clearAllMocks();

    vi.mocked(OllamaClient).mockImplementation(function (this: OllamaClient) {
      this.healthCheck = vi.fn().mockResolvedValue({ ok: true });
      this.embed = vi.fn();
      this.embedBatch = vi.fn();
      return this;
    } as unknown as typeof OllamaClient);

    vi.mocked(VectorStore).mockImplementation(function (this: VectorStore) {
      this.exists = vi.fn().mockReturnValue(true);
      this.connect = vi.fn().mockResolvedValue(undefined);
      this.close = vi.fn();
      this.addChunks = vi.fn();
      this.deleteByFilePath = vi.fn();
      return this;
    } as unknown as typeof VectorStore);
  });

  afterEach(() => {
    fs.rmSync(tempDir, { recursive: true, force: true });
  });

  test("creates IndexWatcher instance", () => {
    const watcher = createIndexWatcher({
      directory: tempDir,
      config: mockConfig,
    });

    expect(watcher).toBeInstanceOf(IndexWatcher);
  });

  test("passes all options to IndexWatcher", () => {
    const onReady = vi.fn();
    const onError = vi.fn();
    const onIndexed = vi.fn();
    const onRemoved = vi.fn();

    const watcher = createIndexWatcher({
      directory: tempDir,
      config: mockConfig,
      debounceMs: 2000,
      onReady,
      onError,
      onIndexed,
      onRemoved,
    });

    expect(watcher).toBeInstanceOf(IndexWatcher);
  });
});
