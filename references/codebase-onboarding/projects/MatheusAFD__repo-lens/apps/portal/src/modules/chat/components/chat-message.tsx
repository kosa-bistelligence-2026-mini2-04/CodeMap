import type { ChatMessage as ChatMessageType } from '@repo/shared'
import { Markdown } from '@repo/ui/components/markdown'
import { cn } from '@repo/ui/lib/utils'
import { Bot, User } from 'lucide-react'

interface ChatMessageProps {
  senderRole: ChatMessageType['role']
  content: string
  isStreaming?: boolean
  hasError?: boolean
}

export function ChatMessage({ senderRole, content, isStreaming, hasError }: ChatMessageProps) {
  const isUser = senderRole === 'user'

  return (
    <div
      className={cn('group flex w-full gap-3 px-2', isUser ? 'justify-end' : 'justify-start')}
      data-role={senderRole}
    >
      {!isUser && (
        <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
          <Bot className="h-3.5 w-3.5" aria-hidden="true" />
        </div>
      )}
      <div
        className={cn(
          'max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
          isUser
            ? 'bg-primary text-primary-foreground'
            : hasError
              ? 'border border-destructive/40 bg-destructive/10 text-foreground'
              : 'bg-muted text-foreground',
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap break-words">{content}</p>
        ) : (
          <div className="break-words">
            {content ? (
              <Markdown content={content} />
            ) : (
              <span className="text-muted-foreground italic">Thinking…</span>
            )}
            {isStreaming && (
              <span
                aria-hidden="true"
                className="ml-0.5 inline-block h-3 w-1.5 translate-y-0.5 animate-pulse bg-foreground/70 align-middle"
              />
            )}
          </div>
        )}
      </div>
      {isUser && (
        <div className="mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
          <User className="h-3.5 w-3.5" aria-hidden="true" />
        </div>
      )}
    </div>
  )
}
