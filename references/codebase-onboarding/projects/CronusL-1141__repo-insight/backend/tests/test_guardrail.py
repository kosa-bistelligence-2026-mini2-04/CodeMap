from __future__ import annotations

import pytest

from app.guardrail.regex_validator import RegexValidator
from app.guardrail.semantic_validator import SemanticValidator
from app.guardrail.validator import GuardrailValidator
from app.models.api_schemas import GuardrailTelemetry


@pytest.fixture(autouse=True)
def _stub_semantic(monkeypatch):
    monkeypatch.setenv("SEMANTIC_VALIDATOR_BACKEND", "stub")
    yield


def test_regex_validator_catches_future_tense():
    validator = RegexValidator()
    blocks = validator.validate("2027年将推出全新架构")
    assert len(blocks) >= 1
    assert any(b.rule_id == "future_tense" for b in blocks)
    assert all(b.layer == "regex" for b in blocks)


def test_regex_validator_catches_absolute_assertion():
    validator = RegexValidator()
    blocks = validator.validate("这个方案必须采用，毫无疑问")
    rule_ids = {b.rule_id for b in blocks}
    assert "absolute" in rule_ids


def test_regex_validator_catches_fabricated():
    validator = RegexValidator()
    blocks = validator.validate("根据最新研究表明性能提升三倍")
    rule_ids = {b.rule_id for b in blocks}
    assert "fabricated" in rule_ids


def test_regex_validator_clean_text_passes():
    validator = RegexValidator()
    blocks = validator.validate("该模块提供异步任务队列能力")
    assert blocks == []


def test_semantic_stub_returns_empty():
    validator = SemanticValidator()
    result = validator.validate("anything", "source")
    assert result == []


async def test_guardrail_validator_constructs_telemetry():
    validator = GuardrailValidator()
    text = "2027年将发布全新接口\n该模块提供异步任务队列"
    cleaned, telem = await validator.validate(text, "源文档")

    assert isinstance(telem, GuardrailTelemetry)
    assert len(telem.regex_blocked) >= 1
    assert any(b.rule_id == "future_tense" for b in telem.regex_blocked)
    assert telem.regenerate_count == 0
    assert telem.fallback_triggered is False
    assert "2027年将发布全新接口" not in cleaned
    assert "该模块提供异步任务队列" in cleaned


async def test_guardrail_validator_passes_clean_output():
    validator = GuardrailValidator()
    text = "该项目使用 FastAPI 构建 REST API"
    cleaned, telem = await validator.validate(text, "项目使用 FastAPI")
    assert cleaned == text
    assert telem.regex_blocked == []
    assert telem.semantic_filtered == []


async def test_guardrail_telemetry_json_serializable():
    validator = GuardrailValidator()
    _, telem = await validator.validate("必须采用新架构", "背景介绍")
    payload = telem.model_dump()
    assert "regex_blocked" in payload
    assert "semantic_filtered" in payload
    assert payload["regenerate_count"] == 0
    assert payload["fallback_triggered"] is False
