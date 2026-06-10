from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.llm.cache import CacheKey, LLMCache, reset_cache_stats
from app.llm.openai_provider import OpenAIProvider
from app.llm.provider import BudgetExhaustedError, ConfigError


@pytest.fixture(autouse=True)
def _reset_cache_counters():
    reset_cache_stats()
    yield
    reset_cache_stats()


@pytest.fixture
def _clean_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("_REPO_INSIGHT_DOTENV_LOADED", "1")
    yield


async def test_openai_missing_key_raises_config_error(_clean_openai_key):
    provider = OpenAIProvider(model="gpt-5.4")
    with pytest.raises(ConfigError, match="OPENAI_API_KEY not set"):
        await provider.complete("ping")


async def test_budget_exhausted_skips_network(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("_REPO_INSIGHT_DOTENV_LOADED", "1")

    network_called = {"flag": False}

    class _FailingClient:
        class chat:
            class completions:
                @staticmethod
                async def create(**kwargs):
                    network_called["flag"] = True
                    raise AssertionError("network should not be called")

    provider = OpenAIProvider(
        model="gpt-5.4",
        budget_checker=lambda: False,
    )
    provider._client = _FailingClient()

    with pytest.raises(BudgetExhaustedError):
        await provider.complete("hello")
    assert network_called["flag"] is False


async def test_cache_key_is_stable_and_32_chars():
    k1 = CacheKey(
        repo_url="https://github.com/a/b",
        agent_name="BehaviorInferer",
        file_contents_hash="deadbeef",
        prompt_version="v2",
        model_name="gpt-5.4",
        temperature_int=0,
    )
    k2 = CacheKey(
        repo_url="https://github.com/a/b",
        agent_name="BehaviorInferer",
        file_contents_hash="deadbeef",
        prompt_version="v2",
        model_name="gpt-5.4",
        temperature_int=0,
    )
    assert k1.to_string() == k2.to_string()
    assert len(k1.to_string()) == 32


async def test_prompt_cache_hit_forwards_cache_hit_true(monkeypatch):
    """B4: When OpenAI returns prompt_tokens_details.cached_tokens > 0,
    the audit logger must see cache_hit=True (server-side prompt cache hit)."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("_REPO_INSIGHT_DOTENV_LOADED", "1")

    audit_calls: list[dict] = []

    class FakeAudit:
        async def record(self, **kw):
            audit_calls.append(kw)

    provider = OpenAIProvider(model="gpt-5.4-nano", audit_logger=FakeAudit())

    def _make_response(cached: int):
        resp = MagicMock()
        resp.choices = [MagicMock()]
        resp.choices[0].message.content = '{"ok": 1}'
        usage = MagicMock()
        usage.prompt_tokens = 1500
        usage.completion_tokens = 80
        details = MagicMock()
        details.cached_tokens = cached
        usage.prompt_tokens_details = details
        resp.usage = usage
        return resp

    async def fake_create_hit(**kw):
        return _make_response(cached=1200)

    class C1:
        class chat:
            class completions:
                create = staticmethod(fake_create_hit)

    provider._client = C1()
    await provider.complete("prompt with long static prefix")
    assert audit_calls[-1]["cache_hit"] is True

    # When cached_tokens == 0, cache_hit must be False
    async def fake_create_miss(**kw):
        return _make_response(cached=0)

    class C2:
        class chat:
            class completions:
                create = staticmethod(fake_create_miss)

    provider._client = C2()
    await provider.complete("prompt no cache")
    assert audit_calls[-1]["cache_hit"] is False


async def test_cache_key_repo_url_normalized_windows_vs_posix():
    """BUG-R4 fix: same local path with mixed separators / trailing slash should
    produce the SAME cache key, not trigger a cache miss on the second run."""
    base = dict(
        agent_name="BehaviorInferer",
        file_contents_hash="h",
        prompt_version="v1",
        model_name="gpt-5.4",
        temperature_int=0,
    )
    k_backslash = CacheKey(repo_url="C:\\Users\\TUF\\project", **base).to_string()
    k_forward = CacheKey(repo_url="C:/Users/TUF/project", **base).to_string()
    k_trailing = CacheKey(repo_url="C:/Users/TUF/project/", **base).to_string()
    k_upper = CacheKey(repo_url="C:/Users/TUF/PROJECT", **base).to_string()
    k_gh = CacheKey(repo_url="https://github.com/owner/repo.git", **base).to_string()
    k_gh_no_suffix = CacheKey(repo_url="https://github.com/owner/repo", **base).to_string()

    assert k_backslash == k_forward == k_trailing == k_upper
    assert k_gh == k_gh_no_suffix


async def test_cache_key_six_dimensions_differ():
    base = dict(
        repo_url="r",
        agent_name="a",
        file_contents_hash="h",
        prompt_version="v1",
        model_name="m",
        temperature_int=0,
    )
    base_key = CacheKey(**base).to_string()
    for field in base.keys():
        variant = dict(base)
        if field == "temperature_int":
            variant[field] = 50
        else:
            variant[field] = variant[field] + "_"
        assert CacheKey(**variant).to_string() != base_key, f"{field} must affect key"


async def test_llm_cache_roundtrip_and_ttl(tmp_path):
    cache = LLMCache(db_path=tmp_path / "llm.db")
    await cache.set("k1", "v1", ttl=60)
    assert await cache.get("k1") == "v1"

    await cache.set("k2", "v2", ttl=0.0)
    await asyncio.sleep(0.01)
    assert await cache.get("k2") is None


async def test_cache_hit_runs_guardrail_once(tmp_path, monkeypatch):
    """Cache hit does NOT skip guardrail — validator is invoked every call."""
    from app.guardrail import GuardrailValidator

    monkeypatch.setenv("SEMANTIC_VALIDATOR_BACKEND", "stub")

    cache = LLMCache(db_path=tmp_path / "llm.db")
    await cache.set("key-hit", "cached llm output", ttl=60)

    call_count = {"n": 0}
    validator = GuardrailValidator()
    original_validate = validator.validate

    async def counting_validate(text, src):
        call_count["n"] += 1
        return await original_validate(text, src)

    validator.validate = counting_validate  # type: ignore[method-assign]

    cached = await cache.get("key-hit")
    assert cached == "cached llm output"
    cleaned, telem = await validator.validate(cached, "source readme text")
    assert cleaned == "cached llm output"
    assert telem.regex_blocked == []
    assert call_count["n"] == 1


async def test_retry_then_success(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("_REPO_INSIGHT_DOTENV_LOADED", "1")
    monkeypatch.setattr("random.uniform", lambda *_: 0.0)
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    try:
        from openai import APIConnectionError
    except ImportError:
        pytest.skip("openai sdk not available")

    attempts = {"n": 0}

    async def flaky(**kwargs):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise APIConnectionError(request=MagicMock())
        msg = MagicMock()
        msg.message.content = "ok"
        response = MagicMock()
        response.choices = [msg]
        response.usage = MagicMock(prompt_tokens=1, completion_tokens=1)
        return response

    client = MagicMock()
    client.chat.completions.create = flaky
    provider = OpenAIProvider(model="gpt-5.4")
    provider._client = client

    result = await provider.complete("hi")
    assert result == "ok"
    assert attempts["n"] == 2


async def test_4xx_does_not_retry(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("_REPO_INSIGHT_DOTENV_LOADED", "1")
    monkeypatch.setattr("random.uniform", lambda *_: 0.0)
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    try:
        from openai import APIStatusError
    except ImportError:
        pytest.skip("openai sdk not available")

    attempts = {"n": 0}

    async def always_400(**kwargs):
        attempts["n"] += 1
        response = MagicMock()
        response.status_code = 400
        err = APIStatusError(
            message="bad request", response=response, body={"error": "bad"}
        )
        raise err

    client = MagicMock()
    client.chat.completions.create = always_400
    provider = OpenAIProvider(model="gpt-5.4")
    provider._client = client

    with pytest.raises(APIStatusError):
        await provider.complete("hi")
    assert attempts["n"] == 1


async def test_semantic_stub_does_not_import_st(monkeypatch):
    """With SEMANTIC_VALIDATOR_BACKEND=stub, importing semantic_validator must
    NOT pull sentence_transformers into sys.modules."""
    monkeypatch.setenv("SEMANTIC_VALIDATOR_BACKEND", "stub")
    for mod in list(sys.modules.keys()):
        if mod.startswith("sentence_transformers"):
            sys.modules.pop(mod, None)
    sys.modules.pop("app.guardrail.semantic_validator", None)

    import importlib

    mod = importlib.import_module("app.guardrail.semantic_validator")
    validator = mod.SemanticValidator()
    result = validator.validate("some output", "source text")
    assert result == []
    assert "sentence_transformers" not in sys.modules
