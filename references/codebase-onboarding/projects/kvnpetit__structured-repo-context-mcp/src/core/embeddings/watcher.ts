/**
 * File watcher for automatic index updates
 *
 * Features:
 * - SHA-256 hash comparison to detect real content changes
 * - Debounce (5s default) to handle rapid changes
 * - Persistent hash cache to avoid unnecessary re-indexing
 * - fast-glob for efficient file scanning
 */

import * as fs from "node:fs";
import * as path from "node:path";
import * as crypto from "node:crypto";
import { watch, type FSWatcher } from "chokidar";
import fg from "fast-glob";
import ignore, { type Ignore } from "ignore";
import type { EmbeddingConfig } from "@core/embeddings/types";
import { OllamaClient } from "@core/embeddings/client";
import { VectorStore } from "@core/embeddings/store";
import {
  chunkFile,
  shouldIndexFile,
  SUPPORTED_EXTENSIONS,
} from "@core/embeddings/chunker";
import { enrichChunksFromFile } from "@core/embeddings/enricher";
import { logger } from "@utils";

/** Default debounce delay in milliseconds */
const DEFAULT_DEBOUNCE_MS = 5000;

/** Cache file name for storing hashes */
const HASH_CACHE_FILE = ".src-index-hashes.json";

export interface WatcherOptions {
  directory: string;
  config: EmbeddingConfig;
  /** Debounce delay in ms (default: 5000) */
  debounceMs?: number;
  onReady?: () => void;
  onError?: (error: Error) => void;
  onIndexed?: (filePath: string) => void;
  onRemoved?: (filePath: string) => void;
}

type HashCache = Record<string, string>;

interface PendingChange {
  type: "add" | "change" | "unlink";
  filePath: string;
  timer: ReturnType<typeof setTimeout>;
}

export class IndexWatcher {
  private readonly directory: string;
  private readonly config: EmbeddingConfig;
  private readonly debounceMs: number;
  private readonly ollamaClient: OllamaClient;
  private readonly vectorStore: VectorStore;
  private watcher: FSWatcher | null = null;
  private ig: Ignore;
  private isProcessing = false;
  private hashCache: HashCache = {};
  private pendingChanges = new Map<string, PendingChange>();
  private operationQueue: (() => Promise<void>)[] = [];

  private readonly onReady?: () => void;
  private readonly onError?: (error: Error) => void;
  private readonly onIndexed?: (filePath: string) => void;
  private readonly onRemoved?: (filePath: string) => void;

  constructor(options: WatcherOptions) {
    this.directory = path.resolve(options.directory);
    this.config = options.config;
    this.debounceMs = options.debounceMs ?? DEFAULT_DEBOUNCE_MS;
    this.ollamaClient = new OllamaClient(options.config);
    this.vectorStore = new VectorStore(this.directory, options.config);
    this.ig = this.createIgnoreFilter();

    this.onReady = options.onReady;
    this.onError = options.onError;
    this.onIndexed = options.onIndexed;
    this.onRemoved = options.onRemoved;

    this.loadHashCache();
  }

  /**
   * Compute SHA-256 hash of content
   */
  private computeHash(content: string): string {
    return crypto.createHash("sha256").update(content, "utf8").digest("hex");
  }

  /**
   * Get hash cache file path
   */
  private getHashCachePath(): string {
    return path.join(this.directory, ".src-index", HASH_CACHE_FILE);
  }

  /**
   * Load hash cache from disk
   */
  private loadHashCache(): void {
    const cachePath = this.getHashCachePath();

    if (fs.existsSync(cachePath)) {
      try {
        const content = fs.readFileSync(cachePath, "utf-8");
        this.hashCache = JSON.parse(content) as HashCache;
        logger.debug(
          `Loaded ${String(Object.keys(this.hashCache).length)} cached hashes`,
        );
      } catch {
        this.hashCache = {};
      }
    }
  }

  /**
   * Save hash cache to disk
   */
  private saveHashCache(): void {
    const cachePath = this.getHashCachePath();
    const cacheDir = path.dirname(cachePath);

    try {
      if (!fs.existsSync(cacheDir)) {
        fs.mkdirSync(cacheDir, { recursive: true });
      }
      fs.writeFileSync(cachePath, JSON.stringify(this.hashCache, null, 2));
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      logger.debug(`Failed to save hash cache: ${error.message}`);
    }
  }

  /**
   * Check if file content has changed by comparing hashes
   */
  private hasContentChanged(filePath: string, content: string): boolean {
    const newHash = this.computeHash(content);
    const oldHash = this.hashCache[filePath];

    if (oldHash === newHash) {
      return false;
    }

    this.hashCache[filePath] = newHash;
    return true;
  }

  /**
   * Remove file from hash cache
   */
  private removeFromHashCache(filePath: string): void {
    const { [filePath]: _, ...rest } = this.hashCache;
    this.hashCache = rest;
  }

