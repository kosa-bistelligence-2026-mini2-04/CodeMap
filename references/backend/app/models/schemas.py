from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class ModelInfo(BaseModel):
    id: str
    label: str
    hint: str

class ProviderCatalog(BaseModel):
    provider: str
    base_url: Optional[str] = None
    default_model: str
    models: List[ModelInfo]

class AnalyzeRequest(BaseModel):
    source: str
    path: str
    force_refresh: Optional[bool] = False
    model: Optional[str] = None

class AnalyzeResponse(BaseModel):
    job_id: str
    status: str = "queued"
    created_at: str
    ws_url: str

class LineRisk(BaseModel):
    line: int
    risk_level: str
    reason: str
    metric: Optional[str] = None

class Recommendation(BaseModel):
    title: str
    detail: str
    affected_files: List[str]
    priority: str

class ConflictResolution(BaseModel):
    module: str
    static_view: str
    behavior_view: str
    final_recommendation: str
    judge_model: Optional[str] = None
    escalated: Optional[bool] = False
    confidence: Optional[float] = None

class CommunityMetrics(BaseModel):
    commits_per_week: float
    avg_issue_response_hours: Optional[float] = None
    unique_contributors: int
    top_contributors: List[str]
    is_degraded: bool
    degraded_reason: Optional[str] = None
    llm_analysis: Optional[str] = None

class GuardrailRegexBlock(BaseModel):
    original_text: str
    rule_id: str
    layer: str = "regex"

class GuardrailSemanticFilter(BaseModel):
    original_text: str
    similarity_score: float
    threshold: float

class GuardrailTelemetry(BaseModel):
    regex_blocked: List[GuardrailRegexBlock] = []
    semantic_filtered: List[GuardrailSemanticFilter] = []
    regenerate_count: int = 0
    fallback_triggered: bool = False
    input_secrets_redacted: Optional[int] = 0
    input_injections_blocked: Optional[int] = 0
    self_check_warnings: List[str] = []

class ReportJsonResponse(BaseModel):
    job_id: str
    status: str = "completed"
    completed_at: str
    total_pipeline_ms: int
    recommendations: List[Recommendation]
    conflicts_resolved: List[ConflictResolution]
    community: Optional[CommunityMetrics] = None
    html_report: Optional[str] = None
    file_heatmap: Optional[Dict[str, List[LineRisk]]] = None
    guardrail_telemetry: Optional[GuardrailTelemetry] = None
    agent_durations: Optional[Dict[str, int]] = None
    executive_summary: Optional[str] = None
    health_score: Optional[int] = None
    key_strengths: Optional[List[str]] = None
    key_risks: Optional[List[str]] = None
    summary_confidence: Optional[float] = None
