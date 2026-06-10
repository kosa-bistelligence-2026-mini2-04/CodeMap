import Anthropic from '@anthropic-ai/sdk'
import { Injectable } from '@nestjs/common'
import type { CodeArea, Result } from '@repo/shared'
import { eq } from 'drizzle-orm'
import { db } from '../../config/database'
import { repository } from '../../config/database/schema'
import { GithubService, type GithubTreeItem } from '../github/github.service'
import { ReposService } from '../repos/repos.service'

const STALE_AFTER_MS = 7 * 24 * 60 * 60 * 1000

const FALLBACK_AREAS: CodeArea[] = [
  { id: 'core', label: 'Core', description: 'Top-level source files' },
  { id: 'config', label: 'Config', description: 'Build and tooling configuration' },
]

@Injectable()
export class ScopeMapperService {
  private readonly anthropic = new Anthropic({
    apiKey: process.env.ANTHROPIC_API_KEY,
  })

  constructor(
    private readonly githubService: GithubService,
    private readonly reposService: ReposService,
  ) {}

  async getCodeAreas(repoId: string, userId: string): Promise<Result<CodeArea[]>> {
    const [repoErr, repo] = await this.reposService.getRepo(repoId, userId)
    if (repoErr || !repo) return [repoErr ?? new Error('Repo not found'), null]

    if (repo.codeAreas && repo.codeAreasComputedAt) {
      const age = Date.now() - new Date(repo.codeAreasComputedAt).getTime()
      if (age < STALE_AFTER_MS) {
        try {
          const parsed = JSON.parse(repo.codeAreas) as CodeArea[]
          return [null, parsed]
        } catch {}
      }
    }

    const token = await this.githubService.getToken(userId)
    if (!token) return [null, FALLBACK_AREAS]

    const [treeErr, tree] = await this.githubService.getRepoTree(repo.owner, repo.name, token)
    if (treeErr || !tree) return [null, FALLBACK_AREAS]

    const isMockMode = process.env.ANTHROPIC_MOCK === 'true'
    const areas = isMockMode
      ? this.heuristicAreas(tree)
      : await this.detectWithLlm(tree).catch(() => this.heuristicAreas(tree))

    await db
      .update(repository)
      .set({
        codeAreas: JSON.stringify(areas),
        codeAreasComputedAt: new Date(),
      })
      .where(eq(repository.id, repoId))

    return [null, areas]
  }

  private async detectWithLlm(tree: GithubTreeItem[]): Promise<CodeArea[]> {
    const summary = this.summarizeTree(tree)

    const result = await this.anthropic.messages.create({
      model: 'claude-haiku-4-5-20251001',
      max_tokens: 512,
      system:
        'You map repository directory structures to high-level domain modules. Output strict JSON only.',
      messages: [
        {
          role: 'user',
          content: `Given this repository tree summary, list 4-8 high-level domain modules.\n\nOutput strict JSON in this shape and nothing else:\n{"areas":[{"id":"kebab-case","label":"Title Case","description":"<60 chars"}]}\n\nTree:\n${summary}`,
        },
      ],
    })

    const text = result.content
      .filter((block) => block.type === 'text')
      .map((block) => (block as { text: string }).text)
      .join('')

    const jsonMatch = text.match(/\{[\s\S]*\}/)
    if (!jsonMatch) throw new Error('No JSON in scope-mapper response')

    const parsed = JSON.parse(jsonMatch[0]) as { areas?: CodeArea[] }
    const areas = (parsed.areas ?? []).filter((a) => a.id && a.label).slice(0, 8)
    if (areas.length === 0) throw new Error('Empty areas')
    return areas
  }

  private heuristicAreas(tree: GithubTreeItem[]): CodeArea[] {
    const dirs = new Map<string, number>()
    for (const item of tree) {
      if (item.type !== 'blob') continue
      const segments = item.path.split('/')
      if (segments.length < 2) continue
      const top = segments[0]
      if (top.startsWith('.')) continue
      if (['node_modules', 'dist', 'build', 'coverage', '.next', '.turbo'].includes(top)) continue
      dirs.set(top, (dirs.get(top) ?? 0) + 1)
    }

    const sorted = [...dirs.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8)
    if (sorted.length === 0) return FALLBACK_AREAS

    return sorted.map(([dir]) => ({
      id: dir.replace(/[^a-z0-9-]/gi, '-').toLowerCase(),
      label: dir,
      description: `Top-level ${dir} directory`,
    }))
  }

  private summarizeTree(tree: GithubTreeItem[]): string {
    const blobs = tree.filter((t) => t.type === 'blob').slice(0, 400)
    return blobs.map((t) => t.path).join('\n')
  }
}
