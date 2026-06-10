import type { ChatMessage as ChatMessageType } from '@repo/shared'
import { ScrollArea } from '@repo/ui/components/scroll-area'
import { Skeleton } from '@repo/ui/components/skeleton'
import { useCallback, useEffect, useRef } from 'react'
import { ChatMessage } from './chat-message'

interface ChatThreadProps {
  messages: ChatMessageType[] | undefined
  isLoading: boolean
  isStreaming: boolean
  streamingMessageId: string | null
  streamingContent: string
}

const STICKY_THRESHOLD_PX = 120

export function ChatThread({
  messages,
  isLoading,
  isStreaming,
  streamingMessageId,
  streamingContent,
}: ChatThreadProps) {
  const scrollAreaRef = useRef<HTMLDivElement | null>(null)
  const stickToBottomRef = useRef(true)
  const messageCount = messages?.length ?? 0

  const getViewport = useCallback((): HTMLElement | null => {
    return (
      scrollAreaRef.current?.querySelector<HTMLElement>('[data-radix-scroll-area-viewport]') ?? null
    )
  }, [])

  const scrollToBottom = useCallback(
    (smooth: boolean) => {
      const viewport = getViewport()
      if (!viewport) return
      viewport.scrollTo({
        top: viewport.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto',
      })
    },
    [getViewport],
  )

  useEffect(() => {
    const viewport = getViewport()
    if (!viewport) return
    const onScroll = () => {
      const distance = viewport.scrollHeight - viewport.scrollTop - viewport.clientHeight
      stickToBottomRef.current = distance < STICKY_THRESHOLD_PX
    }
    viewport.addEventListener('scroll', onScroll, { passive: true })
    return () => viewport.removeEventListener('scroll', onScroll)
  }, [getViewport])

  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll on count change is intentional
  useEffect(() => {
    scrollToBottom(true)
  }, [messageCount])

  // biome-ignore lint/correctness/useExhaustiveDependencies: scroll on streaming chunks
  useEffect(() => {
    if (!isStreaming) return
    if (!stickToBottomRef.current) return
    scrollToBottom(false)
  }, [isStreaming, streamingContent])

  if (isLoading) {
    return (
      <div className="space-y-4 p-4">
        <Skeleton className="h-16 w-2/3" />
        <Skeleton className="h-24 w-3/4 ml-auto" />
        <Skeleton className="h-20 w-2/3" />
      </div>
    )
  }

  return (
    <ScrollArea ref={scrollAreaRef} className="h-full">
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-6 pb-32">
        {messages?.map((msg) => {
          const isStreamingThis = isStreaming && streamingMessageId === msg.id
          const content = isStreamingThis ? streamingContent : msg.content
          return (
            <ChatMessage
              key={msg.id}
              senderRole={msg.role}
              content={content}
              isStreaming={isStreamingThis}
              hasError={msg.status === 'failed'}
            />
          )
        })}
        {isStreaming && !streamingMessageId && (
          <ChatMessage senderRole="assistant" content={streamingContent} isStreaming />
        )}
      </div>
    </ScrollArea>
  )
}
