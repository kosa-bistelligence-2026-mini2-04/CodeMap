import { Module } from '@nestjs/common'
import { AnalysisModule } from '../analysis/analysis.module'
import { GithubModule } from '../github/github.module'
import { ReposModule } from '../repos/repos.module'
import { ChatPromptBuilderService } from './chat-prompt-builder.service'
import { ChatController } from './chat.controller'
import { ChatService } from './chat.service'
import { ScopeMapperService } from './scope-mapper.service'
import { CreateChatUseCase } from './use-cases/create-chat.use-case'
import { DeleteChatUseCase } from './use-cases/delete-chat.use-case'
import { GetChatUseCase } from './use-cases/get-chat.use-case'
import { GetSuggestionsUseCase } from './use-cases/get-suggestions.use-case'
import { ListChatsUseCase } from './use-cases/list-chats.use-case'
import { ListMessagesUseCase } from './use-cases/list-messages.use-case'
import { RenameChatUseCase } from './use-cases/rename-chat.use-case'
import { SendMessageUseCase } from './use-cases/send-message.use-case'

@Module({
  imports: [GithubModule, ReposModule, AnalysisModule],
  controllers: [ChatController],
  providers: [
    ChatService,
    ChatPromptBuilderService,
    ScopeMapperService,
    CreateChatUseCase,
    ListChatsUseCase,
    GetChatUseCase,
    ListMessagesUseCase,
    RenameChatUseCase,
    DeleteChatUseCase,
    GetSuggestionsUseCase,
    SendMessageUseCase,
  ],
})
export class ChatModule {}
