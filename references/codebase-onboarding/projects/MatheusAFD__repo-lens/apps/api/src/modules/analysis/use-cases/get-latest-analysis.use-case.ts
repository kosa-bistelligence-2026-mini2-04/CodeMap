import { Injectable } from '@nestjs/common'
import { and, desc, eq } from 'drizzle-orm'
import { db } from '../../../config/database'
import { analysis } from '../../../config/database/schema'

interface GetLatestAnalysisParams {
  repoId: string
  userId: string
}

@Injectable()
export class GetLatestAnalysisUseCase {
  async execute({ repoId, userId }: GetLatestAnalysisParams) {
    const [row] = await db
      .select()
      .from(analysis)
      .where(
        and(
          eq(analysis.repositoryId, repoId),
          eq(analysis.userId, userId),
          eq(analysis.status, 'completed'),
        ),
      )
      .orderBy(desc(analysis.completedAt))
      .limit(1)

    if (!row || !row.result) return null
    return { ...row, result: JSON.parse(row.result) }
  }
}
