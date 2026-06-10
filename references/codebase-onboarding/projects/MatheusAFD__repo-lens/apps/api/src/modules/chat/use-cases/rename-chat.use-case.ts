import { Injectable } from '@nestjs/common'
import type { Chat, Result } from '@repo/shared'
import { eq } from 'drizzle-orm'
import { toChat } from '../../../common/mappers/chat.mapper'
import { db } from '../../../config/database'
import { chat } from '../../../config/database/schema'
import { loadChatRow } from './load-chat-row'

interface RenameChatParams {
  chatId: string
  userId: string
  title: string
}

@Injectable()
export class RenameChatUseCase {
  async execute({ chatId, userId, title }: RenameChatParams): Promise<Result<Chat>> {
    await loadChatRow(chatId, userId)
    const trimmed = title.trim()
    if (!trimmed) return [new Error('Title cannot be empty'), null]

    const [updated] = await db
      .update(chat)
      .set({ title: trimmed.slice(0, 100) })
      .where(eq(chat.id, chatId))
      .returning()

    return [null, toChat(updated)]
  }
}
