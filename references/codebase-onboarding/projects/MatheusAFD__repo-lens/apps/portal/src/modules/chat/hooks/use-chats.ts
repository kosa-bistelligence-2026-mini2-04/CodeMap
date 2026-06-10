import { createChat, listChats } from '@/services/http/chat'
import type { Chat, CreateChatRequest } from '@repo/shared'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

export function useChats(repoId: string) {
  return useQuery<Chat[]>({
    queryKey: ['chats', repoId],
    queryFn: () => listChats(repoId),
    enabled: !!repoId,
  })
}

export function useCreateChat(repoId: string) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateChatRequest = {}) => createChat(repoId, body),
    onSuccess: (chat) => {
      queryClient.setQueryData<Chat[]>(['chats', repoId], (prev) =>
        prev ? [chat, ...prev.filter((c) => c.id !== chat.id)] : [chat],
      )
    },
  })
}
