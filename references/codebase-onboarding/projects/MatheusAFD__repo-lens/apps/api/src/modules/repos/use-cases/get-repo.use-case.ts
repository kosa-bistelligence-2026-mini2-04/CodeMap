import { Injectable, NotFoundException } from '@nestjs/common'
import type { Result } from '@repo/shared'
import { and, eq } from 'drizzle-orm'
import { db } from '../../../config/database'
import { repository } from '../../../config/database/schema'

interface GetRepoParams {
  repoId: string
  userId: string
}

@Injectable()
export class GetRepoUseCase {
  async execute({
    repoId,
    userId,
  }: GetRepoParams): Promise<Result<typeof repository.$inferSelect>> {
    const [repo] = await db
      .select()
      .from(repository)
      .where(and(eq(repository.id, repoId), eq(repository.userId, userId)))

    if (!repo) return [new NotFoundException('Repository not found'), null]
    return [null, repo]
  }
}
