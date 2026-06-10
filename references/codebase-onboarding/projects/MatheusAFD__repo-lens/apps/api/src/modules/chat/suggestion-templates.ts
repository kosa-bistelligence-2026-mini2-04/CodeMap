import type { AnalysisSectionType, SuggestionLens } from '@repo/shared'

export const LENSES: SuggestionLens[] = [
  { id: 'executive_summary', label: 'Executive summary' },
  { id: 'tech_stack', label: 'Tech stack' },
  { id: 'architecture', label: 'Architecture' },
  { id: 'security', label: 'Security' },
  { id: 'dependencies', label: 'Dependencies' },
  { id: 'update_plan', label: 'Update plan' },
  { id: 'recommendations', label: 'Recommendations' },
  { id: 'code_metrics', label: 'Code metrics' },
  { id: 'fun_facts', label: 'Fun facts' },
]

export const LENS_PROMPTS: Record<AnalysisSectionType, string> = {
  executive_summary: 'Give me a concise executive summary of this repository.',
  tech_stack: 'Walk me through the tech stack used in this repo.',
  architecture: 'Explain the overall architecture and key patterns of this codebase.',
  security: 'Walk me through the security posture of this repo, including likely OWASP concerns.',
  dependencies: 'Which dependencies are outdated or risky, and what should I prioritize?',
  update_plan: 'Suggest a prioritized update plan for the dependencies and tooling.',
  recommendations: 'What are the top recommendations to improve this codebase?',
  code_metrics: 'Summarize the code metrics: size, languages, and largest files.',
  fun_facts: 'Share a few interesting fun facts about this codebase.',
  analysis_progress: 'Compare this repository against the previous analysis.',
}

export function buildAreaPrompt(label: string): string {
  return `Explain how the ${label} area of this codebase is structured.`
}

export function buildCombinedPrompt(areaLabel: string, lensLabel: string): string {
  const lensVerb = lensLabel.toLowerCase()
  return `Walk me through ${lensVerb} concerns specific to the ${areaLabel} area of this repo.`
}
