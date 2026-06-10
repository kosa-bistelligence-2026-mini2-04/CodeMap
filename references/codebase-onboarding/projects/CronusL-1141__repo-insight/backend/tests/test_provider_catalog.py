"""Provider catalog detection tests — ensures frontend sees the right models
based on the configured OPENAI_BASE_URL."""
from __future__ import annotations

import pytest

from app.services.provider_catalog import (
    catalog_to_dict,
    detect_provider,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("OPENAI_BASE_URL", "OPENAI_MODEL"):
        monkeypatch.delenv(k, raising=False)
    yield


def test_default_is_openai_gpt_5_4(monkeypatch):
    c = detect_provider()
    assert c.provider == "openai"
    assert c.default_model == "gpt-5.4"
    assert any(m.id == "gpt-5.4" for m in c.models)
    assert any(m.id == "gpt-5.4-nano" for m in c.models)


def test_explicit_openai_base_url(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    c = detect_provider()
    assert c.provider == "openai"


def test_deepseek_detected(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("OPENAI_MODEL", "deepseek-chat")
    c = detect_provider()
    assert c.provider == "deepseek"
    assert c.default_model == "deepseek-chat"
    assert any(m.id == "deepseek-chat" for m in c.models)
    assert any(m.id == "deepseek-reasoner" for m in c.models)


def test_qwen_detected(monkeypatch):
    monkeypatch.setenv(
        "OPENAI_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    monkeypatch.setenv("OPENAI_MODEL", "qwen3-max")
    c = detect_provider()
    assert c.provider == "qwen"
    assert c.default_model == "qwen3-max"
    assert any(m.id.startswith("qwen") for m in c.models)


def test_qwen_international_base_url(monkeypatch):
    monkeypatch.setenv(
        "OPENAI_BASE_URL",
        "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    )
    c = detect_provider()
    assert c.provider == "qwen"


def test_zhipu_detected(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    monkeypatch.setenv("OPENAI_MODEL", "glm-5")
    c = detect_provider()
    assert c.provider == "zhipu"
    assert c.default_model == "glm-5"
    assert any(m.id == "glm-5" for m in c.models)


def test_moonshot_detected(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.moonshot.cn/v1")
    monkeypatch.setenv("OPENAI_MODEL", "kimi-k2.5")
    c = detect_provider()
    assert c.provider == "moonshot"
    assert c.default_model == "kimi-k2.5"
    assert any("kimi" in m.id for m in c.models)


def test_unknown_base_url_falls_through_to_custom(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com/v1")
    monkeypatch.setenv("OPENAI_MODEL", "my-model")
    c = detect_provider()
    assert c.provider == "custom"
    assert c.default_model == "my-model"


def test_default_model_respected_when_matches_provider(monkeypatch):
    """When user sets OPENAI_MODEL and it matches the provider, keep it."""
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("OPENAI_MODEL", "deepseek-reasoner")
    c = detect_provider()
    assert c.default_model == "deepseek-reasoner"


def test_catalog_to_dict_shape():
    c = detect_provider()
    d = catalog_to_dict(c)
    assert set(d.keys()) == {"provider", "base_url", "default_model", "models"}
    assert isinstance(d["models"], list)
    for m in d["models"]:
        assert {"id", "label", "hint"} <= m.keys()
