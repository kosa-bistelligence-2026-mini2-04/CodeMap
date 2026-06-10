from __future__ import annotations

from app.guardrail.regex_validator import RegexValidator, _Rule, ABSOLUTE
from app.guardrail.validator import GuardrailValidator
from app.models.api_schemas import GuardrailTelemetry


class JudgeRegexValidator(RegexValidator):
    """Regex validator for judge context: skips FUTURE_TENSE, keeps ABSOLUTE."""

    def __init__(self) -> None:
        super().__init__(rules=[_Rule("absolute", ABSOLUTE)])


class JudgeGuardrail(GuardrailValidator):
    """
    GuardrailValidator subclass for the LLM judge in ConflictResolver.

    Differences from base:
    - Skips FUTURE_TENSE regex (judge may reasonably reference past timelines)
    - Keeps ABSOLUTE regex (guards against overconfident judge verdicts)
    - On validation failure, returns fallback verdict=monitor instead of re-generating
    """

    def __init__(self) -> None:
        super().__init__(regex_validator=JudgeRegexValidator())

    async def validate_or_fallback(
        self, raw_output: str, source_text: str
    ) -> tuple[str, GuardrailTelemetry, bool]:
        """
        Returns (cleaned_text, telemetry, used_fallback).
        If cleaning removes everything, used_fallback=True.
        """
        cleaned, telemetry = await self.validate(raw_output, source_text)
        used_fallback = False
        if not cleaned.strip() and raw_output.strip():
            used_fallback = True
            cleaned = raw_output
            telemetry = GuardrailTelemetry(
                regex_blocked=telemetry.regex_blocked,
                semantic_filtered=telemetry.semantic_filtered,
                regenerate_count=0,
                fallback_triggered=True,
            )
        return cleaned, telemetry, used_fallback
