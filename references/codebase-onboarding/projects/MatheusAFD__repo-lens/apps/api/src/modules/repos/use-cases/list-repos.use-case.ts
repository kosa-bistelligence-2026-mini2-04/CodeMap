import { Injectable } from '@nestjs/common'
import { desc, eq, max } from 'drizzle-orm'
import { db } from '../../../config/database'
import { analysis, repository } from '../../../config/database/schema'

interface ListReposParams {
  userId: string
}

@Injectable()
export class ListReposUseCase {
  async execute({ userId }: ListReposParams) {
    const rows = await db
      .select({
        id: repository.id,
        userId: repository.userId,
        githubRepoId: repository.githubRepoId,
        owner: repository.owner,
        name: repository.name,
        fullName: repository.fullName,
        description: repository.description,
        language: repository.language,
        isPrivate: repository.isPrivate,
        htmlUrl: repository.htmlUrl,
        createdAt: repository.createdAt,
        updatedAt: repository.updatedAt,
        lastAnalyzedAt: max(analysis.createdAt),
      })
      .from(repository)
      .leftJoin(analysis, eq(analysis.repositoryId, repository.id))
      .where(eq(repository.userId, userId))
      .groupBy(repository.id)
      .orderBy(desc(repository.updatedAt))

    return rows.map((r) => ({
      ...r,
      lastAnalyzedAt: r.lastAnalyzedAt ?? null,
      hasAnalysis: r.lastAnalyzedAt !== null,
    }))
  }
}
