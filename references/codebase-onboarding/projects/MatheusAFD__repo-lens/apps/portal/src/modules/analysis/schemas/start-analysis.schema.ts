import { z } from 'zod'

export const ALL_SECTION_TYPES = [
  'executive_summary',
  'tech_stack',
  'architecture',
  'security',
  'dependencies',
  'update_plan',
  'recommendations',
  'code_metrics',
  'fun_facts',
] as const

export const startAnalysisSchema = z.object({
  sections: z.array(z.enum(ALL_SECTION_TYPES)).min(1, 'Select at least one section'),
  customContext: z.string().max(500).optional(),
})

export type StartAnalysisFormRequest = z.infer<typeof startAnalysisSchema>
