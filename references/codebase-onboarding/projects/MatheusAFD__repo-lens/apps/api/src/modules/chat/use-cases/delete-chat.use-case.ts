import { Injectable } from '@nestjs/common'
import type { Result } from '@repo/shared'
import { eq } from 'drizzle-orm'
import { db } from '../../../config/database'
import { chat } from '../../../config/database/schema'
import { loadChatRow } from './load-chat-row'

interface DeleteChatParams {
  chatId: string
  userId: string
}

@Injectable()
export class DeleteChatUseCase {
  async execute({ chatId, userId }: DeleteChatParams): Promise<Result<{ success: true }>> {
    await loadChatRow(chatId, userId)
    await db.delete(chat).where(eq(chat.id, chatId))
    return [null, { success: true }]
  }
}
