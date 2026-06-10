export type StdClass = Record<PropertyKey, unknown>;

export interface OperationResult {
  success: boolean,
  message: string | null,
  name: string,
  error: unknown
}

export interface RunnerResult {
  success: boolean,
  message: string | null,
  results: OperationResult[]
}

export type VectorStoreEntry = {
  id: string,
  metadata: Record<string, string | number | boolean> | null,
  document: string | null
}

export type RagOptions = {
  refineUserPrompt: boolean,
  similaritySearchResults: number,
  model: null | string
}