import { Check, Copy } from 'lucide-react'
import { type ComponentProps, type ReactNode, useCallback, useState } from 'react'
import { cn } from '../lib/utils'

interface CodeBlockProps extends ComponentProps<'pre'> {
  language?: string
  raw: string
  children?: ReactNode
}

export function CodeBlock({ language, raw, children, className, ...rest }: CodeBlockProps) {
  const [copied, setCopied] = useState(false)

  const onCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(raw)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {}
  }, [raw])

  return (
    <div className="group relative my-3 overflow-hidden rounded-lg border border-border bg-card">
      <div className="flex items-center justify-between border-b border-border bg-muted/40 px-3 py-1.5 text-xs">
        <span className="font-mono text-muted-foreground">{language || 'code'}</span>
        <button
          type="button"
          onClick={onCopy}
          className="inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-muted-foreground transition hover:bg-muted hover:text-foreground"
          aria-label="Copy code"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5" /> Copied
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" /> Copy
            </>
          )}
        </button>
      </div>
      <pre className={cn('overflow-x-auto p-3 text-sm leading-relaxed', className)} {...rest}>
        {children}
      </pre>
    </div>
  )
}

export function InlineCode({ className, ...rest }: ComponentProps<'code'>) {
  return (
    <code
      className={cn(
        'rounded bg-muted px-1.5 py-0.5 font-mono text-[0.9em] text-foreground',
        className,
      )}
      {...rest}
    />
  )
}
