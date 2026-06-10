import Anthropic from '@anthropic-ai/sdk'
import { Injectable } from '@nestjs/common'
import type { AnalysisResult, AnalysisSectionType, SseEvent } from '@repo/shared'
import { eq } from 'drizzle-orm'
import { parseSections } from '../../../common/parsing/section-parser'
import { db } from '../../../config/database'
import { analysis, type repository } from '../../../config/database/schema'
import { GithubService } from '../../github/github.service'
import { ContextBuilderService } from '../context-builder.service'
import { PromptBuilderService } from '../prompt-builder.service'
import { AnalysisStreamPool } from './analysis-stream-pool'

interface RunAnalysisParams {
  analysisId: string
  repo: typeof repository.$inferSelect
  userId: string
  sections: AnalysisSectionType[]
  customContext?: string
  previousAnalysis?: Partial<AnalysisResult>
}

@Injectable()
export class RunAnalysisUseCase {
  private readonly anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })

  constructor(
    private readonly githubService: GithubService,
    private readonly contextBuilder: ContextBuilderService,
    private readonly promptBuilder: PromptBuilderService,
    private readonly pool: AnalysisStreamPool,
  ) {}

  async execute(params: RunAnalysisParams): Promise<void> {
    const { analysisId, repo, userId, sections, customContext, previousAnalysis } = params

    this.pool.initResult(analysisId)

    const isMockMode = process.env.ANTHROPIC_MOCK === 'true'

    let files: Awaited<ReturnType<ContextBuilderService['buildContext']>> = []

    if (!isMockMode) {
      this.emit(analysisId, { type: 'progress', message: 'Fetching repository structure…' })

      const token = await this.githubService.getToken(userId)
      if (!token) throw new Error('GitHub account not connected')

      const [treeErr, tree] = await this.githubService.getRepoTree(repo.owner, repo.name, token)
      if (treeErr || !tree) throw treeErr ?? new Error('Could not fetch repository tree')

      this.emit(analysisId, { type: 'progress', message: 'Selecting relevant files…' })

      files = await this.contextBuilder.buildContext(
        repo.owner,
        repo.name,
        tree,
        this.githubService,
        token,
      )
    }

    this.emit(analysisId, { type: 'progress', message: 'Analyzing with Claude AI…' })

    const systemPrompt = this.promptBuilder.buildSystemPrompt(sections, !!previousAnalysis)
    const userPrompt = this.promptBuilder.buildUserPrompt(
      {
        owner: repo.owner,
        name: repo.name,
        description: repo.description,
        language: repo.language,
      },
      files,
      customContext,
      previousAnalysis,
    )

    let buffer = ''
    let inputTokens = 0
    let outputTokens = 0
    const stream = isMockMode
      ? // biome-ignore lint/suspicious/noExplicitAny: dynamic require used only in test mode
        (require('../__mocks__/anthropic-stream.fixture') as any).createMockAnthropicStream(
          sections,
        )
      : this.anthropic.messages.stream({
          model: 'claude-sonnet-4-6',
          max_tokens: 8192,
          system: systemPrompt,
          messages: [{ role: 'user', content: userPrompt }],
        })

    for await (const chunk of stream) {
      if (chunk.type === 'content_block_delta' && chunk.delta.type === 'text_delta') {
        buffer += chunk.delta.text
        const { sections: parsed, remaining } = parseSections(buffer)
        for (const section of parsed) {
          this.pool.setSection(analysisId, section.name, section.data)
          this.emit(analysisId, {
            type: 'section',
            name: section.name as AnalysisSectionType,
            data: section.data,
          })
        }
        buffer = remaining
      }
      if (chunk.type === 'message_delta' && chunk.usage) {
        outputTokens = chunk.usage.output_tokens
      }
      if (chunk.type === 'message_start' && chunk.message.usage) {
        inputTokens = chunk.message.usage.input_tokens
      }
    }

    const resultData = this.pool.getResult(analysisId)
    await db
      .update(analysis)
      .set({
        status: 'completed',
        completedAt: new Date(),
        inputTokens,
        outputTokens,
        result: JSON.stringify(resultData),
      })
      .where(eq(analysis.id, analysisId))

    this.emit(analysisId, { type: 'done', analysisId })
    this.pool.complete(analysisId)
    this.pool.clearResult(analysisId)
  }

  private emit(analysisId: string, event: SseEvent): void {
    this.pool.emit(analysisId, event)
  }
}
