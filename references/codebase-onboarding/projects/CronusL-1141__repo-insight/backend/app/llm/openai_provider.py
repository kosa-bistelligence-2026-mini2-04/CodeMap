from __future__ import annotations

import asyncio
import logging
import os
import random
from typing import Any

from .provider import BudgetExhaustedError, ConfigError

logger = logging.getLogger(__name__)

LLM_TIMEOUT_SECONDS = 30.0
MAX_RETRIES = 2
DEFAULT_MODEL = "gpt-5.4"


def _load_dotenv_once() -> None:
    """Read .env into os.environ if not already loaded (best-effort, no deps)."""
    if os.environ.get("_REPO_INSIGHT_DOTENV_LOADED") == "1":
        return
    candidates = [
        os.path.join(os.getcwd(), ".env"),
        os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env"),
    ]
    for path in candidates:
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and k not in os.environ:
                        os.environ[k] = v
        except OSError:
            continue
    os.environ["_REPO_INSIGHT_DOTENV_LOADED"] = "1"


class OpenAIProvider:
    name = "openai"

    def __init__(
        self,
        model: str | None = None,
        max_retries: int = MAX_RETRIES,
        budget_checker=None,
        audit_logger=None,
    ) -> None:
        _load_dotenv_once()
        self.model = model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)
        self.max_retries = max_retries
        self._client = None
        self._budget_checker = budget_checker
        self._audit_logger = audit_logger

    def _get_client(self):
        if self._client is not None:
            return self._client
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ConfigError("OPENAI_API_KEY not set")
        from openai import AsyncOpenAI

        base_url = os.environ.get("OPENAI_BASE_URL") or None
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        return self._client

    @staticmethod
    def _is_retryable(exc: BaseException) -> bool:
        try:
            from openai import (
                APIConnectionError,
                APIStatusError,
                APITimeoutError,
                RateLimitError,
            )
        except ImportError:
            return False
        if isinstance(exc, (APITimeoutError, APIConnectionError, RateLimitError)):
            return True
        if isinstance(exc, APIStatusError):
            status = getattr(exc, "status_code", None)
            if status is None:
                response = getattr(exc, "response", None)
                status = getattr(response, "status_code", None)
            return bool(status and status >= 500)
        return False

    @staticmethod
    def _is_client_error(exc: BaseException) -> bool:
        try:
            from openai import APIStatusError
        except ImportError:
            return False
        if isinstance(exc, APIStatusError):
            status = getattr(exc, "status_code", None)
            if status is None:
                response = getattr(exc, "response", None)
                status = getattr(response, "status_code", None)
            return bool(status and 400 <= status < 500)
        return False

    async def complete(
        self,
        prompt: str,
        *,
        response_format: dict | None = None,
        temperature: float = 0.0,
        model: str | None = None,
        max_tokens: int | None = None,
    ) -> str:
        if self._budget_checker is not None:
            ok = self._budget_checker()
            if asyncio.iscoroutine(ok):
                ok = await ok
            if not ok:
                raise BudgetExhaustedError("monthly LLM budget exhausted")

        client = self._get_client()
        used_model = model or self.model
        last_exc: BaseException | None = None

        for attempt in range(self.max_retries + 1):
            try:
                kwargs: dict[str, Any] = {
                    "model": used_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                }
                if response_format is not None:
                    kwargs["response_format"] = response_format
                if max_tokens is not None:
                    kwargs["max_tokens"] = max_tokens

                coro = client.chat.completions.create(**kwargs)
                response = await asyncio.wait_for(coro, timeout=LLM_TIMEOUT_SECONDS)

                choice = response.choices[0]
                content = choice.message.content or ""

                if self._audit_logger is not None:
                    usage = getattr(response, "usage", None)
                    prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
                    completion_tokens = (
                        getattr(usage, "completion_tokens", 0) if usage else 0
                    )
                    # B4: OpenAI server-side prompt cache hit tokens (new
                    # feature). Surface it as cache_hit=True so observability
                    # and audit_log show the actual server-side cache benefit.
                    cached_tokens = 0
                    usage_details = getattr(usage, "prompt_tokens_details", None)
                    if usage_details is not None:
                        cached_tokens = getattr(usage_details, "cached_tokens", 0) or 0
                    server_cache_hit = cached_tokens > 0
                    try:
                        maybe = self._audit_logger.record(
                            model=used_model,
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            cache_hit=server_cache_hit,
                        )
                        if asyncio.iscoroutine(maybe):
                            await maybe
                    except Exception as log_exc:
                        logger.warning(
                            "audit log write failed: %s: %s",
                            log_exc.__class__.__name__, log_exc,
                            exc_info=True,
                        )
                return content

            except asyncio.TimeoutError as exc:
                last_exc = exc
                logger.warning("openai request timed out (attempt=%d)", attempt)
            except BaseException as exc:
                last_exc = exc
                if self._is_client_error(exc):
                    raise
                if not self._is_retryable(exc):
                    raise
                logger.warning(
                    "openai retryable error (attempt=%d): %s", attempt, exc
                )

            if attempt >= self.max_retries:
                break
            backoff = 1.5 ** attempt + random.uniform(-0.2, 0.2)
            await asyncio.sleep(max(0.0, backoff))

        assert last_exc is not None
        raise last_exc
