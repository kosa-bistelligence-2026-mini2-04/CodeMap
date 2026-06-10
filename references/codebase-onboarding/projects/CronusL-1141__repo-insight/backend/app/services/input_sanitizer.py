"""Input guardrail for sanitizing untrusted repository content before LLM calls.

This module lives under ``app.services`` (NOT ``app.guardrail``) so that
``BehaviorInferer`` can import it without violating the importlinter contract
that forbids ``app.agents.behavior_inferer`` from depending on
``app.guardrail.*`` (see CLAUDE.md / .importlinter forbidden contracts).

Purpose: prevent secrets in cloned repositories (README, ISSUE templates,
PR titles) from being exfiltrated to the OpenAI API via the prompt body,
and detect basic prompt-injection attempts that try to override the
system prompt of the BehaviorInferer agent.
"""

from __future__ import annotations

import re
from typing import Pattern

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

SECRET_PATTERNS: dict[str, str] = {
    "openai_key": r"sk-(?:proj-)?[A-Za-z0-9_-]{40,}",
    "aws_access_key": r"AKIA[0-9A-Z]{16}",
    "aws_secret": r"(?i)aws_?secret_?access_?key\s*[=:]\s*['\"][A-Za-z0-9/+=]{40}['\"]",
    "github_token": r"gh[pousr]_[A-Za-z0-9_]{36,}",
    "anthropic_key": r"sk-ant-[A-Za-z0-9_-]{40,}",
    "google_api_key": r"AIza[0-9A-Za-z_-]{35}",
    "ssh_private": r"-----BEGIN (RSA|OPENSSH|EC|DSA) PRIVATE KEY-----",
    "generic_bearer": r"(?i)bearer\s+[A-Za-z0-9_\-.=/]{20,}",
    "db_url_with_pass": r"(?i)(postgres|mysql|mongodb|redis)://[^:@\s]+:[^@\s]+@",
}

INJECTION_PATTERNS: list[str] = [
    r"(?i)ignore\s+(all\s+)?previous\s+instructions",
    r"(?i)system\s*:\s*",
    r"(?i)你现在是\s*",
    r"(?i)forget\s+(all\s+)?(your\s+)?instructions",
    r"(?i)<\|im_start\|>",
    r"(?i)role\s*:\s*['\"]?(system|assistant)['\"]?",
]


_COMPILED_SECRETS: dict[str, Pattern[str]] = {
    name: re.compile(pat) for name, pat in SECRET_PATTERNS.items()
}
_COMPILED_INJECTIONS: list[tuple[str, Pattern[str]]] = [
    (pat, re.compile(pat)) for pat in INJECTION_PATTERNS
]


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


class SecretFinding(BaseModel):
    pattern_name: str
    matched_preview: str = Field(
        description="First 8 characters of the match followed by '***' for safe logging"
    )
    offset: int


class InjectionFinding(BaseModel):
    pattern: str
    offset: int
    snippet: str


class InputScanResult(BaseModel):
    has_secrets: bool
    has_injection: bool
    secrets: list[SecretFinding] = Field(default_factory=list)
    injections: list[InjectionFinding] = Field(default_factory=list)
    cleaned_text: str


# ---------------------------------------------------------------------------
# Guardrail
# ---------------------------------------------------------------------------


_INJECTION_BLOCK_PLACEHOLDER = "[BLOCKED:possible_prompt_injection]"


class InputGuardrail:
    """Scan untrusted text for secrets / prompt injection and produce a cleaned copy."""

    def scan(self, text: str) -> InputScanResult:
        if not text:
            return InputScanResult(
                has_secrets=False,
                has_injection=False,
                secrets=[],
                injections=[],
                cleaned_text=text or "",
            )

        secrets = self._find_secrets(text)
        injections = self._find_injections(text)

        if injections:
            cleaned = _INJECTION_BLOCK_PLACEHOLDER
        else:
            cleaned = self._redact_secrets(text, secrets)

        return InputScanResult(
            has_secrets=bool(secrets),
            has_injection=bool(injections),
            secrets=secrets,
            injections=injections,
            cleaned_text=cleaned,
        )

    def _find_secrets(self, text: str) -> list[SecretFinding]:
        findings: list[SecretFinding] = []
        for name, pattern in _COMPILED_SECRETS.items():
            for match in pattern.finditer(text):
                raw = match.group(0)
                preview = (raw[:8] + "***") if len(raw) > 8 else (raw + "***")
                findings.append(
                    SecretFinding(
                        pattern_name=name,
                        matched_preview=preview,
                        offset=match.start(),
                    )
                )
        findings.sort(key=lambda f: f.offset)
        return findings

    def _find_injections(self, text: str) -> list[InjectionFinding]:
        findings: list[InjectionFinding] = []
        for pat_src, pattern in _COMPILED_INJECTIONS:
            for match in pattern.finditer(text):
                start = match.start()
                snippet_start = max(0, start - 20)
                snippet_end = min(len(text), match.end() + 20)
                findings.append(
                    InjectionFinding(
                        pattern=pat_src,
                        offset=start,
                        snippet=text[snippet_start:snippet_end],
                    )
                )
        findings.sort(key=lambda f: f.offset)
        return findings

    def _redact_secrets(
        self, text: str, secrets: list[SecretFinding]
    ) -> str:
        if not secrets:
            return text
        # Walk patterns once more so we replace the actual matched span. Iterating
        # by-pattern keeps it simple and avoids overlap accounting.
        cleaned = text
        for name, pattern in _COMPILED_SECRETS.items():
            cleaned = pattern.sub(f"[REDACTED:{name}]", cleaned)
        return cleaned


__all__ = [
    "SECRET_PATTERNS",
    "INJECTION_PATTERNS",
    "SecretFinding",
    "InjectionFinding",
    "InputScanResult",
    "InputGuardrail",
]
