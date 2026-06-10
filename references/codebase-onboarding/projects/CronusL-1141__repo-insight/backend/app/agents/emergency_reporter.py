from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Literal

from app.models.agent_schemas import Recommendation, RiskLevel
from app.models.api_schemas import (
    CommunityMetrics,
    GuardrailTelemetry,
    PartialReporterInput,
    ReportJsonResponse,
)

EmergencyReason = Literal[
    "reporter_timeout",
    "reporter_failed",
    "behavior_inferer_failed",
    "static_analyzer_failed",
    "planner_budget_exhausted",
]

_REASON_LABELS: dict[str, str] = {
    "reporter_timeout": "Reporter 超时",
    "reporter_failed": "Reporter 内部错误",
    "behavior_inferer_failed": "行为推断 Agent 失败",
    "static_analyzer_failed": "静态分析 Agent 失败",
    "planner_budget_exhausted": "Pipeline 总预算耗尽",
}


def _emergency_html(job_id: str, reason: str, reason_label: str, recs_html: str, community_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>RepoInsight Report (Degraded) — {job_id}</title>
<style>
body{{font-family:sans-serif;max-width:900px;margin:0 auto;padding:1rem}}
.card{{background:#f8f9fa;border-radius:8px;padding:1rem;margin-bottom:1rem}}
.emergency-banner{{background:#f8d7da;border:1px solid #f5c2c7;color:#842029;border-radius:6px;padding:.75rem 1rem;font-weight:bold;margin-bottom:1rem}}
ul{{padding-left:1.2rem}}
</style>
</head>
<body>
<div class="emergency-banner">&#9888; 降级模式: {reason_label} (reason={reason})</div>
<h1>RepoInsight Analysis Report</h1>
<div class="card">
  <h2>Summary</h2>
  <p>Job ID: <code>{job_id}</code></p>
  <p>Status: <strong>degraded</strong></p>
</div>
<div class="card">
  <h2>Top Recommendations (partial)</h2>
  <ol>{recs_html}</ol>
</div>
{community_html}
</body>
</html>"""


class EmergencyReporter:
    """Produces a degraded report from whatever partial pipeline results are available."""

    async def render(
        self,
        partial: PartialReporterInput,
        reason: EmergencyReason,
    ) -> ReportJsonResponse:
        t_start = time.monotonic()

        reason_label = _REASON_LABELS.get(reason, reason)

        recommendations: list[Recommendation] = []
        if partial.static_result is not None:
            from app.agents.reporter import _build_recommendations
            if partial.static_result.high_complexity_functions:
                fake_behavior_core: list[str] = []
                if partial.behavior_result is not None:
                    fake_behavior_core = partial.behavior_result.core_modules
                from app.models.agent_schemas import BehaviorResult
                stub_behavior = BehaviorResult(
                    job_id=partial.job_id,
                    usage_patterns=[],
                    core_modules=fake_behavior_core,
                    inference_evidence={},
                    guardrail_passed=True,
                    duration_ms=0,
                )
                recommendations = _build_recommendations(partial.static_result, stub_behavior)

        community_metrics: CommunityMetrics | None = None
        if partial.community_result is not None:
            cr = partial.community_result
            community_metrics = CommunityMetrics(
                commits_per_week=cr.commits_per_week,
                avg_issue_response_hours=cr.avg_issue_response_hours,
                unique_contributors=cr.unique_contributors,
                top_contributors=cr.top_contributors,
                is_degraded=cr.is_degraded,
                degraded_reason=cr.degraded_reason,
            )
        else:
            community_metrics = CommunityMetrics(
                commits_per_week=0.0,
                unique_contributors=0,
                is_degraded=True,
                degraded_reason="数据不可用（pipeline 降级）",
            )

        recs_html = "".join(
            f'<li><strong>[{r.priority.value.upper()}]</strong> {r.title}<br><em>{r.detail}</em></li>'
            for r in recommendations
        ) or "<li>无可用建议（分析数据不完整）</li>"

        community_html = ""
        if community_metrics:
            degraded_note = (
                f'<p style="color:#856404">社区数据降级: {community_metrics.degraded_reason}</p>'
                if community_metrics.is_degraded
                else ""
            )
            community_html = f"""<div class="card">
  <h2>Community Health</h2>
  {degraded_note}
  <ul>
    <li>Commits/week: {community_metrics.commits_per_week:.1f}</li>
    <li>Unique contributors: {community_metrics.unique_contributors}</li>
    <li>Avg issue response: {community_metrics.avg_issue_response_hours or 'N/A'}</li>
  </ul>
</div>"""

        render_ms = int((time.monotonic() - t_start) * 1000)

        html_report = _emergency_html(
            job_id=partial.job_id,
            reason=reason,
            reason_label=reason_label,
            recs_html=recs_html,
            community_html=community_html,
        )

        telemetry = partial.guardrail_telemetry or GuardrailTelemetry()
        telemetry.emergency_mode = True
        telemetry.emergency_reason = reason

        return ReportJsonResponse(
            job_id=partial.job_id,
            status="completed",
            completed_at=datetime.now(timezone.utc),
            total_pipeline_ms=render_ms,
            recommendations=recommendations,
            conflicts_resolved=[],
            community=community_metrics,
            html_report=html_report,
            file_heatmap=None,
            guardrail_telemetry=telemetry,
        )
