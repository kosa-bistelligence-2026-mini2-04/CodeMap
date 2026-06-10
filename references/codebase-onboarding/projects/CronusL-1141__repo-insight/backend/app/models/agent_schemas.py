from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class FunctionRisk(BaseModel):
    file: str = Field(description="Relative file path from repo root")
    line: int = Field(ge=1, description="Starting line number of the function")
    name: str = Field(description="Fully qualified function name")
    cc: int = Field(ge=1, description="Cyclomatic complexity (radon)")
    risk_level: RiskLevel
    suggestion: str = Field(description="Actionable refactor suggestion")


class ModuleCoverage(BaseModel):
    path: str = Field(description="Relative module path")
    coverage_pct: float = Field(ge=0.0, le=100.0, description="Line coverage percentage")
    uncovered_lines: list[int] = Field(default_factory=list)


class LineRisk(BaseModel):
    line: int = Field(ge=1)
    risk_level: RiskLevel
    reason: str


class Recommendation(BaseModel):
    title: str
    detail: str
    affected_files: list[str] = Field(default_factory=list)
    priority: RiskLevel = RiskLevel.MEDIUM


class ConflictResolution(BaseModel):
    module: str = Field(description="Module path that triggered conflict")
    static_view: str = Field(description="StaticAnalyzer's risk assessment summary")
    behavior_view: str = Field(description="BehaviorInferer's usage frequency summary")
    final_recommendation: str = Field(
        description="LLM judge output: risk-value tradeoff recommendation"
    )
    judge_model: str = Field(default="gpt-5.4-nano", description="Model used for the final verdict")
    escalated: bool = Field(default=False, description="True if low confidence triggered escalation to higher-tier model")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0, description="Judge's self-reported confidence in the verdict")


# ---------------------------------------------------------------------------
# StaticAnalyzer
# ---------------------------------------------------------------------------

class StaticAnalyzerInput(BaseModel):
    repo_path: str = Field(description="Absolute local path to cloned repo")
    job_id: str
    timeout_seconds: int = Field(default=60, le=60)
    pylint_threshold: float = Field(
        default=7.0,
        description="Minimum pylint score; modules below this are flagged",
    )
    cc_threshold: int = Field(
        default=10,
        description="Cyclomatic complexity threshold for high-risk flag",
    )
    coverage_threshold: float = Field(
        default=70.0,
        description="Coverage percentage below which a module is flagged",
    )


class StaticResult(BaseModel):
    job_id: str
    high_complexity_functions: list[FunctionRisk]
    low_coverage_modules: list[ModuleCoverage]
    file_heatmap: dict[str, list[LineRisk]] = Field(
        description="Mapping from relative file path to list of line-level risks"
    )
    pylint_scores: dict[str, float] = Field(
        description="Mapping from module path to pylint score (0-10)"
    )
    total_files_scanned: int
    duration_ms: int


# ---------------------------------------------------------------------------
# BehaviorInferer
# ---------------------------------------------------------------------------

class BehaviorInfererInput(BaseModel):
    repo_path: str
    job_id: str
    timeout_seconds: int = Field(default=50, le=50)
    readme_path: str | None = Field(
        default=None,
        description="Override README path; auto-detected if None",
    )
    max_pr_count: int = Field(default=3, description="Number of recent PRs to fetch")
    llm_model: str = Field(default="gpt-5.4")
    source_url: str | None = Field(
        default=None,
        description="Original user-supplied URL or path; used as stable cache key dimension",
    )
    force_refresh: bool = Field(
        default=False,
        description="If True, bypass LLM cache and force a fresh call",
    )


class BehaviorResult(BaseModel):
    job_id: str
    usage_patterns: list[str] = Field(
        description="Inferred typical usage scenarios (natural language)"
    )
    core_modules: list[str] = Field(
        description="High-frequency call-path modules inferred from README/issues/PRs"
    )
    inference_evidence: dict[str, str] = Field(
        description="Mapping from claim to source snippet used as evidence (traceability)"
    )
    guardrail_passed: bool = Field(
        description="True if output passed both regex and semantic guardrail layers"
    )
    guardrail_warnings: list[str] = Field(
        default_factory=list,
        description="Warnings emitted by guardrail (non-blocking after rewrite)",
    )
    duration_ms: int


# ---------------------------------------------------------------------------
# CommunityAssessor
# ---------------------------------------------------------------------------

class CommunityAssessorInput(BaseModel):
    repo_path: str
    job_id: str
    timeout_seconds: int = Field(default=45, le=45)
    lookback_days: int = Field(default=30, description="Git log lookback window")
    github_token: str | None = Field(
        default=None,
        description="Optional GitHub token for issue API; sourced from env",
    )


class CommunityResult(BaseModel):
    job_id: str
    commits_per_week: float = Field(ge=0.0)
    avg_issue_response_hours: float | None = Field(
        default=None,
        description="None when GitHub issue API unavailable",
    )
    unique_contributors: int = Field(ge=0)
    top_contributors: list[str] = Field(
        default_factory=list,
        description="Top-5 contributor handles by commit count",
    )
    is_degraded: bool = Field(
        default=False,
        description="True when result is sourced from cache or historical average",
    )
    degraded_reason: str | None = Field(
        default=None,
        description="Human-readable explanation when is_degraded=True",
    )
    duration_ms: int
    llm_analysis: str | None = Field(
        default=None,
        description="LLM-generated Chinese interpretation of the community metrics",
    )


# ---------------------------------------------------------------------------
# Reporter
# ---------------------------------------------------------------------------

class ReporterInput(BaseModel):
    job_id: str
    repo_path: str
    static_result: StaticResult
    behavior_result: BehaviorResult
    community_result: CommunityResult
    timeout_seconds: int = Field(default=30, le=30)
    llm_model: str = Field(default="gpt-5.4")
    guardrail_telemetry: Any = Field(default=None, description="GuardrailTelemetry from Planner")
    agent_durations: dict[str, int] = Field(default_factory=dict)
    force_refresh: bool = Field(default=False, description="Bypass LLM cache for executive summary")


class ReportResult(BaseModel):
    job_id: str
    html_report: str = Field(description="Complete self-contained HTML with inline ECharts")
    recommendations: list[Recommendation] = Field(
        min_length=3,
        description="At least 3 actionable recommendations",
    )
    conflicts_resolved: list[ConflictResolution] = Field(
        default_factory=list,
        description="Non-empty when Static/Behavior module overlap detected",
    )
    duration_ms: int
    total_pipeline_ms: int = Field(
        description="Wall-clock time from job start to report completion"
    )
