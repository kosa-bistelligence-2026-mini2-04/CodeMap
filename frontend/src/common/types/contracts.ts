// Mirrors backend Pydantic v2 schemas.
// Field names stay snake_case to avoid a serialization translation layer.

export type AgentName =
  | 'static_analyzer'
  | 'behavior_inferer'
  | 'community_assessor'
  | 'reporter';

export type AgentStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'degraded';

export type Severity = 'low' | 'medium' | 'high' | 'critical';

export type Effort = 'S' | 'M' | 'L';

export type Priority = 'critical' | 'high' | 'medium' | 'low';

export interface AgentRuntimeStatus {
  name: AgentName;
  status: AgentStatus;
  progress: number;
  message?: string;
  stage_label?: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
}

export interface LineRisk {
  line: number;
  risk_level: Severity;
  reason: string;
  metric?: 'complexity' | 'coverage' | 'maintainability';
}

export type FileHeatmap = Record<string, LineRisk[]>;

export interface Recommendation {
  title: string;
  detail: string;
  affected_files: string[];
  priority: Priority;
}

export interface ConflictResolution {
  module: string;
  static_view: string;
  behavior_view: string;
  final_recommendation: string;
  judge_model?: string;
  escalated?: boolean;
  confidence?: number;
}

export interface CommunityMetrics {
  commits_per_week: number;
  avg_issue_response_hours: number | null;
  unique_contributors: number;
  top_contributors: string[];
  is_degraded: boolean;
  degraded_reason: string | null;
  llm_analysis?: string | null;
}

export type LlmModel = string;

export interface ModelInfo {
  id: string;
  label: string;
  hint: string;
}

export interface ProviderCatalog {
  provider: 'openai' | 'deepseek' | 'qwen' | 'zhipu' | 'moonshot' | 'custom';
  base_url: string | null;
  default_model: string;
  models: ModelInfo[];
}

export interface AnalyzeRequest {
  repoUrl: string;
  branch?: string;
  model?: string;
  forceRefresh?: boolean;
}

export interface AnalysisData {
  jobId: string;
  repoName: string;
  owner: string;
  branch: string;
  status: string;
  createdAt: string;
  model?: string;
}

export interface WorkspaceFile {
  path: string;
  name: string;
  language: string;
  lines: number;
  size: number;
  kind: 'source' | 'test';
}

export interface WorkspaceReport {
  job_id?: string;
  status?: 'completed';
  completed_at?: string;
  model_used?: string;
  repository: { name: string; root?: string };
  stats: {
    files: number;
    lines: number;
    bytes: number;
    tests: number;
    todos: number;
    primary_language: string;
  };
  languages: Array<{ name: string; lines: number }>;
  stack: string[];
  entrypoints: string[];
  files: WorkspaceFile[];
  health_score: number;
  executive_summary: string;
  key_strengths: string[];
  key_risks: string[];
  recommendations: Recommendation[];
  conflicts_resolved: ConflictResolution[];
  reading_order?: string[];
  onboarding_steps?: Array<{ title: string; files: string[] }>;
}

export interface JobStatusData {
  jobId: string;
  repoName: string;
  owner: string;
  repoUrl: string;
  branch: string;
  clonePath: string;
  status: 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
  stage?: string | null;
  progress: number;
  statusMessage?: string | null;
  model: string;
  report?: WorkspaceReport | null;
  createdAt: string;
  updatedAt: string;
}

export interface AnalyzeResponse {
  code: number;
  message: string;
  data: AnalysisData;
}

export type AnalysisHistoryStatus = 'queued' | 'running' | 'completed' | 'failed';

