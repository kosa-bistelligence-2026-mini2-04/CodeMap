/**
 * Embedding types for Ollama + LanceDB integration
 */

/**
 * A chunk of code with metadata
 */
export interface CodeChunk {
  id: string;
  content: string;
  filePath: string;
  language: string;
  startLine: number;
  endLine: number;
  symbolName?: string;
  symbolType?: string;
}

/**
 * A chunk with its embedding vector
 */
export interface EmbeddedChunk extends CodeChunk {
  vector: number[];
}

/**
 * Search result from LanceDB
 */
export interface SearchResult {
  chunk: CodeChunk;
  score: number;
}

/**
 * Index status information
 */
export interface IndexStatus {
  directory: string;
  indexPath: string;
  exists: boolean;
  totalChunks: number;
  totalFiles: number;
  languages: Record<string, number>;
  lastUpdated?: Date;
}

/**
 * Embedding configuration
 */
export interface EmbeddingConfig {
  ollamaBaseUrl: string;
  embeddingModel: string;
  embeddingDimensions: number;
  defaultChunkSize: number;
  defaultChunkOverlap: number;
  batchSize: number;
}

/**
 * A symbol contained within a chunk
 */
export interface ChunkSymbol {
  /** Symbol name */
  name: string;
  /** Symbol type (function, class, variable, etc.) */
  type: string;
  /** Optional signature for functions/methods */
  signature?: string;
}

/**
 * A chunk enriched with semantic metadata
 */
export interface EnrichedChunk extends CodeChunk {
  /** The enriched content to be used for embedding */
  enrichedContent: string;
  /** Symbols contained within this chunk */
  containedSymbols: ChunkSymbol[];
  /** Whether enrichment was successfully applied */
  wasEnriched: boolean;
}
