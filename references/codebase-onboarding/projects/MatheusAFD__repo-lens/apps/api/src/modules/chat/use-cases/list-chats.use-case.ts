import { Injectable } from '@nestjs/common'
import type { Chat, Result } from '@repo/shared'
import { and, desc, eq } from 'drizzle-orm'
import { toChat } from '../../../common/mappers/chat.mapper'
import { db } from '../../../config/database'
import { chat } from '../../../config/database/schema'
import { ReposService } from '../../repos/repos.service'

interface ListChatsParams {
  repoId: string
  userId: string
}

@Injectable()
export class ListChatsUseCase {
  constructor(private readonly reposService: ReposService) {}

  async execute({ repoId, userId }: ListChatsParams): Promise<Result<Chat[]>> {
    const [repoErr] = await this.reposService.getRepo(repoId, userId)
    if (repoErr) return [repoErr, null]

    const rows = await db
      .select()
      .from(chat)
      .where(and(eq(chat.repositoryId, repoId), eq(chat.userId, userId)))
      .orderBy(desc(chat.lastMessageAt))

    return [null, rows.map(toChat)]
  }
}
