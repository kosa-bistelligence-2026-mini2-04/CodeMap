import { Injectable, UnauthorizedException } from '@nestjs/common'
import type { Result } from '@repo/shared'
import type { GithubRepo } from '../github.types'
import { GetTokenUseCase } from './get-token.use-case'

interface ListUserReposParams {
  userId: string
}

@Injectable()
export class ListUserReposUseCase {
  constructor(private readonly getTokenUseCase: GetTokenUseCase) {}

  async execute({ userId }: ListUserReposParams): Promise<Result<GithubRepo[]>> {
    const token = await this.getTokenUseCase.execute({ userId })
    if (!token) return [new UnauthorizedException('GitHub account not connected'), null]

    const res = await fetch(
      'https://api.github.com/user/repos?per_page=100&sort=updated&affiliation=owner',
      {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: 'application/vnd.github+json',
          'X-GitHub-Api-Version': '2022-11-28',
        },
      },
    )

    if (!res.ok) return [new Error(`GitHub API error: ${res.status}`), null]

    const repos = (await res.json()) as GithubRepo[]
    return [null, repos]
  }
}
