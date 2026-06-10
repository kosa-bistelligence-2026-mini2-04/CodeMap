import { Button } from '@repo/ui/components/button'
import { Textarea } from '@repo/ui/components/textarea'
import { cn } from '@repo/ui/lib/utils'
import { Loader2, Send, Square } from 'lucide-react'
import {
  type FormEvent,
  type KeyboardEvent,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from 'react'

export interface ChatComposerHandle {
  setContent: (value: string) => void
  focus: () => void
}

interface ChatComposerProps {
  ref?: React.Ref<ChatComposerHandle>
  disabled?: boolean
  isStreaming: boolean
  onSubmit: (content: string) => Promise<void> | void
  onCancel?: () => void
  initialValue?: string
  placeholder?: string
}

export function ChatComposer({
  ref,
  disabled,
  isStreaming,
  onSubmit,
  onCancel,
  initialValue = '',
  placeholder = 'Ask anything about this repository…',
}: ChatComposerProps) {
  const [value, setValue] = useState(initialValue)
  const textareaRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    setValue(initialValue)
  }, [initialValue])

  useImperativeHandle(ref, () => ({
    setContent: (next: string) => {
      setValue(next)
      requestAnimationFrame(() => textareaRef.current?.focus())
    },
    focus: () => textareaRef.current?.focus(),
  }))

  const canSubmit = value.trim().length > 0 && !disabled && !isStreaming

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canSubmit) return
    const content = value.trim()
    setValue('')
    await onSubmit(content)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      if (canSubmit) {
        const content = value.trim()
        setValue('')
        void onSubmit(content)
      }
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(
        'sticky bottom-0 z-10 border-t border-border bg-background/80 backdrop-blur-sm',
        'pb-[env(safe-area-inset-bottom)]',
      )}
    >
      <div className="mx-auto flex w-full max-w-3xl items-end gap-2 px-4 py-3">
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className="min-h-[44px] max-h-48 flex-1 resize-none rounded-xl border-border bg-card px-3 py-2.5 text-sm shadow-sm focus-visible:ring-1"
        />
        {isStreaming ? (
          <Button
            type="button"
            variant="outline"
            size="icon"
            onClick={onCancel}
            className="h-11 w-11 shrink-0 rounded-xl"
            aria-label="Stop"
          >
            <Square className="h-4 w-4" aria-hidden="true" />
          </Button>
        ) : (
          <Button
            type="submit"
            size="icon"
            disabled={!canSubmit}
            className="h-11 w-11 shrink-0 rounded-xl"
            aria-label="Send"
          >
            {disabled ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Send className="h-4 w-4" aria-hidden="true" />
            )}
          </Button>
        )}
      </div>
    </form>
  )
}
