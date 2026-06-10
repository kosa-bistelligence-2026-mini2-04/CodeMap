import { getChatMessages } from '@/services/http/chat'
import type { ChatMessage } from '@repo/shared'
import { useQuery } from '@tanstack/react-query'

export const chatMessagesQueryKey = (chatId: string) => ['chat', chatId, 'messages'] as const

export function useChatMessages(chatId: string | undefined) {
  return useQuery<ChatMessage[]>({
    queryKey: chatMessagesQueryKey(chatId ?? ''),
    queryFn: () => getChatMessages(chatId as string),
    enabled: !!chatId,
  })
}
