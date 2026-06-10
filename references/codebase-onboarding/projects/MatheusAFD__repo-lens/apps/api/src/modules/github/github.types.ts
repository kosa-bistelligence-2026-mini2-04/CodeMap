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

export interface GithubTreeItem {
  path: string
  type: 'blob' | 'tree'
  size?: number
  sha: string
}
