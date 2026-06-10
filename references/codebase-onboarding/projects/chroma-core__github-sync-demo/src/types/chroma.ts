import { z } from "zod";

export const chromaDocumentMetadataSchema = z.object({
  chunk_strategy: z
    .union([z.enum(["tree_sitter", "lines"]), z.string()])
    .optional(),
  document_key: z.string(),
  document_key_sha256: z.string(),
  end_col: z.number().optional(),
  end_line: z.number().optional(),
  language: z.string().optional(),
  start_col: z.number().optional(),
  start_line: z.number().optional(),
  version_key: z.string(),
  version_key_sha256: z.string(),
});

export type ChromaDocumentMetadata = z.infer<
  typeof chromaDocumentMetadataSchema
>;

export interface QueryResult {
  id: string;
  distance: number;
  metadata: ChromaDocumentMetadata;
  document: string;
}

export interface CreateSourceResponse {
  source_id: string;
}

export interface CreateInvocationResponse {
  invocation_id: string;
}

export type InvocationStatus =
  | "pending"
  | "processing"
  | "cancelled"
  | "completed"
  | "failed";

export interface InvocationStatusResponse {
  id: string;
  status:
    | "pending"
    | "processing"
    | "cancelled"
    | { complete: { duration_ms: number; finished_at: string } }
    | { failed: { error: string } };
  created_at: string;
  metadata?: {
    collection_name?: string;
    database_name?: string;
  };
}

export interface NormalizedInvocationStatus {
  id: string;
  status: InvocationStatus;
  created_at: string;
  metadata?: {
    collection_name?: string;
    database_name?: string;
  };
}
