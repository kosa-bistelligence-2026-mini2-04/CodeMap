import type { AnalysisSummary, Repository } from '@/modules/repos/domain/repo.domain'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:4000'

const headers = { 'Content-Type': 'application/json' }
const opts = { credentials: 'include' as const }

export async function fetchRepos(): Promise<Repository[]> {
  const res = await fetch(`${API_URL}/repos`, { ...opts })
  if (!res.ok) throw new Error('Failed to fetch repositories')
  return res.json()
}

export async function upsertRepo(dto: {
  githubRepoId: string
  owner: string
  name: string
  fullName: string
  description?: string | null
  language?: string | null
  isPrivate: boolean
  htmlUrl: string
}): Promise<Repository> {
  const res = await fetch(`${API_URL}/repos`, {
    method: 'POST',
    headers,
    ...opts,
    body: JSON.stringify(dto),
  })
  if (!res.ok) throw new Error('Failed to add repository')
  return res.json()
}

export async function fetchRepo(id: string): Promise<Repository> {
  const res = await fetch(`${API_URL}/repos/${id}`, { ...opts })
  if (!res.ok) throw new Error('Failed to fetch repository')
  return res.json()
}

export async function fetchRepoAnalyses(id: string): Promise<AnalysisSummary[]> {
  const res = await fetch(`${API_URL}/repos/${id}/analyses`, { ...opts })
  if (!res.ok) throw new Error('Failed to fetch analyses')
  return res.json()
}
