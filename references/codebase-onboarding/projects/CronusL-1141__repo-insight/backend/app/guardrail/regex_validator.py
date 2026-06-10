from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Pattern

from app.models.api_schemas import GuardrailRegexBlock

FUTURE_TENSE: Pattern[str] = re.compile(
    r"202[7-9]|20[3-9]\d|未来\s*[5-9]\s*年|下一代|即将发布"
)
ABSOLUTE: Pattern[str] = re.compile(
    r"必须|绝对|100%|永远不会|毫无疑问"
)
FABRICATED: Pattern[str] = re.compile(
    r"根据最新研究|据我所知|业界共识"
)


@dataclass(frozen=True)
class _Rule:
    rule_id: str
    pattern: Pattern[str]


_RULES: list[_Rule] = [
    _Rule("future_tense", FUTURE_TENSE),
    _Rule("absolute", ABSOLUTE),
    _Rule("fabricated", FABRICATED),
]


class RegexValidator:
    """Layer-1 filter: returns structured blocks for telemetry."""

    def __init__(self, rules: list[_Rule] | None = None) -> None:
        self.rules = rules if rules is not None else _RULES

    def validate(self, text: str) -> list[GuardrailRegexBlock]:
        blocks: list[GuardrailRegexBlock] = []
        if not text:
            return blocks
        for rule in self.rules:
            for match in rule.pattern.finditer(text):
                blocks.append(
                    GuardrailRegexBlock(
                        original_text=match.group(0),
                        rule_id=rule.rule_id,
                        layer="regex",
                    )
                )
        return blocks
