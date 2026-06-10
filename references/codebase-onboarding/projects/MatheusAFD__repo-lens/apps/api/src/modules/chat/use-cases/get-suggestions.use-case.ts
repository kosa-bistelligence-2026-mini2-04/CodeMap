import { Injectable } from '@nestjs/common'
import type {
  AnalysisSectionType,
  PromptSuggestion,
  PromptSuggestionsResponse,
  Result,
} from '@repo/shared'
import { ScopeMapperService } from '../scope-mapper.service'
import { LENSES, LENS_PROMPTS, buildAreaPrompt, buildCombinedPrompt } from '../suggestion-templates'

const COMBINED_SUGGESTION_LIMIT = 6
const COMBINED_LENS_IDS: AnalysisSectionType[] = ['security', 'architecture', 'tech_stack']

interface GetSuggestionsParams {
  repoId: string
  userId: string
}

@Injectable()
export class GetSuggestionsUseCase {
  constructor(private readonly scopeMapper: ScopeMapperService) {}

  async execute({
    repoId,
    userId,
  }: GetSuggestionsParams): Promise<Result<PromptSuggestionsResponse>> {
    const [areasErr, areas] = await this.scopeMapper.getCodeAreas(repoId, userId)
    if (areasErr || !areas) return [areasErr ?? new Error('Could not load areas'), null]

    const suggestions: PromptSuggestion[] = []

    for (const lens of LENSES) {
      suggestions.push({
        id: `lens:${lens.id}`,
        label: lens.label,
        prompt: LENS_PROMPTS[lens.id],
        axis: 'lens',
        lensId: lens.id,
      })
    }

    for (const area of areas) {
      suggestions.push({
        id: `area:${area.id}`,
        label: area.label,
        prompt: buildAreaPrompt(area.label),
        axis: 'area',
        areaId: area.id,
      })
    }

    let combinedCount = 0
    outer: for (const area of areas) {
      for (const lensId of COMBINED_LENS_IDS) {
        if (combinedCount >= COMBINED_SUGGESTION_LIMIT) break outer
        const lens = LENSES.find((l) => l.id === lensId)
        if (!lens) continue
        suggestions.push({
          id: `combined:${area.id}:${lens.id}`,
          label: `${lens.label} · ${area.label}`,
          prompt: buildCombinedPrompt(area.label, lens.label),
          axis: 'combined',
          areaId: area.id,
          lensId: lens.id,
        })
        combinedCount += 1
      }
    }

    return [null, { areas, lenses: LENSES, suggestions }]
  }
}
