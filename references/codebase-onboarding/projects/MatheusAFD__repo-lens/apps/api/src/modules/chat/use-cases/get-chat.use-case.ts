import { Injectable } from '@nestjs/common'
import type { Chat, Result } from '@repo/shared'
import { toChat } from '../../../common/mappers/chat.mapper'
import { loadChatRow } from './load-chat-row'

interface GetChatParams {
  chatId: string
  userId: string
}

@Injectable()
export class GetChatUseCase {
  async execute({ chatId, userId }: GetChatParams): Promise<Result<Chat>> {
    const row = await loadChatRow(chatId, userId)
    return [null, toChat(row)]
  }
}