export interface AnalysisHistoryJob {
  jobId: string;
  repoUrl: string;
  branch: string;
  status: AnalysisHistoryStatus;
  progress: number;
  failedAgent: string | null;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface AnalysisHistoryData {
  totalCount: number;
  page: number;
  limit: number;
  jobs: AnalysisHistoryJob[];
}

export interface AnalysisHistoryResponse {
  code: number;
  message: string;
  data: AnalysisHistoryData;
}

export interface GuardrailRegexBlock {
  original_text: string;
  rule_id: string;
  layer: 'regex';
}

export interface GuardrailSemanticFilter {
  original_text: string;
  similarity_score: number;
  threshold: number;
}

export interface GuardrailTelemetry {
  regex_blocked: GuardrailRegexBlock[];
  semantic_filtered: GuardrailSemanticFilter[];
  regenerate_count: number;
  fallback_triggered: boolean;
  input_secrets_redacted?: number;
  input_injections_blocked?: number;
  self_check_warnings: string[];
  emergency_mode: boolean;
  emergency_reason: string | null;
}

export interface ReportJsonResponse {
  job_id: string;
  status: 'completed';
  completed_at: string;
  total_pipeline_ms: number;
  recommendations: Recommendation[];
  conflicts_resolved: ConflictResolution[];
  community?: CommunityMetrics;
  html_report?: string | null;
  file_heatmap?: FileHeatmap | null;
  guardrail_telemetry?: GuardrailTelemetry | null;
  agent_durations?: Record<string, number>;
  executive_summary?: string | null;
  health_score?: number | null;
  key_strengths?: string[];
  key_risks?: string[];
  summary_confidence?: number | null;
}

export interface JobProgressResponse {
  job_id: string;
  status: 'running' | 'queued';
  progress: Record<AgentName, AgentStatus>;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
    detail?: unknown;
  };
}

// WebSocket events
export type WsEventType =
  | 'agent_status'
  | 'agent_completed'
  | 'conflict_detected'
  | 'degraded'
  | 'completed'
  | 'failed'
  | 'error';

export interface WsBaseEvent {
  type: WsEventType;
  job_id: string;
  timestamp: string;
}

export interface WsAgentStatusEvent extends WsBaseEvent {
  type: 'agent_status';
  agent: AgentName;
  status: AgentStatus;
  progress: number;
  stage_label?: string;
}

export interface WsAgentCompletedEvent extends WsBaseEvent {
  type: 'agent_completed';
  agent: AgentName;
  duration_ms: number;
  summary: string;
}

export interface WsConflictDetectedEvent extends WsBaseEvent {
  type: 'conflict_detected';
  modules: string[];
  count: number;
}

export interface WsDegradedEvent extends WsBaseEvent {
  type: 'degraded';
  agent: AgentName;
  reason: string;
  fallback: 'cache' | 'historical_average';
}

export interface WsCompletedEvent extends WsBaseEvent {
  type: 'completed';
  report_url: string;
  total_duration_ms: number;
}

export interface WsFailedEvent extends WsBaseEvent {
  type: 'failed';
  error_code: string;
  message: string;
}

export interface WsErrorEvent extends WsBaseEvent {
  type: 'error';
  code: string;
  message?: string;
}

export type WsEvent =
  | WsAgentStatusEvent
  | WsAgentCompletedEvent
  | WsConflictDetectedEvent
  | WsDegradedEvent
  | WsCompletedEvent
  | WsFailedEvent
  | WsErrorEvent;

// ── Chat types ──────────────────────────────────────────────────────────────

export type ChatMode = 'quick' | 'deep';

export type StreamPhase =
  | 'searching'
  | 'building_context'
  | 'generating'
  | 'complete';

export interface CodeReference {
  file: string;
  line: number;
  snippet: string;
  language: string;
}


// ── Pre-clone validation types ────────────────────────────────────────────────
export interface PreValidateRequest {
  repoUrl: string;
  branch?: string;
}

export interface PreValidateData {
  isValid: boolean;
  fileCount: number;
  totalSizeKb: number;
  warningMessage: string | null;
  isTruncated: boolean;
}

export interface PreValidateResponse {
  code: number;
  message: string;
  data: PreValidateData;
}

