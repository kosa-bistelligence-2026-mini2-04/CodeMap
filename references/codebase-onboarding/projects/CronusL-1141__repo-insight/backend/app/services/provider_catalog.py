"""Provider catalog — introspects OPENAI_BASE_URL to detect which LLM
provider is configured and returns the matching model list.

Why: users in mainland China often cannot reach OpenAI directly. The LLM layer
is OpenAI-compatible so any provider speaking the same protocol (DeepSeek,
Qwen DashScope, Zhipu GLM, Moonshot Kimi, ...) plugs in via just changing
three env vars (OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL).

The frontend calls `GET /api/models` on mount to populate the model dropdown
so users only see models that will actually work against the configured base URL.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    id: str
    label: str
    hint: str


@dataclass(frozen=True)
class ProviderCatalog:
    provider: str  # "openai" / "deepseek" / "qwen" / "zhipu" / "moonshot" / "custom"
    base_url: str | None
    default_model: str
    models: tuple[ModelInfo, ...]


# Catalogs verified against official API docs on 2026-04-14.

_OPENAI_CATALOG = (
    ModelInfo("gpt-5.4", "GPT-5.4",
              "$2.50/$15 · 1M 上下文 · 旗舰"),
    ModelInfo("gpt-5.4-mini", "GPT-5.4-mini",
              "$0.75/$4.50 · 400K 上下文 · 平衡"),
    ModelInfo("gpt-5.4-nano", "GPT-5.4-nano",
              "$0.20/$1.25 · 最便宜，判官默认"),
)

_DEEPSEEK_CATALOG = (
    ModelInfo("deepseek-chat", "DeepSeek V3.2",
              "$0.28/$0.42 · 128K · 主力对话"),
    ModelInfo("deepseek-reasoner", "DeepSeek V3.2 Reasoner",
              "$0.28/$0.42 · 128K · 深度推理 (R1 模式)"),
)

_QWEN_CATALOG = (
    ModelInfo("qwen3-max", "通义千问 Qwen3-Max",
              "旗舰模型 · 当前稳定版"),
    ModelInfo("qwen3.5-plus", "通义千问 Qwen3.5-Plus",
              "平衡质量与速度"),
    ModelInfo("qwen3.5-flash", "通义千问 Qwen3.5-Flash",
              "快速低成本"),
    ModelInfo("qwen-long-latest", "通义千问 Qwen-Long",
              "超长上下文 10M tokens"),
)

_ZHIPU_CATALOG = (
    ModelInfo("glm-5", "智谱 GLM-5",
              "$0.72/$0.60 · 2026-02 最新旗舰"),
    ModelInfo("glm-4.6", "智谱 GLM-4.6",
              "$0.39/$1.74 · 205K 上下文 · 高性价比"),
    ModelInfo("glm-4.5", "智谱 GLM-4.5",
              "$0.60/$2.20 · 131K · 稳定版"),
)

_MOONSHOT_CATALOG = (
    ModelInfo("kimi-k2.5", "Kimi K2.5",
              "$0.60/$3.00 · 262K · 多模态 · 2026-01 最新"),
    ModelInfo("kimi-k2", "Kimi K2",
              "$0.55/$2.20 · 之前版本"),
    ModelInfo("moonshot-v1-128k", "Moonshot v1-128k",
              "Legacy 长上下文"),
)


def detect_provider() -> ProviderCatalog:
    """Introspect OPENAI_BASE_URL env var and return matching catalog."""
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip().rstrip("/")
    default_model = os.environ.get("OPENAI_MODEL", "gpt-5.4").strip()

    if not base_url or "api.openai.com" in base_url:
        return ProviderCatalog(
            provider="openai",
            base_url=base_url or "https://api.openai.com/v1",
            default_model=default_model or "gpt-5.4",
            models=_OPENAI_CATALOG,
        )
    if "deepseek" in base_url:
        return ProviderCatalog(
            provider="deepseek",
            base_url=base_url,
            default_model=default_model if default_model.startswith("deepseek") else "deepseek-chat",
            models=_DEEPSEEK_CATALOG,
        )
    if "dashscope" in base_url or "dashscope.aliyuncs" in base_url:
        return ProviderCatalog(
            provider="qwen",
            base_url=base_url,
            default_model=default_model if default_model.startswith("qwen") else "qwen-plus",
            models=_QWEN_CATALOG,
        )
    if "bigmodel.cn" in base_url or "zhipu" in base_url:
        return ProviderCatalog(
            provider="zhipu",
            base_url=base_url,
            default_model=default_model if default_model.startswith("glm") else "glm-4-air",
            models=_ZHIPU_CATALOG,
        )
    if "moonshot" in base_url:
        is_moonshot_model = default_model.startswith("moonshot") or default_model.startswith("kimi")
        return ProviderCatalog(
            provider="moonshot",
            base_url=base_url,
            default_model=default_model if is_moonshot_model else "kimi-k2.5",
            models=_MOONSHOT_CATALOG,
        )

    # Unknown custom OpenAI-compatible endpoint — return GPT-5.4 catalog
    # since the user already set OPENAI_MODEL themselves.
    return ProviderCatalog(
        provider="custom",
        base_url=base_url,
        default_model=default_model or "gpt-5.4",
        models=_OPENAI_CATALOG,
    )


def catalog_to_dict(c: ProviderCatalog) -> dict:
    return {
        "provider": c.provider,
        "base_url": c.base_url,
        "default_model": c.default_model,
        "models": [
            {"id": m.id, "label": m.label, "hint": m.hint}
            for m in c.models
        ],
    }
