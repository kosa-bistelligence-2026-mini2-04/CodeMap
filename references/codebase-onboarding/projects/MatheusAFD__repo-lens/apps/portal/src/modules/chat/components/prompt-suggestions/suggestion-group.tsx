import type { PromptSuggestion } from '@repo/shared'
import { Button } from '@repo/ui/components/button'
import { cn } from '@repo/ui/lib/utils'

interface SuggestionGroupProps {
  title: string
  description: string
  suggestions: PromptSuggestion[]
  variant: 'outline' | 'secondary' | 'ghost'
  onPick: (suggestion: PromptSuggestion) => void
  disabled?: boolean
}

export function SuggestionGroup({
  title,
  description,
  suggestions,
  variant,
  onPick,
  disabled,
}: SuggestionGroupProps) {
  return (
    <div className="space-y-2">
      <div className="flex flex-col">
        <span className="text-sm font-medium text-foreground">{title}</span>
        <span className="text-xs text-muted-foreground">{description}</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((suggestion) => (
          <Button
            key={suggestion.id}
            type="button"
            size="sm"
            variant={variant}
            disabled={disabled}
            onClick={() => onPick(suggestion)}
            className={cn('h-8 rounded-full text-xs')}
          >
            {suggestion.label}
          </Button>
        ))}
      </div>
    </div>
  )
}
