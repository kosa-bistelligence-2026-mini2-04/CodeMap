import type { Repository } from '@/modules/repos/domain/repo.domain'
import type { PromptSuggestion, PromptSuggestionsResponse } from '@repo/shared'
import { Sparkles } from 'lucide-react'
import { PromptSuggestions } from './prompt-suggestions'

interface ChatEmptyStateProps {
  repo: Repository
  suggestions: PromptSuggestionsResponse | undefined
  onPickSuggestion: (suggestion: PromptSuggestion) => void
  disabled?: boolean
  isLoading?: boolean
}

export function ChatEmptyState({
  repo,
  suggestions,
  onPickSuggestion,
  disabled,
  isLoading,
}: ChatEmptyStateProps) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-10">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
          <Sparkles className="h-4 w-4" aria-hidden="true" />
        </div>
        <div className="space-y-1">
          <h2 className="text-lg font-semibold tracking-tight">Ask anything about {repo.name}</h2>
          <p className="text-sm text-muted-foreground">
            Pick a starting point or type your own question. Answers come from the latest analysis
            of this repository plus selected source files.
          </p>
        </div>
      </div>

      <PromptSuggestions
        data={suggestions}
        onPick={onPickSuggestion}
        disabled={disabled}
        isLoading={isLoading}
      />
    </div>
  )
}
