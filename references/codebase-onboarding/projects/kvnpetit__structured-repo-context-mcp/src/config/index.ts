import type { EmbeddingConfig } from "@core/embeddings/types";
import type { ServerConfig } from "@types";

export const config: ServerConfig = {
  name: "src-mcp",
  fullName: "SRC (Structured Repo Context)",
  version: "1.0.3",
  description:
    "MCP server for codebase analysis with Treesitter (SCM queries), AST parsing, and embedding-based indexing",
};

const nodeEnv = process.env.NODE_ENV;
const logLevelEnv = process.env.LOG_LEVEL;

export const ENV = {
  isDev: nodeEnv === "development",
  isProd: nodeEnv === "production",
  logLevel: logLevelEnv ?? "info",
};

/**
 * Embedding configuration with environment variable overrides
 */
export const EMBEDDING_CONFIG: EmbeddingConfig = {
  ollamaBaseUrl: process.env.OLLAMA_BASE_URL ?? "http://localhost:11434",
  embeddingModel: process.env.EMBEDDING_MODEL ?? "nomic-embed-text",
  embeddingDimensions: Number(process.env.EMBEDDING_DIMENSIONS) || 768,
  defaultChunkSize: Number(process.env.CHUNK_SIZE) || 1000,
  defaultChunkOverlap: Number(process.env.CHUNK_OVERLAP) || 200,
  batchSize: Number(process.env.EMBEDDING_BATCH_SIZE) || 10,
};

/**
 * Enrichment configuration for cross-file context
 */
export const ENRICHMENT_CONFIG = {
  /** Include cross-file import definitions in enrichment */
  includeCrossFileContext: process.env.ENRICHMENT_CROSS_FILE !== "false",
  /** Maximum number of imports to resolve per file */
  maxImportsToResolve: Number(process.env.ENRICHMENT_MAX_IMPORTS) || 10,
  /** Maximum symbols per imported file to include */
  maxSymbolsPerImport:
    Number(process.env.ENRICHMENT_MAX_SYMBOLS_PER_IMPORT) || 5,
};
