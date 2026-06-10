import { Injectable } from '@nestjs/common'
import type { Chat, Result } from '@repo/shared'
import { toChat } from '../../../common/mappers/chat.mapper'
import { db } from '../../../config/database'
import { chat } from '../../../config/database/schema'
import { ReposService } from '../../repos/repos.service'

interface CreateChatParams {
  repoId: string
  userId: string
  title?: string
}

@Injectable()
export class CreateChatUseCase {
  constructor(private readonly reposService: ReposService) {}

  async execute({ repoId, userId, title }: CreateChatParams): Promise<Result<Chat>> {
    const [repoErr] = await this.reposService.getRepo(repoId, userId)
    if (repoErr) return [repoErr, null]

    const [created] = await db
      .insert(chat)
      .values({
        repositoryId: repoId,
        userId,
        title: title?.trim() || 'New conversation',
      })
      .returning()

    return [null, toChat(created)]
  }
}
