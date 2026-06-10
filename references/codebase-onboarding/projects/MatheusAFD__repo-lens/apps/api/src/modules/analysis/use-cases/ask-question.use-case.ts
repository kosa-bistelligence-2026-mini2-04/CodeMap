import Anthropic from '@anthropic-ai/sdk'
import { Injectable, NotFoundException } from '@nestjs/common'
import type { AnalysisResult, AskQuestionRequest, SseEvent } from '@repo/shared'
import { and, eq } from 'drizzle-orm'
import type { Observable } from 'rxjs'
import { SseSubjectPool } from '../../../common/streaming/sse-subject-pool'
import { db } from '../../../config/database'
import { analysis, analysisQuestion } from '../../../config/database/schema'

interface AskQuestionParams {
  analysisId: string
  userId: string
  body: AskQuestionRequest
}

@Injectable()
export class AskQuestionUseCase {
  private readonly anthropic = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })
  private readonly pool = new SseSubjectPool<SseEvent>()

  async execute({
    analysisId,
    userId,
    body,
  }: AskQuestionParams): Promise<Observable<MessageEvent>> {
    const { question } = body

    const [row] = await db
      .select()
      .from(analysis)
      .where(and(eq(analysis.id, analysisId), eq(analysis.userId, userId)))

    if (!row) throw new NotFoundException('Analysis not found')

    const [{ questionId }] = await db
      .insert(analysisQuestion)
      .values({ analysisId, userId, question })
      .returning({ questionId: analysisQuestion.id })

    const savedResult = row.result ? (JSON.parse(row.result) as Partial<AnalysisResult>) : {}
    const contextSummary = JSON.stringify(savedResult, null, 2).slice(0, 8000)

    const systemPrompt = `You are an expert assistant for the repository ${row.repositoryId}. Answer questions concisely based on the analysis context provided.`
    const userPrompt = `Analysis context:\n${contextSummary}\n\nQuestion: ${question}`

    const streamKey = `ask:${questionId}`
    const subject = this.pool.create(streamKey)

    this.runStream(streamKey, questionId, systemPrompt, userPrompt).catch((err: Error) => {
      this.pool.emit(streamKey, { type: 'error', message: err?.message ?? 'Failed to answer' })
      this.pool.complete(streamKey)
    })

    return subject.asObservable()
  }

  private async runStream(
    streamKey: string,
    questionId: string,
    systemPrompt: string,
    userPrompt: string,
  ): Promise<void> {
    let answer = ''
    const stream = this.anthropic.messages.stream({
      model: 'claude-sonnet-4-6',
      max_tokens: 1024,
      system: systemPrompt,
      messages: [{ role: 'user', content: userPrompt }],
    })

    for await (const chunk of stream) {
      if (chunk.type === 'content_block_delta' && chunk.delta.type === 'text_delta') {
        answer += chunk.delta.text
        this.pool.emit(streamKey, { type: 'progress', message: chunk.delta.text })
      }
    }

    await db.update(analysisQuestion).set({ answer }).where(eq(analysisQuestion.id, questionId))

    this.pool.emit(streamKey, { type: 'done', analysisId: questionId })
    this.pool.complete(streamKey)
  }
}
