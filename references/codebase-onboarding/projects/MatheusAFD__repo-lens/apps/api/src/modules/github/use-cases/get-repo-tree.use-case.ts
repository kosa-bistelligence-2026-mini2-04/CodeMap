import { Injectable } from '@nestjs/common'
import type { Result } from '@repo/shared'
import type { GithubTreeItem } from '../github.types'

interface GetRepoTreeParams {
  owner: string
  repo: string
  token: string
}

@Injectable()
export class GetRepoTreeUseCase {
  async execute({ owner, repo, token }: GetRepoTreeParams): Promise<Result<GithubTreeItem[]>> {
    const res = await fetch(
      `https://api.github.com/repos/${owner}/${repo}/git/trees/HEAD?recursive=1`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28',
        },
      },
    )

    if (!res.ok) return [new Error(`GitHub tree error: ${res.status}`), null]

    const data = (await res.json()) as { tree: GithubTreeItem[]; truncated: boolean }
    return [null, data.tree]
  }
}
