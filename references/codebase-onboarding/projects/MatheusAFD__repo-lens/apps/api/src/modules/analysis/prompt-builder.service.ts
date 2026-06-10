import { Injectable } from '@nestjs/common'
import type { AnalysisResult, AnalysisSectionType } from '@repo/shared'

interface RepoMeta {
  owner: string
  name: string
  description?: string | null
  language?: string | null
}

interface FileContext {
  path: string
  content: string
}

const SECTION_SHAPES: Record<AnalysisSectionType, string> = {
  executive_summary: `executive_summary: {"summary": string, "targetAudience": string, "keyCapabilities": string[]}`,
  tech_stack: `tech_stack: {"languages": [{"name": string, "percentage": number}], "frameworks": string[], "databases": string[], "cloud": string[], "testing": string[]}`,
  architecture: `architecture: {"pattern": string, "description": string, "keyPatterns": string[], "observations": string[]}`,
  security: `security: {"grade": "A"|"B"|"C"|"D"|"F", "score": number, "findings": [{"severity": "critical"|"high"|"medium"|"low", "description": string, "owasp": string}], "positives": string[]}`,
  dependencies: `dependencies: {"total": number, "ecosystems": [{"name": string, "count": number, "outdated": number, "vulnerable": number}], "highlights": [{"name": string, "version": string, "latestVersion": string, "status": "ok"|"outdated"|"vulnerable"}]}`,
  update_plan: `update_plan: {"critical": [{"name": string, "current": string, "target": string, "reason": string, "gain": string}], "major": [], "minor": []}`,
  recommendations: `recommendations: {"items": [{"rank": number, "title": string, "effort": "low"|"medium"|"high", "impact": "low"|"medium"|"high", "rationale": string}]}`,
  code_metrics: `code_metrics: {"totalFiles": number, "estimatedLines": number, "byLanguage": [{"name": string, "lines": number, "percentage": number}], "largestFiles": [{"path": string, "lines": number}]}`,
  fun_facts: `fun_facts: {"facts": string[], "codeAge": string | null}`,
  analysis_progress: `analysis_progress: {"scoreChange": number, "gradeChange": string | null, "fixedIssues": [{"title": string, "status": "fixed"|"improved", "description": string}], "newIssues": [{"title": string, "status": "new_issue", "description": string}], "summary": string}`,
}

const SECTION_RULES: Partial<Record<AnalysisSectionType, string>> = {
  executive_summary: 'Use plain language for executive_summary (non-technical audience).',
  security: 'Security: focus on OWASP Top 10. If no issues found, grade A.',
  recommendations: 'Recommendations: exactly 7 items ordered by impact descending.',
  fun_facts:
    'fun_facts: provide 5–7 interesting curiosities about the project. codeAge is a rough estimate (e.g. "~2 years old") or null if unknown.',
  code_metrics:
    'code_metrics: estimate lines of code based on file sizes and structure seen in the context. largestFiles: top 5 files by estimated line count.',
  analysis_progress:
    'analysis_progress: compare this analysis with the PREVIOUS ANALYSIS in the user message. scoreChange is the security score delta (positive = improvement, negative = regression). gradeChange is e.g. "C → B" or null if unchanged. fixedIssues are problems from the previous analysis that are now resolved or improved. newIssues are problems that did not exist before. summary is 1-2 sentences describing the overall evolution.',
}

const SECTION_ORDER: AnalysisSectionType[] = [
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

@Injectable()
export class PromptBuilderService {
  buildSystemPrompt(sections: AnalysisSectionType[], hasPreviousAnalysis: boolean): string {
    const orderedSections = SECTION_ORDER.filter((s) => sections.includes(s))
    const sectionList = orderedSections.map((s, i) => `${i + 1}. ${s}`).join('\n')
    const shapes = orderedSections.map((s) => SECTION_SHAPES[s]).join('\n\n')
    const rules = orderedSections
      .filter((s) => SECTION_RULES[s])
      .map((s) => `- ${SECTION_RULES[s]}`)
      .join('\n')

    const previousAnalysisInstructions = hasPreviousAnalysis
      ? `
Previous analysis context:
- A previous analysis result is included in the user message under "PREVIOUS ANALYSIS".
- The user has applied fixes since that analysis. Take this into account.
- Where issues from the previous analysis have been resolved, reflect that improvement in scores and findings.
- Do NOT penalize the same resolved issue twice. If a finding no longer exists in the current code, remove it.
- Acknowledge progress: if the security score improved, it should be reflected in a higher score/grade.`
      : ''

    return `You are a senior software architect and security engineer performing a structured code repository analysis.

Analyze the provided repository context and respond with exactly ${orderedSections.length} JSON section(s).
Each section is delimited by ##BEGIN_SECTION:{section_name}## and ##END_SECTION:{section_name}##.

Sections in order:
${sectionList}

JSON shapes per section:

${shapes}

Rules:
- Be concise. Target 150-300 words per section.
${rules}
- Output ONLY the section markers and JSON. No preamble, no postamble, no markdown fences.${previousAnalysisInstructions}`
  }

  buildUserPrompt(
    meta: RepoMeta,
    files: FileContext[],
    customContext?: string,
    previousAnalysis?: Partial<AnalysisResult>,
  ): string {
    const lines: string[] = [
      `Repository: ${meta.owner}/${meta.name}`,
      `Primary Language: ${meta.language ?? 'Unknown'}`,
      `Description: ${meta.description ?? 'No description provided'}`,
    ]

    if (customContext) {
      lines.push('')
      lines.push(`Additional context from the user: ${customContext}`)
    }

    if (previousAnalysis) {
      lines.push('')
      lines.push('PREVIOUS ANALYSIS (for comparison — user has applied fixes since this):')
      lines.push(JSON.stringify(previousAnalysis, null, 2).slice(0, 6000))
    }

    lines.push('')

    for (const file of files) {
      lines.push(`=== ${file.path} ===`)
      lines.push(file.content)
      lines.push('')
    }

    return lines.join('\n')
  }
}
