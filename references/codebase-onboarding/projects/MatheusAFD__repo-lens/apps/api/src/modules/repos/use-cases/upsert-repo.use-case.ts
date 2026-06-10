import { randomUUID } from 'node:crypto'
import { Injectable } from '@nestjs/common'
import type { Result } from '@repo/shared'
import { and, eq } from 'drizzle-orm'
import { db } from '../../../config/database'
import { repository } from '../../../config/database/schema'

export interface UpsertRepoDto {
  githubRepoId: string
  owner: string
  name: string
  fullName: string
  description?: string | null
  language?: string | null
  isPrivate: boolean
  htmlUrl: string
}

interface UpsertRepoParams {
  userId: string
  dto: UpsertRepoDto
}

@Injectable()
export class UpsertRepoUseCase {
  async execute({
    userId,
    dto,
  }: UpsertRepoParams): Promise<Result<typeof repository.$inferSelect>> {
    const existing = await db
      .select()
      .from(repository)
      .where(and(eq(repository.userId, userId), eq(repository.githubRepoId, dto.githubRepoId)))
      .limit(1)

    if (existing[0]) {
      const [updated] = await db
        .update(repository)
        .set({
          owner: dto.owner,
          name: dto.name,
          fullName: dto.fullName,
          description: dto.description ?? null,
          language: dto.language ?? null,
          isPrivate: dto.isPrivate,
          htmlUrl: dto.htmlUrl,
        })
        .where(eq(repository.id, existing[0].id))
        .returning()

      return [null, updated]
    }

    const [created] = await db
      .insert(repository)
      .values({
        id: randomUUID(),
        userId,
        githubRepoId: dto.githubRepoId,
        owner: dto.owner,
        name: dto.name,
        fullName: dto.fullName,
        description: dto.description ?? null,
        language: dto.language ?? null,
        isPrivate: dto.isPrivate,
        htmlUrl: dto.htmlUrl,
      })
      .returning()

    return [null, created]
  }
}
