/**
 * LanceDB vector store for code embeddings
 *
 * Supports:
 * - Vector similarity search (embeddings)
 * - Full-text search (BM25)
 * - Hybrid search with RRF (Reciprocal Rank Fusion)
 */

import * as lancedb from "@lancedb/lancedb";
import * as fs from "node:fs";
import * as path from "node:path";
import type {
  EmbeddedChunk,
  EmbeddingConfig,
  IndexStatus,
  SearchResult,
} from "@core/embeddings/types";
import { logger } from "@utils";

const TABLE_NAME = "code_chunks";
const INDEX_DIR_NAME = ".src-index";

/**
 * Search mode for queries
 */
export type SearchMode = "vector" | "fts" | "hybrid";

/**
 * Options for hybrid search
 */
export interface HybridSearchOptions {
  /** Search mode: vector only, fts only, or hybrid (default: hybrid) */
  mode?: SearchMode;
  /** Weight for vector search in hybrid mode (0-1, default: 0.5) */
  vectorWeight?: number;
  /** RRF constant k for rank fusion (default: 60) */
  rrfK?: number;
}

/**
 * Reciprocal Rank Fusion (RRF) to combine ranked lists
 *
 * RRF score = sum(1 / (k + rank_i)) for each list
 * where k is a constant (typically 60) and rank_i is the 1-based rank in list i
 */
function rrfFusion(
  vectorResults: SearchResult[],
  ftsResults: SearchResult[],
  k = 60,
): SearchResult[] {
  const scores = new Map<string, { score: number; result: SearchResult }>();

  // Add vector results with RRF scoring
  vectorResults.forEach((result, index) => {
    const rank = index + 1;
    const rrfScore = 1 / (k + rank);
    const existing = scores.get(result.chunk.id);
    if (existing) {
      existing.score += rrfScore;
    } else {
      scores.set(result.chunk.id, { score: rrfScore, result });
    }
  });

  // Add FTS results with RRF scoring
  ftsResults.forEach((result, index) => {
    const rank = index + 1;
    const rrfScore = 1 / (k + rank);
    const existing = scores.get(result.chunk.id);
    if (existing) {
      existing.score += rrfScore;
    } else {
      scores.set(result.chunk.id, { score: rrfScore, result });
    }
  });

  // Sort by combined RRF score (higher is better)
  const combined = Array.from(scores.values())
    .sort((a, b) => b.score - a.score)
    .map(({ score, result }) => ({
      ...result,
      score, // Replace distance with RRF score
    }));

  return combined;
}

/**
 * Type for LanceDB row results
 */
interface LanceDBRow {
  id: string;
  content: string;
  filePath: string;
  language: string;
  startLine: number;
  endLine: number;
  symbolName: string;
  symbolType: string;
  vector: number[];
  _distance?: number;
}

/**
 * LanceDB vector store wrapper
 */
export class VectorStore {
  private db: lancedb.Connection | null = null;
  private table: lancedb.Table | null = null;
  private readonly indexPath: string;
  private ftsIndexCreated = false;

  constructor(
    directory: string,
    _config: Pick<EmbeddingConfig, "embeddingDimensions">,
  ) {
    this.indexPath = path.join(directory, INDEX_DIR_NAME);
  }

  /**
   * Initialize the database connection
   */
  async connect(): Promise<void> {
    this.db = await lancedb.connect(this.indexPath);

    const tableNames = await this.db.tableNames();
    if (tableNames.includes(TABLE_NAME)) {
      this.table = await this.db.openTable(TABLE_NAME);
    }
  }

  /**
   * Close the database connection
   */
  close(): void {
    this.db = null;
    this.table = null;
  }

  /**
   * Check if the index exists
   */
  exists(): boolean {
    return fs.existsSync(this.indexPath);
  }

  /**
   * Add embedded chunks to the store
   */
  async addChunks(chunks: EmbeddedChunk[]): Promise<void> {
    if (!this.db) {
      throw new Error("Database not connected. Call connect() first.");
    }

    const records = chunks.map((chunk) => ({
      id: chunk.id,
      content: chunk.content,
      filePath: chunk.filePath,
      language: chunk.language,
      startLine: chunk.startLine,
      endLine: chunk.endLine,
      symbolName: chunk.symbolName ?? "",
      symbolType: chunk.symbolType ?? "",
      vector: chunk.vector,
    }));

    if (!this.table) {
      this.table = await this.db.createTable(TABLE_NAME, records);
    } else {
      await this.table.add(records);
    }
  }

  /**
   * Create FTS (Full-Text Search) index on content column
   * This enables BM25-based text search
   */
  async createFtsIndex(): Promise<void> {
    if (!this.table || this.ftsIndexCreated) {
      return;
    }

    try {
      await this.table.createIndex("content", {
        config: lancedb.Index.fts(),
      });
      this.ftsIndexCreated = true;
      logger.debug("FTS index created on content column");
    } catch (error) {
      // Index may already exist
      if (error instanceof Error && error.message.includes("already exists")) {
        this.ftsIndexCreated = true;
        logger.debug("FTS index already exists");
      } else {
        logger.warn(
          `Failed to create FTS index: ${error instanceof Error ? error.message : String(error)}`,
        );
      }
    }
  }

