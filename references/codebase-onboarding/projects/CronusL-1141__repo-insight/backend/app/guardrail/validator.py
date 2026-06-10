from __future__ import annotations

import logging

from app.models.api_schemas import (
    GuardrailRegexBlock,
    GuardrailSemanticFilter,
    GuardrailTelemetry,
)

from .regex_validator import RegexValidator
from .semantic_validator import SemanticValidator

logger = logging.getLogger(__name__)


class GuardrailValidator:
    """Unified two-layer filter. Returns (cleaned_text, telemetry)."""

    def __init__(
        self,
        regex_validator: RegexValidator | None = None,
        semantic_validator: SemanticValidator | None = None,
    ) -> None:
        self.regex_validator = regex_validator or RegexValidator()
        self.semantic_validator = semantic_validator or SemanticValidator()

    async def validate(
        self, llm_output: str, source_text: str
    ) -> tuple[str, GuardrailTelemetry]:
        regex_blocks = self.regex_validator.validate(llm_output)
        semantic_filters = self.semantic_validator.validate(llm_output, source_text)

        cleaned = self._clean(llm_output, regex_blocks, semantic_filters)
        telemetry = GuardrailTelemetry(
            regex_blocked=regex_blocks,
            semantic_filtered=semantic_filters,
            regenerate_count=0,
            fallback_triggered=False,
        )
        if regex_blocks or semantic_filters:
            logger.info(
                "guardrail: regex=%d semantic=%d",
                len(regex_blocks),
                len(semantic_filters),
            )
        return cleaned, telemetry

    @staticmethod
    def _clean(
        text: str,
        regex_blocks: list[GuardrailRegexBlock],
        semantic_filters: list[GuardrailSemanticFilter],
    ) -> str:
        if not text:
            return text
        bad_sentences = {f.original_text for f in semantic_filters}
        bad_fragments = [b.original_text for b in regex_blocks]

        kept: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                kept.append(line)
                continue
            if stripped in bad_sentences:
                continue
            if any(frag and frag in stripped for frag in bad_fragments):
                continue
            kept.append(line)
        return "\n".join(kept)
