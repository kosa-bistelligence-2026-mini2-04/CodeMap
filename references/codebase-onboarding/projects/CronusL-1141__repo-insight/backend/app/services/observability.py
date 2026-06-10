from __future__ import annotations

import math
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.api_schemas import GuardrailTelemetry

# Per-model USD cost per 1K tokens (input, output). Sources:
#   OpenAI:   platform.openai.com/docs/models  (2026-04)
#   DeepSeek: api-docs.deepseek.com/quick_start/pricing (V3.2)
#   Zhipu:    bigmodel.cn/pricing
#   Moonshot: platform.kimi.ai/docs/pricing/chat
# Qwen prices vary by region/version; keep a neutral ballpark.
_MODEL_COST_PER_1K: dict[str, tuple[float, float]] = {
    # OpenAI
    "gpt-5.4":         (0.00250, 0.01500),
    "gpt-5.4-mini":    (0.00075, 0.00450),
    "gpt-5.4-nano":    (0.00020, 0.00125),
    # DeepSeek V3.2 (cache-miss rate)
    "deepseek-chat":      (0.00028, 0.00042),
    "deepseek-reasoner":  (0.00028, 0.00042),
    # Qwen (approximate, region-dependent)
    "qwen3-max":          (0.00250, 0.01000),
    "qwen3.5-plus":       (0.00080, 0.00200),
    "qwen3.5-flash":      (0.00030, 0.00060),
    "qwen-long-latest":   (0.00050, 0.00200),
    # Zhipu GLM
    "glm-5":              (0.00072, 0.00060),
    "glm-4.6":            (0.00039, 0.00174),
    "glm-4.5":            (0.00060, 0.00220),
    # Moonshot
    "kimi-k2.5":          (0.00060, 0.00300),
    "kimi-k2":            (0.00055, 0.00220),
    "moonshot-v1-128k":   (0.00060, 0.00240),
}
_DEFAULT_COST_PER_1K = (0.00250, 0.01500)


def _compute_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    input_rate, output_rate = _MODEL_COST_PER_1K.get(model, _DEFAULT_COST_PER_1K)
    return (prompt_tokens / 1000.0) * input_rate + (completion_tokens / 1000.0) * output_rate


