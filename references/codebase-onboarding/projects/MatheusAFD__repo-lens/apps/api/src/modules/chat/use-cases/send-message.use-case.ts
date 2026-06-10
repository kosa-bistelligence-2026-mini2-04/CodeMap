import Anthropic from '@anthropic-ai/sdk'
import { Injectable } from '@nestjs/common'
import type { ChatSseEvent, CodeArea, SendMessageRequest } from '@repo/shared'
import { desc, eq } from 'drizzle-orm'
import { type Observable, Subject } from 'rxjs'
import { SseSubjectPool } from '../../../common/streaming/sse-subject-pool'
import { db } from '../../../config/database'
import { chat, chatMessage, repository } from '../../../config/database/schema'
import { AnalysisService } from '../../analysis/analysis.service'
import { ContextBuilderService } from '../../analysis/context-builder.service'
import { GithubService } from '../../github/github.service'
import { ReposService } from '../../repos/repos.service'
import { ChatPromptBuilderService } from '../chat-prompt-builder.service'
import { ScopeMapperService } from '../scope-mapper.service'
import { loadChatRow } from './load-chat-row'

const HISTORY_WINDOW = 12
const HISTORY_CHAR_BUDGET = 6000
const BOOTSTRAP_FILE_LIMIT = 30
const BOOTSTRAP_CHAR_BUDGET = 20_000
const TITLE_MAX_LENGTH = 60

interface SendMessageParams {
  chatId: string
  userId: string
  body: SendMessageRequest
}

interface RunStreamArgs {
  streamKey: string
  subject: Subject<MessageEvent>
  chatRow: typeof chat.$inferSelect
  repo: typeof repository.$inferSelect
  userId: string
  userMessageId: string
  assistantMessageId: string
  newContent: string
}

@Injectable()
export class SendMessageUseCase {
  private readonly anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
  private readonly pool = new SseSubjectPool<ChatSseEvent>()

  constructor(
    private readonly reposService: ReposService,
    private readonly githubService: GithubService,
    private readonly contextBuilder: ContextBuilderService,
    private readonly analysisService: AnalysisService,
    private readonly chatPromptBuilder: ChatPromptBuilderService,
    private readonly scopeMapper: ScopeMapperService,
  ) {}

  async execute({ chatId, userId, body }: SendMessageParams): Promise<Observable<MessageEvent>> {
    const chatRow = await loadChatRow(chatId, userId)
    const content = body.content?.trim() ?? ''
    if (!content) throw new Error('Message content is required')

    const [repoErr, repo] = await this.reposService.getRepo(chatRow.repositoryId, userId)
    if (repoErr || !repo) throw repoErr ?? new Error('Repository not found')

    const [{ userMessageId }] = await db
      .insert(chatMessage)
      .values({ chatId, role: 'user', content, status: 'complete' })
      .returning({ userMessageId: chatMessage.id })

    await db.update(chat).set({ lastMessageAt: new Date() }).where(eq(chat.id, chatId))

    const [{ assistantMessageId }] = await db
      .insert(chatMessage)
      .values({ chatId, role: 'assistant', content: '', status: 'streaming' })
      .returning({ assistantMessageId: chatMessage.id })

    const streamKey = `chat:${assistantMessageId}`
    const subject = this.pool.create(streamKey)

    this.runStream({
      streamKey,
      subject,
      chatRow,
      repo,
      userId,
      userMessageId,
      assistantMessageId,
      newContent: content,
    }).catch(async (error: Error) => {
      await db
        .update(chatMessage)
        .set({ status: 'failed', errorMessage: error?.message ?? 'Unknown error' })
        .where(eq(chatMessage.id, assistantMessageId))

      this.pool.emit(streamKey, {
        type: 'error',
        message: error?.message ?? 'Failed to generate response',
      })
      this.pool.complete(streamKey)
    })

    return subject.asObservable()
  }

