import type { Repository } from '@/modules/repos/domain/repo.domain'
import type { PromptSuggestion } from '@repo/shared'
import { Skeleton } from '@repo/ui/components/skeleton'
import { useNavigate } from '@tanstack/react-router'
import { useCallback, useRef, useState } from 'react'
import { toast } from 'sonner'
import { useChatMessages } from '../hooks/use-chat-messages'
import { useChats, useCreateChat } from '../hooks/use-chats'
import { usePromptSuggestions } from '../hooks/use-prompt-suggestions'
import { useSendMessage } from '../hooks/use-send-message'
import { ChatComposer, type ChatComposerHandle } from './chat-composer'
import { ChatEmptyState } from './chat-empty-state'
import { ChatHeader } from './chat-header'
import { ChatMobileTrigger } from './chat-mobile-trigger'
import { ChatSidebar } from './chat-sidebar'
import { ChatThread } from './chat-thread'

interface ChatPageProps {
  repo: Repository
  chatId?: string
}

export function ChatPage({ repo, chatId }: ChatPageProps) {
  const navigate = useNavigate()
  const composerRef = useRef<ChatComposerHandle | null>(null)

  const { data: chats, isLoading: chatsLoading } = useChats(repo.id)
  const { data: suggestions, isLoading: suggestionsLoading } = usePromptSuggestions(repo.id)
  const { data: messages, isLoading: messagesLoading } = useChatMessages(chatId)
  const createChat = useCreateChat(repo.id)
  const [isCreating, setIsCreating] = useState(false)
  const [pendingPrompt, setPendingPrompt] = useState<string>('')

  const { send, cancel, streamingContent, streamingMessageId, isStreaming } = useSendMessage({
    repoId: repo.id,
    chatId: chatId ?? '',
  })

  const handlePickSuggestion = useCallback((suggestion: PromptSuggestion) => {
    setPendingPrompt(suggestion.prompt)
    composerRef.current?.setContent(suggestion.prompt)
  }, [])

  const handleSubmit = useCallback(
    async (content: string) => {
      if (!content.trim()) return
      let activeChatId = chatId
      if (!activeChatId) {
        setIsCreating(true)
        try {
          const chat = await createChat.mutateAsync({})
          activeChatId = chat.id
          navigate({
            to: '/repos/$repoId/chat/$chatId' as never,
            params: { repoId: repo.id, chatId: chat.id } as never,
            replace: true,
          })
        } catch (err) {
          toast.error((err as Error).message)
          return
        } finally {
          setIsCreating(false)
        }
      }

      const result = await send(content, activeChatId)
      if (result.error && result.error !== 'Stopped') {
        toast.error(result.error)
      }
    },
    [chatId, createChat, navigate, repo.id, send],
  )

  const showEmptyState = !chatId && !messagesLoading
  const composerDisabled = isCreating
  const hasChats = !chatsLoading && (chats?.length ?? 0) > 0

  return (
    <div className="flex h-screen flex-col">
      <main className="grid h-full min-h-0 flex-1 grid-cols-1 md:grid-cols-[280px_1fr]">
        <div className="hidden md:block">
          <ChatSidebar repo={repo} activeChatId={chatId} />
        </div>
        <section className="flex min-h-0 flex-1 flex-col">
          <ChatHeader
            repo={repo}
            mobileTrigger={<ChatMobileTrigger repo={repo} activeChatId={chatId} />}
          />
          <div className="flex min-h-0 flex-1 flex-col">
            {chatsLoading && !hasChats ? (
              <div className="flex-1 space-y-3 p-6">
                <Skeleton className="h-12 w-3/4" />
                <Skeleton className="h-24 w-2/3" />
                <Skeleton className="h-12 w-1/2" />
              </div>
            ) : showEmptyState ? (
              <div className="flex-1 overflow-y-auto">
                <ChatEmptyState
                  repo={repo}
                  suggestions={suggestions}
                  onPickSuggestion={handlePickSuggestion}
                  disabled={composerDisabled || isStreaming}
                  isLoading={suggestionsLoading}
                />
              </div>
            ) : (
              <ChatThread
                messages={messages}
                isLoading={messagesLoading}
                isStreaming={isStreaming}
                streamingMessageId={streamingMessageId}
                streamingContent={streamingContent}
              />
            )}
            <ChatComposer
              ref={composerRef}
              isStreaming={isStreaming}
              disabled={composerDisabled}
              onSubmit={handleSubmit}
              onCancel={cancel}
              initialValue={pendingPrompt}
            />
          </div>
        </section>
      </main>
    </div>
  )
}
