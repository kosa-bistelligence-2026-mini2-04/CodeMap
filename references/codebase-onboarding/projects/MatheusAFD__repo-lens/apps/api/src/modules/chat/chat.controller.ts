import {
  BadRequestException,
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Patch,
  Post,
  Sse,
} from '@nestjs/common'
import { Throttle } from '@nestjs/throttler'
import { Session, type UserSession } from '@thallesp/nestjs-better-auth'
import type { Observable } from 'rxjs'
import { ChatService } from './chat.service'
import { RenameChatDto } from './dto/rename-chat.dto'
import { CreateChatDto, SendMessageDto } from './dto/send-message.dto'

@Controller('chat')
export class ChatController {
  constructor(private readonly chatService: ChatService) {}

  @Post('repos/:repoId')
  async createChat(
    @Param('repoId') repoId: string,
    @Body() body: CreateChatDto,
    @Session() session: UserSession,
  ) {
    const [error, data] = await this.chatService.createChat(repoId, session.user.id, body?.title)
    if (error) throw error
    return data
  }

  @Get('repos/:repoId')
  async listChats(@Param('repoId') repoId: string, @Session() session: UserSession) {
    const [error, data] = await this.chatService.listChats(repoId, session.user.id)
    if (error) throw error
    return data
  }

  @Get('repos/:repoId/suggestions')
  async getSuggestions(@Param('repoId') repoId: string, @Session() session: UserSession) {
    const [error, data] = await this.chatService.getSuggestions(repoId, session.user.id)
    if (error) throw error
    return data
  }

  @Get(':chatId')
  async getChat(@Param('chatId') chatId: string, @Session() session: UserSession) {
    const [error, data] = await this.chatService.getChat(chatId, session.user.id)
    if (error) throw error
    return data
  }

  @Get(':chatId/messages')
  async listMessages(@Param('chatId') chatId: string, @Session() session: UserSession) {
    const [error, data] = await this.chatService.listMessages(chatId, session.user.id)
    if (error) throw error
    return data
  }

  @Throttle({ chat: { ttl: 60_000, limit: 15 } })
  @Post(':chatId/messages')
  @Sse()
  sendMessage(
    @Param('chatId') chatId: string,
    @Body() body: SendMessageDto,
    @Session() session: UserSession,
  ): Promise<Observable<MessageEvent>> {
    if (!body?.content?.trim()) {
      throw new BadRequestException('Message content is required')
    }
    return this.chatService.sendMessage(chatId, session.user.id, body)
  }

  @Patch(':chatId')
  async renameChat(
    @Param('chatId') chatId: string,
    @Body() body: RenameChatDto,
    @Session() session: UserSession,
  ) {
    if (!body?.title?.trim()) {
      throw new BadRequestException('Title is required')
    }
    const [error, data] = await this.chatService.renameChat(chatId, session.user.id, body.title)
    if (error) throw error
    return data
  }

  @Delete(':chatId')
  async deleteChat(@Param('chatId') chatId: string, @Session() session: UserSession) {
    const [error, data] = await this.chatService.deleteChat(chatId, session.user.id)
    if (error) throw error
    return data
  }
}
