import type { PromptSuggestion, PromptSuggestionsResponse } from '@repo/shared'
import { SuggestionGroup } from './suggestion-group'
import { SuggestionsSkeleton } from './suggestions-skeleton'

interface PromptSuggestionsProps {
  data: PromptSuggestionsResponse | undefined
  onPick: (suggestion: PromptSuggestion) => void
  disabled?: boolean
  isLoading?: boolean
}

export function PromptSuggestions({ data, onPick, disabled, isLoading }: PromptSuggestionsProps) {
  if (isLoading || !data) return <SuggestionsSkeleton />

  const lensSuggestions = data.suggestions.filter((s) => s.axis === 'lens')
  const areaSuggestions = data.suggestions.filter((s) => s.axis === 'area')
  const combinedSuggestions = data.suggestions.filter((s) => s.axis === 'combined')

  return (
    <div className="flex flex-col gap-5">
      {areaSuggestions.length > 0 && (
        <SuggestionGroup
          title="Code areas"
          description="Modules detected in this repository"
          suggestions={areaSuggestions}
          variant="outline"
          onPick={onPick}
          disabled={disabled}
        />
      )}
      <SuggestionGroup
        title="Lenses"
        description="Pick an analytical perspective"
        suggestions={lensSuggestions}
        variant="secondary"
        onPick={onPick}
        disabled={disabled}
      />
      {combinedSuggestions.length > 0 && (
        <SuggestionGroup
          title="Combined"
          description="A lens applied to a specific area"
          suggestions={combinedSuggestions}
          variant="ghost"
          onPick={onPick}
          disabled={disabled}
        />
      )}
    </div>
  )
}