  private async runStream(args: RunStreamArgs): Promise<void> {
    const { streamKey, chatRow, repo, userId, userMessageId, assistantMessageId, newContent } = args

    this.pool.emit(streamKey, { type: 'message_start', messageId: assistantMessageId })

    const isMockMode = process.env.ANTHROPIC_MOCK === 'true'

    const bootstrap = await this.ensureBootstrap(chatRow, repo, userId, isMockMode)
    const history = await this.loadHistory(chatRow.id, userMessageId)
    const latestAnalysis = await this.analysisService
      .getLatestAnalysis(repo.id, userId)
      .catch(() => null)
    const latestAnalysisResult = latestAnalysis?.result ?? null

    const [, areas] = await this.scopeMapper.getCodeAreas(repo.id, userId)
    const areasList: CodeArea[] = areas ?? []

    const systemPrompt = this.chatPromptBuilder.buildSystemPrompt(
      {
        owner: repo.owner,
        name: repo.name,
        language: repo.language,
        description: repo.description,
      },
      !!latestAnalysisResult,
      !!bootstrap,
      areasList,
    )

    const messages: { role: 'user' | 'assistant'; content: string }[] = []

    if (bootstrap) {
      messages.push({ role: 'user', content: bootstrap })
      messages.push({ role: 'assistant', content: 'Understood. Ready for your questions.' })
    }

    for (const turn of history) {
      messages.push({ role: turn.role as 'user' | 'assistant', content: turn.content })
    }

    messages.push({ role: 'user', content: newContent })

    let buffer = ''
    let inputTokens = 0
    let outputTokens = 0

    const stream = isMockMode
      ? // biome-ignore lint/suspicious/noExplicitAny: dynamic require used only in test mode
        (require('../__mocks__/chat-stream.fixture') as any).createMockChatStream()
      : this.anthropic.messages.stream({
          model: 'claude-sonnet-4-6',
          max_tokens: 4096,
          system: systemPrompt,
          messages,
        })

    for await (const chunk of stream) {
      if (chunk.type === 'content_block_delta' && chunk.delta?.type === 'text_delta') {
        const text = chunk.delta.text as string
        buffer += text
        this.pool.emit(streamKey, { type: 'delta', text })
      }
      if (chunk.type === 'message_start' && chunk.message?.usage) {
        inputTokens = chunk.message.usage.input_tokens
      }
      if (chunk.type === 'message_delta' && chunk.usage) {
        outputTokens = chunk.usage.output_tokens
      }
    }

    await db
      .update(chatMessage)
      .set({ content: buffer, status: 'complete', inputTokens, outputTokens })
      .where(eq(chatMessage.id, assistantMessageId))

    await this.maybeAutoTitle(chatRow, newContent)
    await db.update(chat).set({ lastMessageAt: new Date() }).where(eq(chat.id, chatRow.id))

    this.pool.emit(streamKey, {
      type: 'done',
      messageId: assistantMessageId,
      inputTokens,
      outputTokens,
    })
    this.pool.complete(streamKey)
  }

  private async ensureBootstrap(
    chatRow: typeof chat.$inferSelect,
    repo: typeof repository.$inferSelect,
    userId: string,
    isMockMode: boolean,
  ): Promise<string | null> {
    if (chatRow.bootstrapContext) return chatRow.bootstrapContext

    let files: { path: string; content: string }[] = []

    if (!isMockMode) {
      const token = await this.githubService.getToken(userId)
      if (token) {
        const [treeErr, tree] = await this.githubService.getRepoTree(repo.owner, repo.name, token)
        if (!treeErr && tree) {
          const built = await this.contextBuilder.buildContext(
            repo.owner,
            repo.name,
            tree,
            this.githubService,
            token,
          )
          files = this.shrinkBootstrap(built, BOOTSTRAP_FILE_LIMIT, BOOTSTRAP_CHAR_BUDGET)
        }
      }
    }

    const latestAnalysis = await this.analysisService
      .getLatestAnalysis(repo.id, userId)
      .catch(() => null)

    const bootstrap = this.chatPromptBuilder.buildBootstrap(
      {
        owner: repo.owner,
        name: repo.name,
        language: repo.language,
        description: repo.description,
      },
      files,
      latestAnalysis?.result ?? null,
    )

    await db.update(chat).set({ bootstrapContext: bootstrap }).where(eq(chat.id, chatRow.id))

    return bootstrap
  }

  private shrinkBootstrap(
    files: { path: string; content: string }[],
    fileLimit: number,
    charBudget: number,
  ): { path: string; content: string }[] {
    const result: { path: string; content: string }[] = []
    let used = 0
    for (const file of files.slice(0, fileLimit)) {
      if (used + file.content.length > charBudget) break
      result.push(file)
      used += file.content.length
    }
    return result
  }

  private async loadHistory(
    chatId: string,
    excludeMessageId: string,
  ): Promise<{ role: string; content: string }[]> {
    const rows = await db
      .select({
        role: chatMessage.role,
        content: chatMessage.content,
        id: chatMessage.id,
        status: chatMessage.status,
        createdAt: chatMessage.createdAt,
      })
      .from(chatMessage)
      .where(eq(chatMessage.chatId, chatId))
      .orderBy(desc(chatMessage.createdAt))
      .limit(HISTORY_WINDOW + 2)

    const filtered = rows
      .filter((row) => row.id !== excludeMessageId && row.status === 'complete')
      .reverse()

    let total = 0
    const truncated: { role: string; content: string }[] = []
    for (let i = filtered.length - 1; i >= 0; i--) {
      const row = filtered[i]
      total += row.content.length
      truncated.unshift({ role: row.role, content: row.content })
      if (total > HISTORY_CHAR_BUDGET && truncated.length > 2) {
        truncated.shift()
        break
      }
    }

    return truncated
  }

  private async maybeAutoTitle(
    chatRow: typeof chat.$inferSelect,
    firstUserContent: string,
  ): Promise<void> {
    if (chatRow.title !== 'New conversation') return

    const trimmed = firstUserContent.trim().replace(/\s+/g, ' ')
    if (!trimmed) return

    let title = trimmed.slice(0, TITLE_MAX_LENGTH)
    if (trimmed.length > TITLE_MAX_LENGTH) {
      const lastSpace = title.lastIndexOf(' ')
      if (lastSpace > 20) title = title.slice(0, lastSpace)
      title = `${title}…`
    }

    await db.update(chat).set({ title }).where(eq(chat.id, chatRow.id))
  }
}
