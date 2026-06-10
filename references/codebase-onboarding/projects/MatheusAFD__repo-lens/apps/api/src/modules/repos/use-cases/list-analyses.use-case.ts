import { Injectable } from '@nestjs/common'
import { and, desc, eq } from 'drizzle-orm'
import { db } from '../../../config/database'
import { analysis } from '../../../config/database/schema'

interface ListAnalysesParams {
  repoId: string
  userId: string
}

@Injectable()
export class ListAnalysesUseCase {
  async execute({ repoId, userId }: ListAnalysesParams) {
    const rows = await db
      .select({
        id: analysis.id,
        status: analysis.status,
        createdAt: analysis.createdAt,
        completedAt: analysis.completedAt,
        inputTokens: analysis.inputTokens,
        outputTokens: analysis.outputTokens,
        result: analysis.result,
      })
      .from(analysis)
      .where(and(eq(analysis.repositoryId, repoId), eq(analysis.userId, userId)))
      .orderBy(desc(analysis.createdAt))

    return rows.map(({ result, ...rest }) => {
      let securityGrade: string | null = null
      if (result) {
        try {
          const parsed = JSON.parse(result)
          securityGrade = parsed?.security?.grade ?? null
        } catch {
          securityGrade = null
        }
      }
      return { ...rest, securityGrade }
    })
  }
}
