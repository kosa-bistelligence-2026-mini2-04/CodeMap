from __future__ import annotations

import json
import logging
import os

from app.guardrail.judge_guardrail import JudgeGuardrail
from app.llm.provider import LLMProvider
from app.models.agent_schemas import ConflictResolution, BehaviorResult, StaticResult

logger = logging.getLogger(__name__)

_JUDGE_PROMPT_TEMPLATE = """[SYSTEM]
你是 RepoInsight 冲突消解 LLM 判官。某模块同时被 StaticAnalyzer 标记为高风险，并被 BehaviorInferer 识别为核心模块。请做风险-价值权衡，以中文 JSON 返回一份平衡的裁决。

[USER]
模块: {module}

StaticAnalyzer 视角:
{static_view}

BehaviorInferer 视角:
{behavior_view}

输出合法 JSON（禁止 ```json 包裹）:
{{
  "verdict": "refactor_priority" | "monitor" | "tolerate",
  "rationale": "<中文简短理由，≤80 字>",
  "action": "<中文下一步动作，≤30 字>",
  "final_recommendation": "<中文综合建议，2-4 句，结合复杂度风险与使用价值>",
  "confidence": <0.0-1.0 浮点数，你对本次裁决的信心>
}}

只返回 JSON 本身，不要任何前后缀。
"""


def _normalize_module(path: str) -> str:
    """Normalize a file path / labeled module name to a comparable stem.

    Handles the three formats that reach us:
    - Static: "utils.py", "src\\requests\\utils.py", "src/requests/utils.py"
    - Behavior (LLM output): "utils.py (core retry utility)", "src/utils (...)"
    - Raw module name: "utils"

    Returns the filename stem, lowercased for case-insensitive overlap detection.

    Examples:
        "src/requests/utils.py"            -> "utils"
        "utils.py"                         -> "utils"
        "utils.py (core retry)"            -> "utils"
        "src/requests/utils.py (role)"     -> "utils"
    """
    if not path:
        return ""
    # Strip trailing " (description)" suffix added by BehaviorInferer labels
    if " (" in path:
        path = path.split(" (", 1)[0]
    clean = path.replace("\\", "/").strip().lstrip("./")
    basename = clean.split("/")[-1] if "/" in clean else clean
    if basename.endswith(".py"):
        basename = basename[:-3]
    return basename.lower()


