import { Injectable } from '@nestjs/common'
import type { ChatMessage, Result } from '@repo/shared'
import { asc, eq } from 'drizzle-orm'
import { toChatMessage } from '../../../common/mappers/chat.mapper'
import { db } from '../../../config/database'
import { chatMessage } from '../../../config/database/schema'
import { loadChatRow } from './load-chat-row'

interface ListMessagesParams {
  chatId: string
  userId: string
}

@Injectable()
export class ListMessagesUseCase {
  async execute({ chatId, userId }: ListMessagesParams): Promise<Result<ChatMessage[]>> {
    await loadChatRow(chatId, userId)

    const rows = await db
      .select()
      .from(chatMessage)
      .where(eq(chatMessage.chatId, chatId))
      .orderBy(asc(chatMessage.createdAt))

    return [null, rows.map(toChatMessage)]
  }
}
