import type { AnalysisResult } from '@repo/shared'
import type { analysis } from '../../config/database/schema'

export interface AnalysisDetail {
  id: string
  repositoryId: string
  userId: string
  previousAnalysisId: string | null
  status: string
  result: Partial<AnalysisResult> | null
  errorMessage: string | null
  inputTokens: number | null
  outputTokens: number | null
  createdAt: Date
  completedAt: Date | null
}

export function toAnalysisDetail(row: typeof analysis.$inferSelect): AnalysisDetail {
  let parsed: Partial<AnalysisResult> | null = null
  if (row.result) {
    try {
      parsed = JSON.parse(row.result) as Partial<AnalysisResult>
    } catch {
      parsed = null
    }
  }
  return {
    id: row.id,
    repositoryId: row.repositoryId,
    userId: row.userId,
    previousAnalysisId: row.previousAnalysisId,
    status: row.status,
    result: parsed,
    errorMessage: row.errorMessage,
    inputTokens: row.inputTokens,
    outputTokens: row.outputTokens,
    createdAt: row.createdAt,
    completedAt: row.completedAt,
  }
}
