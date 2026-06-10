import type { GithubRepo } from '@/modules/repos/domain/repo.domain'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:4000'

export async function fetchGithubRepos(): Promise<GithubRepo[]> {
  const res = await fetch(`${API_URL}/github/repos`, { credentials: 'include' })
  if (!res.ok) throw new Error('Failed to fetch GitHub repositories')
  return res.json()
}
