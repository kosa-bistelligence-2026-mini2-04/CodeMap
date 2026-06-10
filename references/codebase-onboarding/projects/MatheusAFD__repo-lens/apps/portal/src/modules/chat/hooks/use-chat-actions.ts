import { deleteChat, renameChat } from '@/services/http/chat'
import type { Chat, RenameChatRequest } from '@repo/shared'
import { useMutation, useQueryClient } from '@tanstack/react-query'

export function useRenameChat(repoId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ chatId, body }: { chatId: string; body: RenameChatRequest }) =>
      renameChat(chatId, body),
    onSuccess: (chat) => {
      queryClient.setQueryData<Chat[]>(['chats', repoId], (prev) =>
        prev ? prev.map((c) => (c.id === chat.id ? chat : c)) : prev,
      )
    },
  })
}

export function useDeleteChat(repoId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (chatId: string) => deleteChat(chatId).then(() => chatId),
    onSuccess: (chatId) => {
      queryClient.setQueryData<Chat[]>(['chats', repoId], (prev) =>
        prev ? prev.filter((c) => c.id !== chatId) : prev,
      )
    },
  })
}
