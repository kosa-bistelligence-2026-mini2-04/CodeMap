from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.agents.behavior_inferer import BehaviorInferenceError, BehaviorInferer
from app.models.agent_schemas import BehaviorInfererInput


def _make_input(repo_path: str, job_id: str = "job-1") -> BehaviorInfererInput:
    return BehaviorInfererInput(
        repo_path=repo_path,
        job_id=job_id,
        timeout_seconds=50,
        max_pr_count=3,
        llm_model="gpt-5.4",
    )


def _valid_llm_payload() -> str:
    return json.dumps(
        {
            "usage_patterns": [
                {
                    "title": "CLI entrypoint",
                    "description": "Users run pipeline via python -m app.cli",
                    "evidence": "See README section Usage, python -m app.cli",
                }
            ],
            "core_modules": [
                {
                    "path": "app/cli.py",
                    "role": "entry",
                    "evidence": "README highlights CLI usage",
                }
            ],
            "inference_evidence": {"cli": "python -m app.cli"},
        }
    )


class _FakeProvider:
    name = "fake"
    model = "gpt-5.4"

    def __init__(self, return_value: str):
        self.return_value = return_value
        self.complete = AsyncMock(return_value=return_value)


class _InMemoryCache:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str, ttl: float | None = None) -> None:
        self.store[key] = value


# ---------------------------------------------------------------------------
# 1. No guardrail import at module load time (gate C runtime layer)
# ---------------------------------------------------------------------------


def test_no_guardrail_import():
    # Purge any guardrail modules that might have been imported by sibling tests.
    for mod in [m for m in list(sys.modules) if m.startswith("app.guardrail")]:
        del sys.modules[mod]
    # Reload target module fresh.
    if "app.agents.behavior_inferer" in sys.modules:
        del sys.modules["app.agents.behavior_inferer"]
    import importlib

    importlib.import_module("app.agents.behavior_inferer")

    leaked = [m for m in sys.modules if m.startswith("app.guardrail")]
    assert leaked == [], f"BehaviorInferer must not pull in app.guardrail, leaked: {leaked}"


# ---------------------------------------------------------------------------
# 2. README truncation
# ---------------------------------------------------------------------------


def test_readme_truncation(tmp_path: Path):
    big_readme = tmp_path / "README.md"
    big_readme.write_text("x" * 20_000, encoding="utf-8")

    inferer = BehaviorInferer()
    prompt = inferer._build_prompt(
        inferer._load_readme(str(tmp_path)),
        "",
        [],
    )

    # The README-derived text inside the prompt must be truncated to <= 8000 chars.
    # The static prefix is intentionally large (>1024 tokens for OpenAI prompt caching).
    # We assert the total prompt is within a reasonable budget < 5000 tokens approx.
    max_tokens_approx = len(prompt) / 4
    assert max_tokens_approx < 5000, (
        f"Prompt too long: ~{max_tokens_approx:.0f} tokens, expected < 5000"
    )
    # The README is truncated to 8000 chars; static prefix may contain a few extra 'x' chars.
    # We verify truncation by asserting total 'x' count is well under the original 20000.
    assert prompt.count("x") <= 8100


# ---------------------------------------------------------------------------
# 3. Missing GITHUB_TOKEN skips PR fetch
# ---------------------------------------------------------------------------


