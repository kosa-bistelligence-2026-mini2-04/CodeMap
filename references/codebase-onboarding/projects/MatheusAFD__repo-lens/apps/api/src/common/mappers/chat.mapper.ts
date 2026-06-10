import type { Chat, ChatMessage } from '@repo/shared'
import type { chat, chatMessage } from '../../config/database/schema'

export function toChat(row: typeof chat.$inferSelect): Chat {
  return {
    id: row.id,
    repositoryId: row.repositoryId,
    userId: row.userId,
    title: row.title,
    lastMessageAt: row.lastMessageAt.toISOString(),
    createdAt: row.createdAt.toISOString(),
    updatedAt: row.updatedAt.toISOString(),
  }
}

export function toChatMessage(row: typeof chatMessage.$inferSelect): ChatMessage {
  return {
    id: row.id,
    chatId: row.chatId,
    role: row.role as ChatMessage['role'],
    content: row.content,
    status: row.status as ChatMessage['status'],
    errorMessage: row.errorMessage,
    inputTokens: row.inputTokens,
    outputTokens: row.outputTokens,
    createdAt: row.createdAt.toISOString(),
  }
}
