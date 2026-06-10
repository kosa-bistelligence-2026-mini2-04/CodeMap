import { Injectable, NotFoundException } from '@nestjs/common'
import { and, eq } from 'drizzle-orm'
import { db } from '../../../config/database'
import { analysis } from '../../../config/database/schema'

interface GetAnalysisParams {
  analysisId: string
  userId: string
}

@Injectable()
export class GetAnalysisUseCase {
  async execute({ analysisId, userId }: GetAnalysisParams) {
    const [row] = await db
      .select()
      .from(analysis)
      .where(and(eq(analysis.id, analysisId), eq(analysis.userId, userId)))

    if (!row) throw new NotFoundException('Analysis not found')
    const result = row.result ? JSON.parse(row.result) : null
    return { ...row, result }
  }
}