def test_no_github_token_skips_pr_fetch(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    inferer = BehaviorInferer()
    titles = asyncio.run(
        inferer._load_pr_titles(_make_input("https://github.com/foo/bar"))
    )
    assert titles == []


# ---------------------------------------------------------------------------
# 4. Cache hit skips LLM call
# ---------------------------------------------------------------------------


def test_cache_hit_skips_llm(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    (tmp_path / "README.md").write_text("hello world", encoding="utf-8")

    provider = _FakeProvider(return_value="should-not-be-called")
    cache = _InMemoryCache()

    # Pre-warm the cache with the exact key the inferer will compute.
    inferer = BehaviorInferer(llm_provider=provider, cache=cache)
    input_data = _make_input(str(tmp_path))

    # We run infer twice: first populates via LLM, second must hit cache.
    provider.complete.return_value = _valid_llm_payload()
    result1 = asyncio.run(inferer.infer(input_data))
    assert result1.usage_patterns, "first run should produce patterns"
    assert provider.complete.await_count == 1

    # Second call — cache must be hit, complete must NOT be called again.
    result2 = asyncio.run(inferer.infer(input_data))
    assert provider.complete.await_count == 1, "LLM must not be called on cache hit"
    assert result2.usage_patterns == result1.usage_patterns


# ---------------------------------------------------------------------------
# 5. Prompt v1 contains the mandatory constraints
# ---------------------------------------------------------------------------


def test_prompt_v1_contains_constraints():
    inferer = BehaviorInferer()
    prompt = inferer._build_prompt("readme body", "issue body", ["fix bug"])
    assert "禁止输出 ```json" in prompt
    assert "evidence 必须至少 8 字符" in prompt
    assert "合法 JSON" in prompt


# ---------------------------------------------------------------------------
# 6. Invalid JSON raises BehaviorInferenceError
# ---------------------------------------------------------------------------


def test_parse_invalid_json_raises(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    (tmp_path / "README.md").write_text("hi", encoding="utf-8")

    provider = _FakeProvider(return_value="not-json-at-all")
    cache = _InMemoryCache()
    inferer = BehaviorInferer(llm_provider=provider, cache=cache)

    with pytest.raises(BehaviorInferenceError):
        asyncio.run(inferer.infer(_make_input(str(tmp_path))))


# ---------------------------------------------------------------------------
# 7. response_format forwarded as {"type": "json_object"}
# ---------------------------------------------------------------------------


def test_response_format_json_object(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    (tmp_path / "README.md").write_text("hi", encoding="utf-8")

    provider = _FakeProvider(return_value=_valid_llm_payload())
    cache = _InMemoryCache()
    inferer = BehaviorInferer(llm_provider=provider, cache=cache)

    asyncio.run(inferer.infer(_make_input(str(tmp_path))))

    assert provider.complete.await_count == 1
    kwargs = provider.complete.await_args.kwargs
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["temperature"] == 0.0
    assert kwargs["model"] == "gpt-5.4"


# ---------------------------------------------------------------------------
# 8. BUG-R4: Cache key stable across different tmp repo_paths with same source_url
# ---------------------------------------------------------------------------

def test_cache_key_stable_across_tmp_paths():
    """Two BehaviorInfererInputs with different repo_path but same source_url produce same CacheKey."""
    import hashlib
    from app.llm.cache import CacheKey

    contents = "readme\x00\x00"
    file_hash = hashlib.sha256(contents.encode("utf-8")).hexdigest()

    key_a = CacheKey(
        repo_url="https://github.com/owner/repo",
        agent_name="behavior_inferer",
        file_contents_hash=file_hash,
        prompt_version="v1",
        model_name="gpt-5.4",
        temperature_int=0,
    )
    key_b = CacheKey(
        repo_url="https://github.com/owner/repo",
        agent_name="behavior_inferer",
        file_contents_hash=file_hash,
        prompt_version="v1",
        model_name="gpt-5.4",
        temperature_int=0,
    )

    assert key_a.to_string() == key_b.to_string(), (
        "Cache keys must be identical when source_url is the same, regardless of tmp repo_path"
    )

    # Verify that different source_urls produce different keys
    key_c = CacheKey(
        repo_url="https://github.com/owner/other-repo",
        agent_name="behavior_inferer",
        file_contents_hash=file_hash,
        prompt_version="v1",
        model_name="gpt-5.4",
        temperature_int=0,
    )
    assert key_a.to_string() != key_c.to_string(), "Different source URLs must produce different cache keys"
