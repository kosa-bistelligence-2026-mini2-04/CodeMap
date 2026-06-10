from __future__ import annotations

from typing import Protocol


class ConfigError(RuntimeError):
    """Raised when required LLM provider configuration is missing."""


class BudgetExhaustedError(RuntimeError):
    """Raised when the monthly token/cost budget has been exhausted."""


class LLMProvider(Protocol):
    name: str
    model: str

    async def complete(
        self,
        prompt: str,
        *,
        response_format: dict | None = None,
        temperature: float = 0.0,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str: ...
