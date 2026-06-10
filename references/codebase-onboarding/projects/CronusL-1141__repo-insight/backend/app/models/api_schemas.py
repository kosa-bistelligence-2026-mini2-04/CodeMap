from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .agent_schemas import Recommendation, ConflictResolution, RiskLevel, StaticResult, BehaviorResult, CommunityResult


class GuardrailRegexBlock(BaseModel):
    original_text: str
    rule_id: str
    layer: Literal["regex"] = "regex"


class GuardrailSemanticFilter(BaseModel):
    original_text: str
    similarity_score: float
    threshold: float


class GuardrailTelemetry(BaseModel):
    regex_blocked: list[GuardrailRegexBlock] = Field(default_factory=list)
    semantic_filtered: list[GuardrailSemanticFilter] = Field(default_factory=list)
    regenerate_count: int = 0
    fallback_triggered: bool = False
    self_check_warnings: list[str] = Field(default_factory=list)
    emergency_mode: bool = False
    emergency_reason: str | None = None
    input_secrets_redacted: int = 0
    input_injections_blocked: int = 0

GITHUB_URL_RE = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+/?$")

# Accepts:
#   Unix absolute:       /home/user/project  /mnt/c/Users/...  (WSL mount)
#   Windows absolute:    C:\Users\...        C:/Users/...      D:\projects\...
# Rejects:
#   Relative paths:      ./foo  foo/bar  ..\up
#   Bare drive letters:  C:     (must have separator after colon)
LOCAL_ABS_PATH_RE = re.compile(r"^(?:/|[A-Za-z]:[/\\])")


# Union of models we support across providers. The per-request `model` override
# is validated against this superset. Which subset is actually usable depends on
# the configured OPENAI_BASE_URL (see app.services.provider_catalog).
_ALLOWED_MODELS = (
    # OpenAI GPT-5.4 family
    "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano",
    # DeepSeek V3.2
    "deepseek-chat", "deepseek-reasoner",
    # Qwen (Alibaba DashScope compatible mode) — Qwen3 series
    "qwen3-max", "qwen3.5-plus", "qwen3.5-flash", "qwen-long-latest",
    # Zhipu GLM — 4.5 / 4.6 / 5
    "glm-5", "glm-4.6", "glm-4.5",
    # Moonshot (Kimi)
    "kimi-k2.5", "kimi-k2", "moonshot-v1-128k",
)


class AnalyzeRequest(BaseModel):
    source: Literal["local", "github"] = Field(
        description="'local' for absolute path; 'github' for HTTPS URL"
    )
    path: str = Field(min_length=1, description="Local absolute path or GitHub repository URL")
    force_refresh: bool = Field(
        default=False,
        description="Bypass the LLM response cache and force a fresh LLM call (for demos)",
    )
    model: str | None = Field(
        default=None,
        description=(
            "Override the primary LLM model. Leave null to use the backend default "
            "(configured via OPENAI_MODEL env). Validated against the union allowlist."
        ),
    )

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        if v not in _ALLOWED_MODELS:
            raise ValueError(
                f"model must be one of {_ALLOWED_MODELS}, got {v!r}"
            )
        return v

    @field_validator("path")
    @classmethod
    def validate_path(cls, v: str, info) -> str:
        source = (info.data or {}).get("source")
        if source == "github" and not GITHUB_URL_RE.match(v):
            raise ValueError("github source requires https://github.com/<owner>/<repo>")
        if source == "local" and not LOCAL_ABS_PATH_RE.match(v):
            raise ValueError(
                "local source requires absolute path "
                "(Unix /path, Windows C:\\path, or WSL /mnt/c/path)"
            )
        return v


class AnalyzeResponse(BaseModel):
    job_id: str = Field(description="UUID4 task identifier")
    status: Literal["queued"] = "queued"
    created_at: datetime = Field(description="Task creation timestamp (UTC)")
    ws_url: str = Field(description="WebSocket progress URL")


class ErrorDetail(BaseModel):
    code: str
    message: str
    detail: Any = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class CommunityMetrics(BaseModel):
    commits_per_week: float
    avg_issue_response_hours: float | None = None
    unique_contributors: int
    top_contributors: list[str] = Field(default_factory=list)
    is_degraded: bool = False
    degraded_reason: str | None = None
    llm_analysis: str | None = None


class LineRiskHttp(BaseModel):
    line: int = Field(ge=1)
    risk_level: RiskLevel
    reason: str


class ReportJsonResponse(BaseModel):
    job_id: str
    status: Literal["completed"] = "completed"
    completed_at: datetime
    total_pipeline_ms: int
    recommendations: list[Recommendation]
    conflicts_resolved: list[ConflictResolution] = Field(default_factory=list)
    community: CommunityMetrics
    html_report: str | None = None
    file_heatmap: dict[str, list[LineRiskHttp]] | None = None
    guardrail_telemetry: GuardrailTelemetry | None = None
    agent_durations: dict[str, int] = Field(default_factory=dict)
    executive_summary: str | None = Field(
        default=None,
        description="LLM-generated natural-language summary of the analysis, Chinese, ≤200 chars",
    )
    health_score: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description="0-100 overall health score inferred by the LLM",
    )
    key_strengths: list[str] = Field(
        default_factory=list,
        description="Short strength bullets from the LLM summary",
    )
    key_risks: list[str] = Field(
        default_factory=list,
        description="Short risk bullets from the LLM summary",
    )
    summary_confidence: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="LLM self-reported confidence in the summary (0-1)",
    )


class PartialReporterInput(BaseModel):
    """Carries whatever partial results are available when a pipeline stage fails."""
    job_id: str
    static_result: StaticResult | None = None
    behavior_result: BehaviorResult | None = None
    community_result: CommunityResult | None = None
    guardrail_telemetry: GuardrailTelemetry | None = None
