# ADR-002: Agent 通信协议与 Planner 编排

**状态**: Accepted  
**日期**: 2026-04-12  
**作者**: backend-arch  
**关联**: ADR-001（技术栈与模块划分）

---

## 1. 背景与问题

RepoInsight 使用 4 个独立 Agent 并行分析代码仓库，需要一套明确的 I/O 契约、编排协议和降级策略，以保证：

- 120s 总预算内完成分析
- 单 Agent 失败不阻断整体流程
- StaticAnalyzer 与 BehaviorInferer 结论冲突时产出有价值的平衡建议

---

## 2. 决策

### 2.1 Agent I/O Pydantic Schema

所有 Schema 定义于 `backend/app/models/`，Pydantic v2。

```python
# backend/app/models/agent_schemas.py

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
```

---

### 2.2 Planner 编排时序

#### 2.2.1 总体伪代码

```python
# backend/app/orchestrator/planner.py  (pseudocode)

BUDGET_TOTAL_S       = 120
BUDGET_STATIC_S      = 60
BUDGET_BEHAVIOR_S    = 50
BUDGET_COMMUNITY_S   = 45
BUDGET_REPORTER_S    = 30

async def run_pipeline(job_id: str, repo_path: str) -> ReportResult:
    t_start = time.monotonic()

    # Phase 1: parallel execution of the three analysis agents
    static_task    = asyncio.create_task(run_static(job_id, repo_path, BUDGET_STATIC_S))
    behavior_task  = asyncio.create_task(run_behavior(job_id, repo_path, BUDGET_BEHAVIOR_S))
    community_task = asyncio.create_task(run_community(job_id, repo_path, BUDGET_COMMUNITY_S))

    results = await asyncio.gather(
        static_task,
        behavior_task,
        community_task,
        return_exceptions=True,
    )

    static_result    = _unwrap_or_raise(results[0], "StaticAnalyzer")
    behavior_result  = _unwrap_or_raise(results[1], "BehaviorInferer")
    community_result = _handle_community(results[2], job_id)  # degradation handled here

    # Phase 2: conflict detection before Reporter
    conflicts = detect_conflicts(static_result, behavior_result)
    if conflicts:
        await ws_broadcast(job_id, {"type": "conflict_detected", "modules": conflicts})

    # Phase 3: Reporter (sequential, depends on Phase 1+2)
    elapsed = time.monotonic() - t_start
    reporter_budget = min(BUDGET_REPORTER_S, BUDGET_TOTAL_S - elapsed - 2)
    report = await run_reporter(
        job_id, repo_path,
        static_result, behavior_result, community_result,
        timeout=reporter_budget,
    )
    return report


async def run_community(job_id: str, repo_path: str, budget: int) -> CommunityResult:
    try:
        return await asyncio.wait_for(
            _community_assessor.run(CommunityAssessorInput(...)),
            timeout=budget,
        )
    except asyncio.TimeoutError:
        return await _timeout_guard.get_degraded_community(job_id, repo_path)
```

#### 2.2.2 超时时序表

| Agent | 独立预算 | 触发时机 |
|---|---|---|
| StaticAnalyzer | 60s | 并行启动，t=0 |
| BehaviorInferer | 50s | 并行启动，t=0 |
| CommunityAssessor | 45s | 并行启动，t=0；超时触发降级 |
| Reporter | 30s（或剩余预算） | Phase 1 全部完成后启动 |
| 总预算 | 120s | 超出整体抛出 PipelineTimeoutError |

---

### 2.3 冲突消解协议

#### 触发条件

```python
def detect_conflicts(
    static: StaticResult,
    behavior: BehaviorResult,
) -> list[str]:
    """Return module paths present in both high-risk set and core_modules."""
    high_risk_modules = {
        f.file.split("/")[0]          # top-level module
        for f in static.high_complexity_functions
        if f.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)
    }
    core_set = set(behavior.core_modules)
    return list(high_risk_modules & core_set)
```

#### 协商流程

```
StaticResult (high_risk_modules) ─┐
                                   ├─► ConflictResolver.resolve()
BehaviorResult (core_modules)    ─┘         │
                                             ▼
                              LLM Judge (gpt-5.4)
                              Prompt: "Module X has CC={cc}, coverage={cov}%
                                       AND is called in {n} core usage patterns.
                                       Provide a risk-value tradeoff recommendation."
                                             │
                                             ▼
                              ConflictResolution { module, static_view,
                                                   behavior_view,
                                                   final_recommendation }
```

实现文件: `backend/app/orchestrator/conflict_resolver.py`

#### ConflictResolution 数据结构（见 §2.1）

- `module`: 触发冲突的模块路径
- `static_view`: StaticAnalyzer 风险摘要（CC 值、覆盖率、pylint 分）
- `behavior_view`: BehaviorInferer 使用频率摘要（出现于几个 usage_pattern）
- `final_recommendation`: LLM judge 产出的平衡建议文本

---

### 2.4 超时降级策略

实现文件: `backend/app/orchestrator/timeout_guard.py`

```
CommunityAssessor 超 45s
        │
        ├─► 查询 SQLite 缓存 (repo_hash + "community_assessor", 24h TTL)
        │       │
        │       ├── 命中 → 返回缓存结果，设 is_degraded=True,
        │       │           degraded_reason="cache_hit_within_24h"
        │       │
        │       └── 未命中 → 返回历史均值
        │                   {
        │                     commits_per_week: 3.5,
        │                     avg_issue_response_hours: 48.0,
        │                     unique_contributors: 5,
        │                     is_degraded: True,
        │                     degraded_reason: "timeout_fallback_historical_average"
        │                   }
        │
        └─► WebSocket 推送:
            {"type": "degraded", "agent": "community_assessor",
             "reason": "exceeded 45s budget"}
```

报告中展示提示（Reporter 负责渲染）:
> "社区数据暂不可用，采用历史均值估算（commits_per_week ≈ 3.5）"

---

## 3. 备选方案

| 方案 | 描述 | 放弃原因 |
|---|---|---|
| 顺序执行 | 三个 Agent 依次运行 | 总耗时 > 120s |
| 消息队列（Celery） | 基于任务队列异步编排 | 引入 broker 依赖，超出当前复杂度预算 |
| 无冲突消解 | 直接合并 Static+Behavior 输出 | 场景：utils.py 高风险但高频调用，忽视会产生误导建议 |

---

## 4. 影响

- `backend/app/models/agent_schemas.py` — 新建，所有 Schema 单一来源
- `backend/app/orchestrator/planner.py` — 实现 §2.2 编排逻辑
- `backend/app/orchestrator/conflict_resolver.py` — 实现 §2.3 协商
- `backend/app/orchestrator/timeout_guard.py` — 实现 §2.4 降级
- 前端 TypeScript 类型需与本 Schema 对齐（见 API-CONTRACT.md）
