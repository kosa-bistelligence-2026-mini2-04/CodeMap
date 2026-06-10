export interface Repository {
  id: string
  userId: string
  githubRepoId: string
  owner: string
  name: string
  fullName: string
  description: string | null
  language: string | null
  isPrivate: boolean
  htmlUrl: string
  createdAt: string
  updatedAt: string
  hasAnalysis: boolean
  lastAnalyzedAt: string | null
}

export interface GithubRepo {
  id: number
  name: string
  full_name: string
  owner: { login: string; avatar_url: string }
  description: string | null
  language: string | null
  private: boolean
  html_url: string
  updated_at: string
  stargazers_count: number
}

export interface AnalysisSummary {
  id: string
  status: string
  createdAt: string
  completedAt: string | null
  inputTokens: number | null
  outputTokens: number | null
  securityGrade: string | null
}
