import { Injectable, NotFoundException } from '@nestjs/common'
import { and, eq } from 'drizzle-orm'
import { db } from '../../../config/database'
import { analysis, analysisQuestion } from '../../../config/database/schema'

interface GetQuestionsParams {
  analysisId: string
  userId: string
}

@Injectable()
export class GetQuestionsUseCase {
  async execute({ analysisId, userId }: GetQuestionsParams) {
    const [row] = await db
      .select()
      .from(analysis)
      .where(and(eq(analysis.id, analysisId), eq(analysis.userId, userId)))

    if (!row) throw new NotFoundException('Analysis not found')

    return db
      .select()
      .from(analysisQuestion)
      .where(eq(analysisQuestion.analysisId, analysisId))
      .orderBy(analysisQuestion.createdAt)
  }
}
