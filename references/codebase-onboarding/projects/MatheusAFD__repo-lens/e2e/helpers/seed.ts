import { randomUUID } from 'node:crypto'
import type { APIRequestContext } from '@playwright/test'
import { TEST_USER } from './fixtures'

const API_URL = 'http://localhost:4001'

export interface SeededRepository {
  id: string
  owner: string
  name: string
  fullName: string
}

async function getApiSessionCookie(request: APIRequestContext): Promise<string> {
  const response = await request.post(`${API_URL}/api/auth/sign-in/email`, {
    data: { email: TEST_USER.email, password: TEST_USER.password },
  })

  const setCookieHeader = response.headers()['set-cookie'] ?? ''
  const sessionCookie = setCookieHeader
    .split(',')
    .map((c) => c.trim())
    .find((c) => c.startsWith('better-auth.session_token='))

  if (!sessionCookie) {
    throw new Error('Failed to obtain session cookie for seed requests')
  }

  return sessionCookie.split(';')[0]
}

export async function seedRepository(
  request: APIRequestContext,
  overrides: Partial<{
    githubRepoId: string
    owner: string
    name: string
    fullName: string
    description: string
    language: string
    isPrivate: boolean
    htmlUrl: string
  }> = {},
): Promise<SeededRepository> {
  const sessionCookie = await getApiSessionCookie(request)

  const payload = {
    githubRepoId: overrides.githubRepoId ?? randomUUID(),
    owner: overrides.owner ?? 'test-owner',
    name: overrides.name ?? 'test-repo',
    fullName: overrides.fullName ?? 'test-owner/test-repo',
    description: overrides.description ?? 'A test repository',
    language: overrides.language ?? 'TypeScript',
    isPrivate: overrides.isPrivate ?? false,
    htmlUrl: overrides.htmlUrl ?? 'https://github.com/test-owner/test-repo',
  }

  const response = await request.post(`${API_URL}/repos`, {
    data: payload,
    headers: { Cookie: sessionCookie },
  })

  return response.json()
}

export const GITHUB_REPOS_FIXTURE = [
  {
    id: 111111,
    name: 'my-awesome-repo',
    full_name: 'test-owner/my-awesome-repo',
    owner: { login: 'test-owner', avatar_url: 'https://avatars.githubusercontent.com/u/1?v=4' },
    description: 'An awesome test repository',
    language: 'TypeScript',
    private: false,
    html_url: 'https://github.com/test-owner/my-awesome-repo',
    updated_at: '2024-01-01T00:00:00Z',
    stargazers_count: 42,
  },
  {
    id: 222222,
    name: 'another-repo',
    full_name: 'test-owner/another-repo',
    owner: { login: 'test-owner', avatar_url: 'https://avatars.githubusercontent.com/u/1?v=4' },
    description: null,
    language: 'Python',
    private: false,
    html_url: 'https://github.com/test-owner/another-repo',
    updated_at: '2024-02-01T00:00:00Z',
    stargazers_count: 7,
  },
]