class ConflictResolver:
    """Detects module-level conflicts between StaticAnalyzer and BehaviorInferer, calls LLM judge."""

    PRIMARY_MODEL = "gpt-5.4-nano"
    ESCALATION_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.4")
    CONFIDENCE_THRESHOLD = 0.6

    def __init__(
        self,
        judge_guardrail: JudgeGuardrail | None = None,
        llm_provider: LLMProvider | None = None,
        observability=None,
    ) -> None:
        self.judge_guardrail = judge_guardrail or JudgeGuardrail()
        self.llm_provider = llm_provider
        self.observability = observability

    @staticmethod
    def detect_conflicts(static: StaticResult, behavior: BehaviorResult) -> list[str]:
        """Return normalized module paths present in both high-risk set and core_modules."""
        static_modules = {
            _normalize_module(f.file)
            for f in static.high_complexity_functions
            if f.risk_level.value in ("high", "critical")
        }
        behavior_modules = {_normalize_module(m) for m in behavior.core_modules}
        overlap = static_modules & behavior_modules
        return sorted(overlap)

    async def resolve(
        self, static: StaticResult, behavior: BehaviorResult
    ) -> list[ConflictResolution]:
        conflicts = self.detect_conflicts(static, behavior)
        if not conflicts:
            return []

        results: list[ConflictResolution] = []
        for module in conflicts:
            resolution = await self._resolve_one(module, static, behavior)
            results.append(resolution)
        return results

    async def _resolve_one(
        self, module: str, static: StaticResult, behavior: BehaviorResult
    ) -> ConflictResolution:
        static_funcs = [
            f for f in static.high_complexity_functions
            if _normalize_module(f.file) == module
        ]
        static_view = "; ".join(
            f"{f.name} CC={f.cc} risk={f.risk_level.value}" for f in static_funcs
        ) or f"module '{module}' flagged high complexity"

        behavior_modules_matching = [
            m for m in behavior.core_modules if _normalize_module(m) == module
        ]
        behavior_view = (
            f"Listed as core module: {', '.join(behavior_modules_matching)}"
            if behavior_modules_matching
            else f"module '{module}' in core_modules"
        )

        if self.llm_provider is None:
            return ConflictResolution(
                module=module,
                static_view=static_view,
                behavior_view=behavior_view,
                final_recommendation=(
                    f"Module '{module}' is both high-complexity and frequently used. "
                    "Consider refactoring incrementally while maintaining backward compatibility. "
                    "Add tests before refactoring to prevent regressions. Verdict: monitor."
                ),
                judge_model=self.PRIMARY_MODEL,
                escalated=False,
                confidence=0.5,
            )

        judge_source = f"{static_view}\n{behavior_view}"
        judge_prompt = _JUDGE_PROMPT_TEMPLATE.format(
            module=module,
            static_view=static_view,
            behavior_view=behavior_view,
        )

        # Primary judge: cheap model
        primary = await self._judge(module, judge_prompt, judge_source, model=self.PRIMARY_MODEL)

        if primary.confidence < self.CONFIDENCE_THRESHOLD:
            # Escalate to high-tier model for uncertain cases
            logger.info(
                "ConflictResolver escalating module='%s' confidence=%.2f < %.2f",
                module, primary.confidence, self.CONFIDENCE_THRESHOLD,
            )
            escalated = await self._judge(module, judge_prompt, judge_source, model=self.ESCALATION_MODEL)
            escalated.escalated = True
            escalated.judge_model = self.ESCALATION_MODEL
            escalated.static_view = static_view
            escalated.behavior_view = behavior_view
            return escalated

        primary.static_view = static_view
        primary.behavior_view = behavior_view
        return primary

    async def _judge(
        self,
        module: str,
        judge_prompt: str,
        judge_source: str,
        model: str,
    ) -> ConflictResolution:
        """Call LLM judge with the given model and return a ConflictResolution."""
        try:
            raw = await self.llm_provider.complete(
                judge_prompt,
                response_format={"type": "json_object"},
                temperature=0.0,
                model=model,
            )
            cleaned, telemetry, used_fallback = await self.judge_guardrail.validate_or_fallback(
                raw, judge_source
            )

            confidence = 0.5
            final_recommendation = ""

            if used_fallback or not cleaned.strip():
                final_recommendation = (
                    f"Module '{module}' conflict detected (guardrail fallback). "
                    "Verdict: monitor — review manually."
                )
                confidence = 0.5
            else:
                try:
                    parsed = json.loads(cleaned)
                    final_recommendation = str(
                        parsed.get("final_recommendation", "")
                        or parsed.get("verdict", "monitor")
                    )
                    raw_conf = parsed.get("confidence")
                    if isinstance(raw_conf, (int, float)):
                        confidence = max(0.0, min(1.0, float(raw_conf)))
                except (json.JSONDecodeError, ValueError):
                    final_recommendation = cleaned.strip()
                    confidence = 0.5

        except Exception as exc:
            logger.warning("ConflictResolver LLM call failed (model=%s): %s", model, exc)
            final_recommendation = (
                f"Module '{module}' conflict could not be resolved (LLM error). "
                "Verdict: monitor."
            )
            confidence = 0.5

        if self.observability is not None and hasattr(self.observability, "record_llm_call"):
            try:
                self.observability.record_llm_call(model=model, prompt_tokens=0, completion_tokens=0)
            except Exception as exc:
                logger.debug("observability.record_llm_call failed: %s", exc)

        return ConflictResolution(
            module=module,
            static_view="",
            behavior_view="",
            final_recommendation=final_recommendation,
            judge_model=model,
            escalated=False,
            confidence=confidence,
        )