  /**
   * Create ignore filter from .gitignore
   */
  private createIgnoreFilter(): Ignore {
    const ig = ignore();
    const gitignorePath = path.join(this.directory, ".gitignore");

    if (fs.existsSync(gitignorePath)) {
      try {
        const content = fs.readFileSync(gitignorePath, "utf-8");
        ig.add(content);
      } catch {
        // Ignore read errors
      }
    }

    return ig;
  }

  /**
   * Check if a file should be indexed
   */
  private shouldIndex(filePath: string): boolean {
    const relativePath = path
      .relative(this.directory, filePath)
      .replace(/\\/g, "/");

    // Skip hidden files/folders
    if (relativePath.split("/").some((part) => part.startsWith("."))) {
      return false;
    }

    // Skip gitignore patterns
    if (this.ig.ignores(relativePath)) {
      return false;
    }

    return shouldIndexFile(filePath);
  }

  /**
   * Schedule a file change with debouncing
   */
  private scheduleChange(
    type: "add" | "change" | "unlink",
    filePath: string,
  ): void {
    const existing = this.pendingChanges.get(filePath);
    if (existing) {
      clearTimeout(existing.timer);
    }

    const timer = setTimeout(() => {
      this.pendingChanges.delete(filePath);
      this.queueOperation(async () => this.processChange(type, filePath));
    }, this.debounceMs);

    this.pendingChanges.set(filePath, { type, filePath, timer });

    logger.debug(
      `Scheduled ${type}: ${path.basename(filePath)} (${String(this.debounceMs)}ms)`,
    );
  }

  /**
   * Process a file change after debounce
   */
  private async processChange(
    type: "add" | "change" | "unlink",
    filePath: string,
  ): Promise<void> {
    if (type === "unlink") {
      await this.removeFile(filePath);
    } else {
      await this.indexFile(filePath);
    }
  }

  /**
   * Index a single file
   */
  private async indexFile(filePath: string): Promise<void> {
    if (!this.shouldIndex(filePath)) {
      return;
    }

    try {
      const content = fs.readFileSync(filePath, "utf-8");

      // Skip if content unchanged
      if (!this.hasContentChanged(filePath, content)) {
        logger.debug(`Skipped (unchanged): ${path.basename(filePath)}`);
        return;
      }

      const chunks = await chunkFile(filePath, content, this.config);

      if (chunks.length === 0) {
        return;
      }

      // Enrich chunks with semantic metadata
      const enrichedChunks = await enrichChunksFromFile(chunks, content);

      // Use enrichedContent for embedding
      const texts = enrichedChunks.map((c) => c.enrichedContent);
      const embeddings = await this.ollamaClient.embedBatch(texts);

      // Store original chunk data (without enrichedContent)
      const embeddedChunks = enrichedChunks.map((chunk, i) => ({
        id: chunk.id,
        content: chunk.content,
        filePath: chunk.filePath,
        language: chunk.language,
        startLine: chunk.startLine,
        endLine: chunk.endLine,
        symbolName: chunk.symbolName,
        symbolType: chunk.symbolType,
        vector: embeddings[i] ?? [],
      }));

      await this.vectorStore.deleteByFilePath(filePath);
      await this.vectorStore.addChunks(embeddedChunks);

      this.saveHashCache();

      logger.debug(`Indexed: ${path.relative(this.directory, filePath)}`);
      this.onIndexed?.(filePath);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      logger.error(`Failed to index ${filePath}: ${error.message}`);
      this.onError?.(error);
    }
  }

