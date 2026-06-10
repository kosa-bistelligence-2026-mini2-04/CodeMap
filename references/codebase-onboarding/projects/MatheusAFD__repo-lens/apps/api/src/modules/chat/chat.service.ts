import { Injectable } from '@nestjs/common'
import type { SendMessageRequest } from '@repo/shared'
import { CreateChatUseCase } from './use-cases/create-chat.use-case'
import { DeleteChatUseCase } from './use-cases/delete-chat.use-case'
import { GetChatUseCase } from './use-cases/get-chat.use-case'
import { GetSuggestionsUseCase } from './use-cases/get-suggestions.use-case'
import { ListChatsUseCase } from './use-cases/list-chats.use-case'
import { ListMessagesUseCase } from './use-cases/list-messages.use-case'
import { RenameChatUseCase } from './use-cases/rename-chat.use-case'
import { SendMessageUseCase } from './use-cases/send-message.use-case'

@Injectable()
export class ChatService {
  constructor(
    private readonly createChatUseCase: CreateChatUseCase,
    private readonly listChatsUseCase: ListChatsUseCase,
    private readonly getChatUseCase: GetChatUseCase,
    private readonly listMessagesUseCase: ListMessagesUseCase,
    private readonly renameChatUseCase: RenameChatUseCase,
    private readonly deleteChatUseCase: DeleteChatUseCase,
    private readonly getSuggestionsUseCase: GetSuggestionsUseCase,
    private readonly sendMessageUseCase: SendMessageUseCase,
  ) {}

  createChat(repoId: string, userId: string, title?: string) {
    return this.createChatUseCase.execute({ repoId, userId, title })
  }

  listChats(repoId: string, userId: string) {
    return this.listChatsUseCase.execute({ repoId, userId })
  }

  getChat(chatId: string, userId: string) {
    return this.getChatUseCase.execute({ chatId, userId })
  }

  listMessages(chatId: string, userId: string) {
    return this.listMessagesUseCase.execute({ chatId, userId })
  }

  renameChat(chatId: string, userId: string, title: string) {
    return this.renameChatUseCase.execute({ chatId, userId, title })
  }

  deleteChat(chatId: string, userId: string) {
    return this.deleteChatUseCase.execute({ chatId, userId })
  }

  getSuggestions(repoId: string, userId: string) {
    return this.getSuggestionsUseCase.execute({ repoId, userId })
  }

  sendMessage(chatId: string, userId: string, body: SendMessageRequest) {
    return this.sendMessageUseCase.execute({ chatId, userId, body })
  }
}
