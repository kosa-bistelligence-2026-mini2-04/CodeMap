import { Injectable } from '@nestjs/common'
import type { Result } from '@repo/shared'

interface GetFileContentParams {
  owner: string
  repo: string
  path: string
  token: string
}

@Injectable()
export class GetFileContentUseCase {
  async execute({ owner, repo, path, token }: GetFileContentParams): Promise<Result<string>> {
    const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents/${path}`, {
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
      },
    })

    if (!res.ok) return [new Error(`GitHub content error: ${res.status}`), null]

    const data = (await res.json()) as { content?: string; encoding?: string }
    if (!data.content || data.encoding !== 'base64') {
      return [new Error('Unexpected response format'), null]
    }

    const content = Buffer.from(data.content.replace(/\n/g, ''), 'base64').toString('utf-8')
    return [null, content]
  }
}
