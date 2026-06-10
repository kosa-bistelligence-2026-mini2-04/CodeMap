import { startMessageStream } from '@/services/http/chat'
import type { ChatSseEvent } from '@repo/shared'
import { useQueryClient } from '@tanstack/react-query'
import { useCallback, useRef, useState } from 'react'
import { chatMessagesQueryKey } from './use-chat-messages'

interface UseSendMessageOptions {
  repoId: string
  chatId: string
}

interface SendResult {
  done: boolean
  error?: string
}

export function useSendMessage({ repoId, chatId }: UseSendMessageOptions) {
  const queryClient = useQueryClient()
  const [streamingContent, setStreamingContent] = useState('')
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const cancel = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  const send = useCallback(
    async (content: string, overrideChatId?: string): Promise<SendResult> => {
      if (isStreaming) return { done: false, error: 'Already streaming' }

      const targetChatId = overrideChatId ?? chatId
      if (!targetChatId) return { done: false, error: 'Chat not ready' }

      setIsStreaming(true)
      setStreamingContent('')
      setStreamingMessageId(null)
      setError(null)

      const controller = new AbortController()
      abortRef.current = controller

      try {
        const stream = await startMessageStream({
          chatId: targetChatId,
          content,
          signal: controller.signal,
        })

        const reader = stream.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        let answer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.startsWith('data:')) continue
            const raw = line.slice(5).trim()
            if (!raw) continue
            try {
              const event = JSON.parse(raw) as ChatSseEvent
              if (event.type === 'message_start') {
                setStreamingMessageId(event.messageId)
              } else if (event.type === 'delta') {
                answer += event.text
                setStreamingContent(answer)
              } else if (event.type === 'done') {
                await queryClient.invalidateQueries({
                  queryKey: chatMessagesQueryKey(targetChatId),
                })
                await queryClient.invalidateQueries({ queryKey: ['chats', repoId] })
              } else if (event.type === 'error') {
                setError(event.message)
              }
            } catch {}
          }
        }

        return { done: true }
      } catch (err) {
        const aborted = (err as Error).name === 'AbortError'
        const message = aborted ? 'Stopped' : ((err as Error).message ?? 'Connection lost.')
        if (!aborted) setError(message)
        return { done: false, error: message }
      } finally {
        setIsStreaming(false)
        setStreamingContent('')
        setStreamingMessageId(null)
        abortRef.current = null
      }
    },
    [chatId, repoId, isStreaming, queryClient],
  )

  return {
    send,
    cancel,
    streamingContent,
    streamingMessageId,
    isStreaming,
    error,
  }
}
