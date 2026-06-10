import type { QuestionAnswer, StartAnalysisRequest } from '@repo/shared'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:4000'

export async function startAnalysis(
  repoId: string,
  body?: StartAnalysisRequest,
): Promise<{ analysisId: string }> {
  const res = await fetch(`${API_URL}/analysis/${repoId}/start`, {
    method: 'POST',
    credentials: 'include',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}))
    throw new Error((errorBody as { message?: string }).message ?? 'Failed to start analysis')
  }
  return res.json()
}

export function createAnalysisStream(analysisId: string): EventSource {
  return new EventSource(`${API_URL}/analysis/${analysisId}/stream`, { withCredentials: true })
}

export interface AnalysisDetail {
  id: string
  status: string
  completedAt: string | null
  inputTokens: number | null
  outputTokens: number | null
  result: import('@repo/shared').AnalysisResult
}

export async function getLatestAnalysis(repoId: string): Promise<AnalysisDetail | null> {
  const res = await fetch(`${API_URL}/analysis/repo/${repoId}/latest`, {
    credentials: 'include',
  })
  if (res.status === 404) return null
  if (!res.ok) return null
  return res.json()
}

export async function getAnalysis(analysisId: string): Promise<AnalysisDetail | null> {
  const res = await fetch(`${API_URL}/analysis/${analysisId}`, {
    credentials: 'include',
  })
  if (res.status === 404) return null
  if (!res.ok) return null
  return res.json()
}

export async function getQuestions(analysisId: string): Promise<QuestionAnswer[]> {
  const res = await fetch(`${API_URL}/analysis/${analysisId}/questions`, {
    credentials: 'include',
  })
  if (!res.ok) return []
  return res.json()
}

export function createQuestionStream(analysisId: string, question: string): EventSource {
  const url = new URL(`${API_URL}/analysis/${analysisId}/ask`)
  const sse = new EventSource(url.toString(), { withCredentials: true })
  fetch(`${API_URL}/analysis/${analysisId}/ask`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  }).catch(() => {})
  return sse
}
