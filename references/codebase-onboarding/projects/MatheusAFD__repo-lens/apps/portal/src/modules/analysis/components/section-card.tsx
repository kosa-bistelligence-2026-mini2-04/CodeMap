import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@repo/ui/components/collapsible'
import { cn } from '@repo/ui/lib/utils'
import { useState } from 'react'
import { toast } from 'sonner'

interface SectionCardProps {
  icon: React.ReactNode
  title: string
  description: string
  children: React.ReactNode
  data?: unknown
  isStreaming?: boolean
  className?: string
}

export function SectionCard({
  icon,
  title,
  description,
  children,
  data,
  isStreaming,
  className,
}: SectionCardProps) {
  const [open, setOpen] = useState(true)

  function handleCopy() {
    const text = data ? JSON.stringify(data, null, 2) : ''
    if (!text) return
    navigator.clipboard
      .writeText(text)
      .then(() => toast.success('Copied to clipboard'))
      .catch(() => {})
  }

  return (
    <div
      className={cn(
        'rounded-xl border border-border/60 bg-card overflow-hidden',
        'animate-in fade-in-0 slide-in-from-bottom-4 duration-500',
        className,
      )}
    >
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="w-full flex items-center justify-between gap-3 px-5 py-4 hover:bg-muted/30 transition-colors text-left"
          >
            <div className="flex items-center gap-3 min-w-0">
              <span className="shrink-0 text-muted-foreground">{icon}</span>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-foreground">{title}</h3>
                <p className="text-xs text-muted-foreground">{description}</p>
              </div>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {isStreaming && (
                <div className="flex gap-1">
                  {[0, 1, 2].map((dotIndex) => (
                    <span
                      key={dotIndex}
                      className="w-1.5 h-1.5 rounded-full bg-primary/60 animate-bounce"
                      style={{ animationDelay: `${dotIndex * 150}ms` }}
                    />
                  ))}
                </div>
              )}
              <ChevronIcon open={open} />
            </div>
          </button>
        </CollapsibleTrigger>

        <CollapsibleContent>
          <div className="border-t border-border/40">
            <div className="px-5 py-4">{children}</div>
            <div className="px-5 pb-3 flex justify-end">
              <button
                type="button"
                onClick={handleCopy}
                className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              >
                <CopyIcon />
                Copy
              </button>
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={cn(
        'w-4 h-4 text-muted-foreground transition-transform duration-200',
        open && 'rotate-180',
      )}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  )
}

function CopyIcon() {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="w-3.5 h-3.5"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
      <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
    </svg>
  )
}
