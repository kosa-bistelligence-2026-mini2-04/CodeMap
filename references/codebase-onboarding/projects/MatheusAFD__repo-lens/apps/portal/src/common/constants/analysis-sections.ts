import type { AnalysisSectionType } from '@repo/shared'

export const SECTION_META: Record<
  AnalysisSectionType,
  { label: string; description: string; icon: string }
> = {
  analysis_progress: {
    label: 'Progress',
    description: 'What changed since the last analysis',
    icon: '📈',
  },
  executive_summary: {
    label: 'Executive Summary',
    description: 'Plain-language overview of the project',
    icon: '📋',
  },
  tech_stack: {
    label: 'Tech Stack',
    description: 'Languages, frameworks, and tools detected',
    icon: '🛠️',
  },
  architecture: {
    label: 'Architecture',
    description: 'Patterns and structural observations',
    icon: '🏗️',
  },
  security: {
    label: 'Security',
    description: 'OWASP findings and overall grade',
    icon: '🔒',
  },
  dependencies: {
    label: 'Dependencies',
    description: 'Package health across ecosystems',
    icon: '📦',
  },
  update_plan: {
    label: 'Update Plan',
    description: 'Prioritized dependency updates with gains',
    icon: '⬆️',
  },
  recommendations: {
    label: 'Recommendations',
    description: 'Top actions ordered by impact',
    icon: '✅',
  },
  code_metrics: {
    label: 'Code Metrics',
    description: 'Lines of code, file sizes, and language breakdown',
    icon: '📊',
  },
  fun_facts: {
    label: 'Fun Facts',
    description: 'Curious observations about the project',
    icon: '💡',
  },
}

export const SECTION_ORDER: AnalysisSectionType[] = [
  'analysis_progress',
  'executive_summary',
  'tech_stack',
  'architecture',
  'security',
  'dependencies',
  'update_plan',
  'recommendations',
  'code_metrics',
  'fun_facts',
]

export const PRODUCT_SECTIONS: AnalysisSectionType[] = [
  'executive_summary',
  'fun_facts',
  'recommendations',
]

export const TECHNICAL_SECTIONS: AnalysisSectionType[] = [
  'tech_stack',
  'architecture',
  'security',
  'dependencies',
  'update_plan',
  'code_metrics',
]

export const SELECTABLE_SECTIONS = [
  'executive_summary',
  'tech_stack',
  'architecture',
  'security',
  'dependencies',
  'update_plan',
  'recommendations',
  'code_metrics',
  'fun_facts',
] as const satisfies AnalysisSectionType[]

export const RECOMMENDED_SECTIONS: AnalysisSectionType[] = [
  'executive_summary',
  'security',
  'architecture',
  'recommendations',
  'tech_stack',
  'fun_facts',
]
