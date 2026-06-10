export interface PaginationParams {
  page?: number
  limit?: number
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  limit: number
  totalPages: number
}

export type Result<T, E = Error> = [E, null] | [null, T]

export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface ApiErrorResponse {
  statusCode: number
  message: string | string[]
  error?: string
}

export type AnalysisStatus = 'running' | 'completed' | 'failed'

export type AnalysisSectionType =
  | 'executive_summary'
  | 'tech_stack'
  | 'architecture'
  | 'security'
  | 'dependencies'
  | 'update_plan'
  | 'recommendations'
  | 'code_metrics'
  | 'fun_facts'
  | 'analysis_progress'

export type SecurityGrade = 'A' | 'B' | 'C' | 'D' | 'F'
export type SeverityLevel = 'critical' | 'high' | 'medium' | 'low'
export type EffortLevel = 'low' | 'medium' | 'high'

export interface ExecutiveSummarySection {
  summary: string
  targetAudience: string
  keyCapabilities: string[]
}

export interface TechStackSection {
  languages: { name: string; percentage: number }[]
  frameworks: string[]
  databases: string[]
  cloud: string[]
  testing: string[]
}

export interface ArchitectureSection {
  pattern: string
  description: string
  keyPatterns: string[]
  observations: string[]
}

export interface SecurityFinding {
  severity: SeverityLevel
  description: string
  owasp: string
}

export interface SecuritySection {
  grade: SecurityGrade
  score: number
  findings: SecurityFinding[]
  positives: string[]
}

export interface DependencyEcosystem {
  name: string
  count: number
  outdated: number
  vulnerable: number
}

export interface DependencyHighlight {
  name: string
  version: string
  latestVersion: string
  status: 'ok' | 'outdated' | 'vulnerable'
}

export interface DependenciesSection {
  total: number
  ecosystems: DependencyEcosystem[]
  highlights: DependencyHighlight[]
}

export interface UpdateItem {
  name: string
  current: string
  target: string
  reason: string
  gain: string
}

export interface UpdatePlanSection {
  critical: UpdateItem[]
  major: UpdateItem[]
  minor: UpdateItem[]
}

export interface RecommendationItem {
  rank: number
  title: string
  effort: EffortLevel
  impact: EffortLevel
  rationale: string
}

export interface RecommendationsSection {
  items: RecommendationItem[]
}

export interface CodeMetricsSection {
  totalFiles: number
  estimatedLines: number
  byLanguage: { name: string; lines: number; percentage: number }[]
  largestFiles: { path: string; lines: number }[]
}

export interface FunFactsSection {
  facts: string[]
  codeAge?: string
}

export interface ProgressItem {
  title: string
  status: 'fixed' | 'improved' | 'new_issue'
  description: string
}

export interface AnalysisProgressSection {
  scoreChange: number
  gradeChange: string | null
  fixedIssues: ProgressItem[]
  newIssues: ProgressItem[]
  summary: string
}

export interface QuestionAnswer {
  id: string
  question: string
  answer: string | null
  createdAt: string
}

export interface StartAnalysisRequest {
  sections: AnalysisSectionType[]
  customContext?: string
}

export interface AskQuestionRequest {
  question: string
}

export interface AnalysisResult {
  executive_summary?: ExecutiveSummarySection
  tech_stack?: TechStackSection
  architecture?: ArchitectureSection
  security?: SecuritySection
  dependencies?: DependenciesSection
  update_plan?: UpdatePlanSection
  recommendations?: RecommendationsSection
  code_metrics?: CodeMetricsSection
  fun_facts?: FunFactsSection
  analysis_progress?: AnalysisProgressSection
}

export type SseEvent =
  | { type: 'section'; name: AnalysisSectionType; data: unknown }
  | { type: 'progress'; message: string }
  | { type: 'done'; analysisId: string }
  | { type: 'error'; message: string }

export type ChatMessageRole = 'user' | 'assistant' | 'system'
export type ChatMessageStatus = 'streaming' | 'complete' | 'failed'

export interface Chat {
  id: string
  repositoryId: string
  userId: string
  title: string
  lastMessageAt: string
  createdAt: string
  updatedAt: string
}

export interface ChatMessage {
  id: string
  chatId: string
  role: ChatMessageRole
  content: string
  status: ChatMessageStatus
  errorMessage?: string | null
  inputTokens?: number | null
  outputTokens?: number | null
  createdAt: string
}

export interface CreateChatRequest {
  title?: string
}

export interface RenameChatRequest {
  title: string
}

export interface SendMessageRequest {
  content: string
}

export interface CodeArea {
  id: string
  label: string
  description?: string
}

export type SuggestionAxis = 'area' | 'lens' | 'combined'

export interface PromptSuggestion {
  id: string
  label: string
  prompt: string
  axis: SuggestionAxis
  areaId?: string
  lensId?: AnalysisSectionType
}

export interface SuggestionLens {
  id: AnalysisSectionType
  label: string
}

export interface PromptSuggestionsResponse {
  areas: CodeArea[]
  lenses: SuggestionLens[]
  suggestions: PromptSuggestion[]
}

export type ChatSseEvent =
  | { type: 'message_start'; messageId: string }
  | { type: 'delta'; text: string }
  | { type: 'done'; messageId: string; inputTokens: number; outputTokens: number }
  | { type: 'error'; message: string }
