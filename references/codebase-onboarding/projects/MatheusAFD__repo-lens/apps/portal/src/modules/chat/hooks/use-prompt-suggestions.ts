import { getPromptSuggestions } from '@/services/http/chat'
import type { PromptSuggestionsResponse } from '@repo/shared'
import { useQuery } from '@tanstack/react-query'

export function usePromptSuggestions(repoId: string) {
  return useQuery<PromptSuggestionsResponse>({
    queryKey: ['chat', repoId, 'suggestions'],
    queryFn: () => getPromptSuggestions(repoId),
    enabled: !!repoId,
    staleTime: 1000 * 60 * 60,
  })
}