  /**
   * Search for similar chunks using vector similarity
   */
  async search(queryVector: number[], limit = 10): Promise<SearchResult[]> {
    if (!this.table) {
      return [];
    }

    const results = (await this.table
      .vectorSearch(queryVector)
      .limit(limit)
      .toArray()) as LanceDBRow[];

    return results.map((row) => ({
      chunk: {
        id: row.id,
        content: row.content,
        filePath: row.filePath,
        language: row.language,
        startLine: row.startLine,
        endLine: row.endLine,
        symbolName: row.symbolName || undefined,
        symbolType: row.symbolType || undefined,
      },
      score: row._distance ?? 0,
    }));
  }

  /**
   * Full-text search using BM25
   */
  async searchFts(queryText: string, limit = 10): Promise<SearchResult[]> {
    if (!this.table) {
      return [];
    }

    // Ensure FTS index exists
    await this.createFtsIndex();

    try {
      const results = (await this.table
        .query()
        .nearestToText(queryText)
        .limit(limit)
        .toArray()) as LanceDBRow[];

      return results.map((row, index) => ({
        chunk: {
          id: row.id,
          content: row.content,
          filePath: row.filePath,
          language: row.language,
          startLine: row.startLine,
          endLine: row.endLine,
          symbolName: row.symbolName || undefined,
          symbolType: row.symbolType || undefined,
        },
        // FTS doesn't return distance, use rank-based score
        score: 1 / (index + 1),
      }));
    } catch (error) {
      logger.warn(
        `FTS search failed, falling back to empty results: ${error instanceof Error ? error.message : String(error)}`,
      );
      return [];
    }
  }

  /**
   * Hybrid search combining vector similarity and full-text search
   * Uses Reciprocal Rank Fusion (RRF) to combine results
   */
  async searchHybrid(
    queryVector: number[],
    queryText: string,
    limit = 10,
    options: HybridSearchOptions = {},
  ): Promise<SearchResult[]> {
    const { mode = "hybrid", rrfK = 60 } = options;

    if (!this.table) {
      return [];
    }

    // Vector-only search
    if (mode === "vector") {
      return this.search(queryVector, limit);
    }

    // FTS-only search
    if (mode === "fts") {
      return this.searchFts(queryText, limit);
    }

    // Hybrid search: run both searches in parallel
    const [vectorResults, ftsResults] = await Promise.all([
      this.search(queryVector, limit * 2), // Get more results for fusion
      this.searchFts(queryText, limit * 2),
    ]);

    // Fuse results using RRF
    const fusedResults = rrfFusion(vectorResults, ftsResults, rrfK);

    // Return top N results
    return fusedResults.slice(0, limit);
  }

  /**
   * Delete chunks by file path
   */
  async deleteByFilePath(filePath: string): Promise<void> {
    if (!this.table) {
      return;
    }

    await this.table.delete(`"filePath" = '${filePath.replace(/'/g, "''")}'`);
  }

  /**
   * Clear all data from the store
   */
  async clear(): Promise<void> {
    if (this.db && this.table) {
      await this.db.dropTable(TABLE_NAME);
      this.table = null;
    }
  }

  /**
   * Get index status
   */
  async getStatus(directory: string): Promise<IndexStatus> {
    const status: IndexStatus = {
      directory,
      indexPath: this.indexPath,
      exists: this.exists(),
      totalChunks: 0,
      totalFiles: 0,
      languages: {},
    };

    if (!this.table) {
      return status;
    }

    const allRows = (await this.table.query().toArray()) as LanceDBRow[];

    status.totalChunks = allRows.length;

    const uniqueFiles = new Set<string>();
    const languageCounts: Record<string, number> = {};

    for (const row of allRows) {
      uniqueFiles.add(row.filePath);
      const lang = row.language;
      languageCounts[lang] = (languageCounts[lang] ?? 0) + 1;
    }

    status.totalFiles = uniqueFiles.size;
    status.languages = languageCounts;

    return status;
  }

  /**
   * Get all indexed file paths
   */
  async getIndexedFiles(): Promise<string[]> {
    if (!this.table) {
      return [];
    }

    const rows = (await this.table
      .query()
      .select(["filePath"])
      .toArray()) as Pick<LanceDBRow, "filePath">[];
    const uniqueFiles = new Set<string>();

    for (const row of rows) {
      uniqueFiles.add(row.filePath);
    }

    return Array.from(uniqueFiles);
  }
}

/**
 * Create a vector store for a directory
 */
export function createVectorStore(
  directory: string,
  config: Pick<EmbeddingConfig, "embeddingDimensions">,
): VectorStore {
  return new VectorStore(directory, config);
}

/**
 * Get the index path for a directory
 */
export function getIndexPath(directory: string): string {
  return path.join(directory, INDEX_DIR_NAME);
}
