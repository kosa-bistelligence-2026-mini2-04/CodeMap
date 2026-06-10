import { Injectable } from '@nestjs/common'
import type { AnalysisResult, AnalysisSectionType, SseEvent } from '@repo/shared'
import { and, eq } from 'drizzle-orm'
import { type Observable, Subject } from 'rxjs'
import { toMessageEvent } from '../../../common/streaming/sse-emitter'
import { db } from '../../../config/database'
import { analysis } from '../../../config/database/schema'
import { AnalysisStreamPool } from './analysis-stream-pool'

interface StreamAnalysisParams {
  analysisId: string
  userId: string
}

@Injectable()
export class StreamAnalysisUseCase {
  constructor(private readonly pool: AnalysisStreamPool) {}

  async execute({ analysisId, userId }: StreamAnalysisParams): Promise<Observable<MessageEvent>> {
    const existing = this.pool.get(analysisId)
    if (existing) return existing.asObservable()

    const [row] = await db
      .select()
      .from(analysis)
      .where(and(eq(analysis.id, analysisId), eq(analysis.userId, userId)))

    if (row?.status === 'completed' || row?.status === 'failed') {
      const subject = new Subject<MessageEvent>()
      setTimeout(() => {
        if (row.status === 'completed' && row.result) {
          try {
            const result = JSON.parse(row.result) as Partial<AnalysisResult>
            for (const [name, data] of Object.entries(result)) {
              const sectionEvent: SseEvent = {
                type: 'section',
                name: name as AnalysisSectionType,
                data,
              }
              subject.next(toMessageEvent(sectionEvent))
            }
          } catch {}
        }
        const finalEvent: SseEvent =
          row.status === 'completed'
            ? { type: 'done', analysisId }
            : { type: 'error', message: row.errorMessage ?? 'Analysis failed' }
        subject.next(toMessageEvent(finalEvent))
        subject.complete()
      }, 0)
      return subject.asObservable()
    }

    const subject = this.pool.create(analysisId)
    return subject.asObservable()
  }
}