class ObservabilityCollector:
    """Collects quality/performance/cost metrics and exposes Prometheus-format /metrics."""

    def __init__(self) -> None:
        self._pipeline_durations_ms: list[float] = []
        self._stage_durations: list[dict] = []
        self._guardrail_regex_hits: int = 0
        self._guardrail_semantic_hits: int = 0
        self._fallback_triggered_count: int = 0
        self._recommendation_count: int = 0
        self._llm_tokens_in: int = 0
        self._llm_tokens_out: int = 0
        self._llm_cost_usd: float = 0.0
        self._llm_cost_usd_by_model: dict[str, float] = defaultdict(float)
        self._cache_hits: int = 0
        self._cache_total: int = 0
        self._total_pipelines: int = 0

    def record_pipeline(
        self,
        job_id: str,
        duration_ms: int,
        stage_durations: dict,
        guardrail_telemetry: "GuardrailTelemetry | None" = None,
        recommendation_count: int = 0,
    ) -> None:
        self._total_pipelines += 1
        self._pipeline_durations_ms.append(float(duration_ms))
        self._stage_durations.append(stage_durations)
        self._recommendation_count += recommendation_count
        if guardrail_telemetry:
            self._guardrail_regex_hits += len(guardrail_telemetry.regex_blocked)
            self._guardrail_semantic_hits += len(guardrail_telemetry.semantic_filtered)
            if guardrail_telemetry.fallback_triggered:
                self._fallback_triggered_count += 1

    def record_llm_usage(
        self, tokens_in: int, tokens_out: int, cost_usd: float, cache_hit: bool
    ) -> None:
        self._llm_tokens_in += tokens_in
        self._llm_tokens_out += tokens_out
        self._llm_cost_usd += cost_usd
        self._cache_total += 1
        if cache_hit:
            self._cache_hits += 1

    def record_llm_call(
        self, model: str, prompt_tokens: int, completion_tokens: int, cache_hit: bool = False
    ) -> None:
        """Record a single LLM call with per-model cost breakdown."""
        cost = _compute_cost(model, prompt_tokens, completion_tokens)
        self._llm_tokens_in += prompt_tokens
        self._llm_tokens_out += completion_tokens
        self._llm_cost_usd += cost
        self._llm_cost_usd_by_model[model] += cost
        self._cache_total += 1
        if cache_hit:
            self._cache_hits += 1

    def _percentile(self, values: list[float], pct: float) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        idx = math.ceil(pct / 100.0 * len(sorted_vals)) - 1
        return sorted_vals[max(0, idx)]

    def compute_metrics(self) -> dict:
        durations_s = [d / 1000.0 for d in self._pipeline_durations_ms]
        total = self._total_pipelines or 1
        return {
            "pipeline_p50_s": self._percentile(durations_s, 50),
            "pipeline_p95_s": self._percentile(durations_s, 95),
            "pipeline_p99_s": self._percentile(durations_s, 99),
            "guardrail_regex_hit_rate": self._guardrail_regex_hits / total,
            "guardrail_semantic_hit_rate": self._guardrail_semantic_hits / total,
            "fallback_triggered_count": self._fallback_triggered_count,
            "recommendation_count_total": self._recommendation_count,
            "llm_tokens_in_total": self._llm_tokens_in,
            "llm_tokens_out_total": self._llm_tokens_out,
            "llm_cost_usd_total": self._llm_cost_usd,
            "cache_hit_rate": self._cache_hits / max(self._cache_total, 1),
            "total_pipelines": self._total_pipelines,
        }

    def prometheus_format(self) -> str:
        m = self.compute_metrics()
        durations_s = [d / 1000.0 for d in self._pipeline_durations_ms]
        buckets = [10.0, 30.0, 60.0, 90.0, 120.0]
        bucket_lines: list[str] = []
        for b in buckets:
            count = sum(1 for d in durations_s if d <= b)
            bucket_lines.append(
                f'repoinsight_pipeline_duration_seconds_bucket{{le="{b}"}} {count}'
            )
        bucket_lines.append(
            f'repoinsight_pipeline_duration_seconds_bucket{{le="+Inf"}} {len(durations_s)}'
        )
        bucket_lines.append(
            f"repoinsight_pipeline_duration_seconds_count {len(durations_s)}"
        )
        bucket_lines.append(
            f"repoinsight_pipeline_duration_seconds_sum {sum(durations_s):.3f}"
        )

        per_model_lines: list[str] = []
        if self._llm_cost_usd_by_model:
            per_model_lines.append("# HELP repoinsight_llm_cost_usd LLM cost in USD broken down by model")
            per_model_lines.append("# TYPE repoinsight_llm_cost_usd counter")
            for model_name, cost in sorted(self._llm_cost_usd_by_model.items()):
                per_model_lines.append(
                    f'repoinsight_llm_cost_usd{{model="{model_name}"}} {cost:.6f}'
                )
            per_model_lines.append("")

        lines = [
            "# HELP repoinsight_pipeline_duration_seconds Pipeline wall-clock duration",
            "# TYPE repoinsight_pipeline_duration_seconds histogram",
            *bucket_lines,
            "",
            "# HELP repoinsight_guardrail_regex_hits_total Total regex guardrail hits",
            "# TYPE repoinsight_guardrail_regex_hits_total counter",
            f"repoinsight_guardrail_regex_hits_total {self._guardrail_regex_hits}",
            "",
            "# HELP repoinsight_guardrail_semantic_hits_total Total semantic guardrail hits",
            "# TYPE repoinsight_guardrail_semantic_hits_total counter",
            f"repoinsight_guardrail_semantic_hits_total {self._guardrail_semantic_hits}",
            "",
            "# HELP repoinsight_fallback_triggered_total Times fallback was triggered",
            "# TYPE repoinsight_fallback_triggered_total counter",
            f"repoinsight_fallback_triggered_total {self._fallback_triggered_count}",
            "",
            "# HELP repoinsight_llm_cost_usd_total Total LLM cost in USD",
            "# TYPE repoinsight_llm_cost_usd_total counter",
            f"repoinsight_llm_cost_usd_total {self._llm_cost_usd:.6f}",
            "",
            *per_model_lines,
            "# HELP repoinsight_cache_hit_rate Cache hit rate [0,1]",
            "# TYPE repoinsight_cache_hit_rate gauge",
            f"repoinsight_cache_hit_rate {m['cache_hit_rate']:.4f}",
            "",
        ]
        return "\n".join(lines)