  /**
   * Remove a file from the index
   */
  private async removeFile(filePath: string): Promise<void> {
    try {
      await this.vectorStore.deleteByFilePath(filePath);
      this.removeFromHashCache(filePath);
      this.saveHashCache();

      logger.debug(`Removed: ${path.relative(this.directory, filePath)}`);
      this.onRemoved?.(filePath);
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));
      logger.error(`Failed to remove ${filePath}: ${error.message}`);
      this.onError?.(error);
    }
  }

  /**
   * Queue an operation to prevent concurrent modifications
   */
  private queueOperation(operation: () => Promise<void>): void {
    this.operationQueue.push(operation);
    void this.processQueue();
  }

  /**
   * Process queued operations sequentially
   */
  private async processQueue(): Promise<void> {
    if (this.isProcessing) {
      return;
    }

    this.isProcessing = true;

    while (this.operationQueue.length > 0) {
      const operation = this.operationQueue.shift();
      if (operation) {
        try {
          await operation();
        } catch (err) {
          const error = err instanceof Error ? err : new Error(String(err));
          logger.error(`Operation failed: ${error.message}`);
        }
      }
    }

    this.isProcessing = false;
  }

  /**
   * Collect files using fast-glob
   */
  private async collectFilesWithGlob(): Promise<string[]> {
    const extensions = SUPPORTED_EXTENSIONS.map((ext) => ext.slice(1));
    const pattern = `**/*.{${extensions.join(",")}}`;

    const files = await fg(pattern, {
      cwd: this.directory,
      absolute: true,
      ignore: ["**/.*", "**/.*/**"],
      dot: false,
      onlyFiles: true,
      followSymbolicLinks: false,
    });

    // Filter by gitignore
    return files.filter((file) => {
      const relativePath = path
        .relative(this.directory, file)
        .replace(/\\/g, "/");
      return !this.ig.ignores(relativePath);
    });
  }

  /**
   * Perform full initial indexing
   */
  private async fullIndex(): Promise<void> {
    logger.info("Starting full index...");

    const files = await this.collectFilesWithGlob();
    let indexed = 0;
    let skipped = 0;

    for (const filePath of files) {
      try {
        const content = fs.readFileSync(filePath, "utf-8");

        if (!this.hasContentChanged(filePath, content)) {
          skipped++;
          continue;
        }

        const chunks = await chunkFile(filePath, content, this.config);

        if (chunks.length === 0) {
          continue;
        }

        // Enrich chunks with semantic metadata
        const enrichedChunks = await enrichChunksFromFile(chunks, content);

        // Use enrichedContent for embedding
        const texts = enrichedChunks.map((c) => c.enrichedContent);
        const embeddings = await this.ollamaClient.embedBatch(texts);

        // Store original chunk data (without enrichedContent)
        const embeddedChunks = enrichedChunks.map((chunk, i) => ({
          id: chunk.id,
          content: chunk.content,
          filePath: chunk.filePath,
          language: chunk.language,
          startLine: chunk.startLine,
          endLine: chunk.endLine,
          symbolName: chunk.symbolName,
          symbolType: chunk.symbolType,
          vector: embeddings[i] ?? [],
        }));

        await this.vectorStore.addChunks(embeddedChunks);
        indexed++;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        logger.debug(`Error indexing ${filePath}: ${error.message}`);
      }
    }

    this.saveHashCache();

    logger.info(
      `Full index: ${String(indexed)} indexed, ${String(skipped)} skipped`,
    );
  }

  /**
   * Start watching for file changes
   */
  async start(): Promise<void> {
    const health = await this.ollamaClient.healthCheck();
    if (!health.ok) {
      throw new Error(health.error ?? "Ollama is not available");
    }

    // Check if index exists BEFORE connect (connect creates the directory)
    const needsFullIndex = !this.vectorStore.exists();

    await this.vectorStore.connect();

    if (needsFullIndex) {
      await this.fullIndex();
    }

    this.watcher = watch(this.directory, {
      ignored: (filePath: string) => {
        const relativePath = path
          .relative(this.directory, filePath)
          .replace(/\\/g, "/");
        // Skip empty paths or root directory
        if (!relativePath) {
          return false;
        }
        // Skip hidden files/folders
        if (relativePath.split("/").some((part) => part.startsWith("."))) {
          return true;
        }
        return this.ig.ignores(relativePath);
      },
      persistent: true,
      ignoreInitial: true,
      awaitWriteFinish: {
        stabilityThreshold: 500,
        pollInterval: 100,
      },
    });

    this.watcher.on("add", (filePath: string) => {
      if (shouldIndexFile(filePath)) {
        this.scheduleChange("add", filePath);
      }
    });

    this.watcher.on("change", (filePath: string) => {
      if (shouldIndexFile(filePath)) {
        this.scheduleChange("change", filePath);
      }
    });

    this.watcher.on("unlink", (filePath: string) => {
      if (shouldIndexFile(filePath)) {
        this.scheduleChange("unlink", filePath);
      }
    });

    this.watcher.on("ready", () => {
      logger.info(
        `Watching: ${this.directory} (${String(this.debounceMs)}ms debounce)`,
      );
      this.onReady?.();
    });

    this.watcher.on("error", (err: unknown) => {
      const error = err instanceof Error ? err : new Error(String(err));
      logger.error(`Watcher error: ${error.message}`);
      this.onError?.(error);
    });
  }

  /**
   * Stop watching and cleanup
   */
  async stop(): Promise<void> {
    for (const pending of this.pendingChanges.values()) {
      clearTimeout(pending.timer);
    }
    this.pendingChanges.clear();

    this.saveHashCache();

    if (this.watcher) {
      await this.watcher.close();
      this.watcher = null;
    }
    this.vectorStore.close();
    logger.info("Watcher stopped");
  }

  /**
   * Check if watcher is running
   */
  isRunning(): boolean {
    return this.watcher !== null;
  }

  /**
   * Clear the hash cache
   */
  clearCache(): void {
    this.hashCache = {};
    const cachePath = this.getHashCachePath();
    if (fs.existsSync(cachePath)) {
      fs.unlinkSync(cachePath);
    }
    logger.info("Hash cache cleared");
  }

  /**
   * Get cache statistics
   */
  getCacheStats(): { cachedFiles: number; cacheSize: number } {
    return {
      cachedFiles: Object.keys(this.hashCache).length,
      cacheSize: JSON.stringify(this.hashCache).length,
    };
  }
}

/**
 * Create a new index watcher
 */
export function createIndexWatcher(options: WatcherOptions): IndexWatcher {
  return new IndexWatcher(options);
}
