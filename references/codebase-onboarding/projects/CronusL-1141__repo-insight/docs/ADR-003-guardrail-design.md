# ADR-003: Guardrail 双层幻觉防护设计

- 状态：Accepted
- 日期：2026-04-12
- 作者：ai-engineer
- 关联：ADR-001 (Architecture)、ADR-002 (Schema)、CLAUDE.md §3.3

## 上下文

RepoInsight 中 BehaviorInferer 是唯一调用 LLM 的 Agent，其输出（usage_patterns、core_modules）将被 Reporter 直接渲染进 HTML 报告。LLM 存在三类典型幻觉风险：

1. **时态幻觉**：基于训练数据外推未来事件（"2026 年之后将支持..."）
2. **断言幻觉**：使用绝对化语言（"肯定"、"毫无疑问"）违背"基于证据"原则
3. **来源幻觉**：虚构外部引用（"根据最新研究"），或编造 README 中不存在的功能描述

本 ADR 定义双层 Guardrail 设计：**正则层快速拦截固定模式 + 语义层检测内容偏离原文**。

## 决策

实现 `backend/app/guardrail/validator.py`，提供 `GuardrailValidator` 统一入口，组合 `RegexValidator` 与 `SemanticValidator`，对 BehaviorInferer 的每段输出执行双层校验。

---

## 1. 正则层（Regex Layer）

### 1.1 设计原则

- 模式必须**高精确率**：宁可漏（语义层兜底），不可错杀
- 模式按类别分组，可独立开关
- 每条规则携带 `severity`（block / warn）和人类可读的违规说明

### 1.2 完整禁词正则库

```python
# backend/app/guardrail/regex_rules.py
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Pattern


class Severity(str, Enum):
    BLOCK = "block"   # 触发拦截 + 回退
    WARN = "warn"     # 标记但不拦截


@dataclass(frozen=True)
class RegexRule:
    name: str
    pattern: Pattern[str]
    severity: Severity
    reason: str


# 1) 未来时态 / 预测性陈述
FUTURE_TENSE_RULES: list[RegexRule] = [
    RegexRule(
        name="future_year",
        pattern=re.compile(r"(20[3-9]\d|2[1-9]\d{2})\s*年(之后|以后|起|开始)?"),
        severity=Severity.BLOCK,
        reason="禁止预测未来年份事件",
    ),
    RegexRule(
        name="future_relative",
        pattern=re.compile(r"未来\s*\d+\s*(年|月|周|天)"),
        severity=Severity.BLOCK,
        reason="禁止使用未来相对时间窗口",
    ),
    RegexRule(
        name="upcoming_release",
        pattern=re.compile(r"(即将|将要|将会|计划于)(发布|推出|上线|支持)"),
        severity=Severity.BLOCK,
        reason="禁止断言未发布的功能",
    ),
    RegexRule(
        name="next_generation",
        pattern=re.compile(r"(下一代|新一代|下个版本将)"),
        severity=Severity.BLOCK,
        reason="禁止虚构未来版本",
    ),
]

# 2) 绝对断言
ABSOLUTE_ASSERTION_RULES: list[RegexRule] = [
    RegexRule(
        name="absolute_certainty",
        pattern=re.compile(r"(肯定|一定|必然|绝对|百分之百|100%)(是|会|能|可以)"),
        severity=Severity.BLOCK,
        reason="禁止绝对化断言",
    ),
    RegexRule(
        name="no_doubt",
        pattern=re.compile(r"(毫无疑问|无可争议|不容置疑)"),
        severity=Severity.BLOCK,
        reason="禁止使用绝对化修饰语",
    ),
]

# 3) 虚构外部引用
FABRICATED_REF_RULES: list[RegexRule] = [
    RegexRule(
        name="latest_research",
        pattern=re.compile(r"(根据|依据)(最新|近期|权威)?(研究|报告|论文|数据)(显示|表明|指出)"),
        severity=Severity.BLOCK,
        reason="禁止引用未提供来源的研究",
    ),
    RegexRule(
        name="self_knowledge",
        pattern=re.compile(r"(据我所知|众所周知|业界公认|普遍认为)"),
        severity=Severity.BLOCK,
        reason="禁止使用模型先验作为来源",
    ),
    RegexRule(
        name="unspecified_source",
        pattern=re.compile(r"(某些|有些|一些)(用户|开发者|专家)(反馈|认为|表示)"),
        severity=Severity.WARN,
        reason="模糊来源应避免，建议引用具体 ISSUE/PR",
    ),
]

ALL_RULES: list[RegexRule] = (
    FUTURE_TENSE_RULES + ABSOLUTE_ASSERTION_RULES + FABRICATED_REF_RULES
)
```

### 1.3 RegexValidator 实现

```python
# backend/app/guardrail/regex_validator.py
from __future__ import annotations

from dataclasses import dataclass, field

from .regex_rules import ALL_RULES, RegexRule, Severity


@dataclass
class RegexViolation:
    rule_name: str
    severity: Severity
    matched_text: str
    span: tuple[int, int]
    reason: str


@dataclass
class RegexResult:
    passed: bool
    violations: list[RegexViolation] = field(default_factory=list)

    @property
    def has_block(self) -> bool:
        return any(v.severity == Severity.BLOCK for v in self.violations)


class RegexValidator:
    def __init__(self, rules: list[RegexRule] | None = None) -> None:
        self.rules = rules if rules is not None else ALL_RULES

    def validate(self, text: str) -> RegexResult:
        violations: list[RegexViolation] = []
        for rule in self.rules:
            for match in rule.pattern.finditer(text):
                violations.append(
                    RegexViolation(
                        rule_name=rule.name,
                        severity=rule.severity,
                        matched_text=match.group(0),
                        span=match.span(),
                        reason=rule.reason,
                    )
                )
        return RegexResult(
            passed=not any(v.severity == Severity.BLOCK for v in violations),
            violations=violations,
        )
```

### 1.4 测试用例（match / no-match）

| 规则 | match（应触发） | no-match（不应触发） |
|---|---|---|
| `future_year` | "2027 年之后将支持插件市场" | "本项目自 2021 年发布" |
| `future_relative` | "未来 3 年内成为主流框架" | "过去 3 年累计 5000 commits" |
| `upcoming_release` | "即将发布 v3.0" | "已发布 v2.5" |
| `next_generation` | "下一代异步引擎" | "当前异步引擎" |
| `absolute_certainty` | "该模块肯定是性能瓶颈" | "该模块可能是性能瓶颈" |
| `no_doubt` | "毫无疑问，FastAPI 是最佳选择" | "在测试场景中，FastAPI 表现优异" |
| `latest_research` | "根据最新研究显示该方案更优" | "根据 README 中的 benchmark" |
| `self_knowledge` | "众所周知 Python GIL 限制并发" | "README 第 12 行说明 GIL 限制" |
| `unspecified_source`（warn） | "一些用户反馈安装失败" | "ISSUE #42 报告了安装失败" |

---

## 2. 语义层（Semantic Layer）

### 2.1 方案对比

| 方案 | 精度 | 延迟 | 依赖 | 推荐 |
|---|---|---|---|---|
| sentence-transformers (`all-MiniLM-L6-v2`) | 高 | 50–200ms / 句 | 80MB 本地模型 | ✓ 默认 |
| TF-IDF cosine（scikit-learn） | 中 | < 10ms / 句 | scikit-learn | 备选/降级 |
| OpenAI embeddings API | 高 | 300ms+ | 网络 + 计费 | 不采用，成本与延迟均不划算 |

### 2.2 决策

- **默认**：`sentence-transformers` + `all-MiniLM-L6-v2`，本地推理，单 CPU 可承受
- **降级**：模型加载失败 / 内存不足时自动回退到 `TfidfVectorizer + cosine_similarity`
- 启动期 lazy load 模型，首次请求承担一次冷启动

### 2.3 相似度计算流程

1. 切句：按中文标点（。！？）+ 英文标点（. ! ?）+ 换行切分 LLM 输出
2. 对每个非空句子计算嵌入
3. 将 README + ISSUE 模板 + 近 3 PR 标题作为 source_text，按段落（`\n\n`）切分计算嵌入
4. 对每句 LLM 输出，与所有 source 段落取**最大** cosine 相似度
5. 最大相似度 < `threshold`（默认 0.35）→ 标记为 `hallucinated_sentence`
6. 输出整体通过条件：所有句子均通过 OR `hallucination_ratio < 0.2`

### 2.4 SemanticValidator 实现

```python
# backend/app/guardrail/semantic_validator.py
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Protocol

logger = logging.getLogger(__name__)

_SENT_SPLIT = re.compile(r"(?<=[。！？!?])\s+|\n+")


class EmbeddingBackend(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


@dataclass
class SentenceCheck:
    sentence: str
    max_similarity: float
    matched_source: str
    is_hallucinated: bool


@dataclass
class SemanticResult:
    passed: bool
    threshold: float
    hallucination_ratio: float
    sentence_checks: list[SentenceCheck] = field(default_factory=list)


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def _cosine(a: list[float], b: list[float]) -> float:
    import math

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class SentenceTransformersBackend:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return [vec.tolist() for vec in vectors]


class TfidfBackend:
    def __init__(self) -> None:
        from sklearn.feature_extraction.text import TfidfVectorizer

        self._vectorizer = TfidfVectorizer()
        self._fitted = False

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not self._fitted:
            matrix = self._vectorizer.fit_transform(texts)
            self._fitted = True
        else:
            matrix = self._vectorizer.transform(texts)
        return matrix.toarray().tolist()


def build_default_backend() -> EmbeddingBackend:
    try:
        return SentenceTransformersBackend()
    except Exception as exc:
        logger.warning("sentence-transformers unavailable, fallback to TF-IDF: %s", exc)
        return TfidfBackend()


class SemanticValidator:
    def __init__(
        self,
        threshold: float = 0.35,
        max_hallucination_ratio: float = 0.2,
        backend: EmbeddingBackend | None = None,
    ) -> None:
        self.threshold = threshold
        self.max_hallucination_ratio = max_hallucination_ratio
        self.backend = backend or build_default_backend()

    def validate(self, llm_output: str, source_text: str) -> SemanticResult:
        sentences = _split_sentences(llm_output)
        sources = _split_paragraphs(source_text)
        if not sentences or not sources:
            return SemanticResult(
                passed=True, threshold=self.threshold, hallucination_ratio=0.0
            )

        sent_vecs = self.backend.encode(sentences)
        src_vecs = self.backend.encode(sources)

        checks: list[SentenceCheck] = []
        for sent, sv in zip(sentences, sent_vecs):
            best_sim = -1.0
            best_src = ""
            for src, srv in zip(sources, src_vecs):
                sim = _cosine(sv, srv)
                if sim > best_sim:
                    best_sim = sim
                    best_src = src
            checks.append(
                SentenceCheck(
                    sentence=sent,
                    max_similarity=best_sim,
                    matched_source=best_src[:120],
                    is_hallucinated=best_sim < self.threshold,
                )
            )

        hallucinated = sum(1 for c in checks if c.is_hallucinated)
        ratio = hallucinated / len(checks)
        return SemanticResult(
            passed=ratio <= self.max_hallucination_ratio,
            threshold=self.threshold,
            hallucination_ratio=ratio,
            sentence_checks=checks,
        )
```

### 2.5 阈值校准说明

- 0.35 来自 `all-MiniLM-L6-v2` 在中英文混合段落上的经验值
- 上线前需用 20 条标注样本（10 真实 + 10 人工幻觉）做 ROC 曲线校准
- 阈值低于 0.25 → 漏报增加；高于 0.5 → 误报激增（同一概念不同表述被拒）

---

## 3. 双层过滤接口

```python
# backend/app/guardrail/validator.py
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .regex_validator import RegexResult, RegexValidator, Severity
from .semantic_validator import SemanticResult, SemanticValidator

logger = logging.getLogger(__name__)


@dataclass
class GuardrailResult:
    passed: bool
    cleaned_output: str
    regex_result: RegexResult
    semantic_result: SemanticResult
    violations: list[str] = field(default_factory=list)
    confidence: float = 1.0   # 1.0=高 / 0.5=中 / 0.0=低


class GuardrailValidator:
    def __init__(
        self,
        regex_layer: RegexValidator | None = None,
        semantic_layer: SemanticValidator | None = None,
    ) -> None:
        self.regex_layer = regex_layer or RegexValidator()
        self.semantic_layer = semantic_layer or SemanticValidator()

    def check(self, llm_output: str, source_text: str) -> GuardrailResult:
        regex_result = self.regex_layer.validate(llm_output)
        semantic_result = self.semantic_layer.validate(llm_output, source_text)

        violations: list[str] = []
        for v in regex_result.violations:
            violations.append(f"[regex/{v.rule_name}] {v.matched_text} — {v.reason}")
        for c in semantic_result.sentence_checks:
            if c.is_hallucinated:
                violations.append(
                    f"[semantic] sim={c.max_similarity:.2f} < {semantic_result.threshold}: {c.sentence[:60]}"
                )

        cleaned = self._strip_violations(llm_output, regex_result, semantic_result)
        confidence = self._compute_confidence(regex_result, semantic_result)
        passed = regex_result.passed and semantic_result.passed

        if not passed:
            logger.info("guardrail blocked: %d violations", len(violations))

        return GuardrailResult(
            passed=passed,
            cleaned_output=cleaned,
            regex_result=regex_result,
            semantic_result=semantic_result,
            violations=violations,
            confidence=confidence,
        )

    @staticmethod
    def _strip_violations(
        text: str, regex_result: RegexResult, semantic_result: SemanticResult
    ) -> str:
        bad_sentences = {
            c.sentence for c in semantic_result.sentence_checks if c.is_hallucinated
        }
        kept: list[str] = []
        for sent in [s.strip() for s in text.splitlines() if s.strip()]:
            if sent in bad_sentences:
                continue
            if any(v.matched_text in sent for v in regex_result.violations
                   if v.severity == Severity.BLOCK):
                continue
            kept.append(sent)
        return "\n".join(kept)

    @staticmethod
    def _compute_confidence(
        regex_result: RegexResult, semantic_result: SemanticResult
    ) -> float:
        if regex_result.has_block or not semantic_result.passed:
            return 0.0
        if regex_result.violations:   # 仅 warn
            return 0.5
        return 1.0
```

---

## 4. 拦截回退策略

### 4.1 三级策略

| 策略 | 条件 | 行为 |
|---|---|---|
| **A: 再生成** | 首次违规 且 重试次数 < 2 | 重新调用 LLM，prompt 加入 `additional_constraints`，列出本次违规原文 |
| **B: 截断** | 再生成后仍有违规 但 cleaned_output 非空 | 使用 `cleaned_output`，删除违规句保留合规部分 |
| **C: low_confidence 兜底** | cleaned_output 为空 或 全部句子被判幻觉 | 输出占位符 `"基于现有材料无法可靠推断典型使用场景"`，`confidence=0.0`，Reporter 渲染时加灰底 + warning 标识 |

### 4.2 决策树

```
LLM 输出 → GuardrailValidator.check
  ├─ passed=True
  │    └─ 直接返回，confidence=1.0
  └─ passed=False
       ├─ retry_count < 2  → 策略 A: 再生成
       │    └─ 重新进入 check
       ├─ cleaned_output 非空 且 句子数 ≥ 2 → 策略 B: 截断保留
       │    └─ confidence=0.5，标记 partial_truncated
       └─ 否则 → 策略 C: low_confidence 兜底
            └─ confidence=0.0，写入审计日志
```

### 4.3 Planner 集成伪代码

```python
async def run_behavior_inferer_with_guardrail(
    inferer, guardrail, source_text, max_retries=2
):
    additional_constraints: list[str] = []
    for attempt in range(max_retries + 1):
        raw = await inferer.infer(source_text, extra_constraints=additional_constraints)
        result = guardrail.check(raw, source_text)
        if result.passed:
            return raw, result
        if attempt < max_retries:
            additional_constraints = [v for v in result.violations]
            continue
        if result.cleaned_output and result.cleaned_output.count("\n") >= 1:
            return result.cleaned_output, result   # 策略 B
    return _build_low_confidence_placeholder(), result   # 策略 C
```

---

## 5. BehaviorInferer 提示词模板

### 5.1 完整 Prompt

```text
# prompts/behavior_inferer/v1.txt

[SYSTEM]
你是 RepoInsight 项目的"代码行为推理 Agent"。你的唯一任务：基于给定的
README、ISSUE 模板、近 3 个 PR 标题，推理这个仓库的典型使用场景与核心模块。

严格约束（违反将被自动拦截）：
1. 只能基于"用户输入材料"中的事实，禁止引入外部知识或猜测
2. 禁止使用未来时态：不得出现"2026 年之后"、"未来 N 年"、"即将"、"下一代"等
3. 禁止绝对断言：不得使用"肯定"、"一定"、"毫无疑问"、"100%"
4. 禁止虚构来源：不得使用"根据最新研究"、"据我所知"、"业界公认"
5. 每个 usage_pattern 必须能在 README/ISSUE/PR 中找到对应原文（evidence 字段）
6. 输出严格遵守 JSON Schema，禁止 Markdown 代码块包裹，禁止额外解释

输出格式（JSON Schema）：
{
  "usage_patterns": [
    {
      "title": "string, 8-30 字",
      "description": "string, 30-120 字，引用原文",
      "evidence": "string, README/ISSUE/PR 中的原文片段",
      "confidence": "high | medium | low"
    }
  ],
  "core_modules": [
    {
      "module_path": "string, 如 src/foo/bar.py",
      "role": "string, 5-20 字",
      "evidence": "string, 引用原文"
    }
  ]
}

约束清单（动态注入）：
{additional_constraints}

[USER]
=== README ===
{readme_text}

=== ISSUE 模板 ===
{issue_template_text}

=== 近 3 个 PR 标题 ===
{recent_pr_titles}

请输出 JSON。
```

### 5.2 输出 JSON Schema（与 ADR-002 BehaviorResult 对齐）

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "BehaviorInfererOutput",
  "type": "object",
  "required": ["usage_patterns", "core_modules"],
  "properties": {
    "usage_patterns": {
      "type": "array",
      "minItems": 1,
      "maxItems": 5,
      "items": {
        "type": "object",
        "required": ["title", "description", "evidence", "confidence"],
        "properties": {
          "title": {"type": "string", "minLength": 8, "maxLength": 30},
          "description": {"type": "string", "minLength": 30, "maxLength": 120},
          "evidence": {"type": "string", "minLength": 5},
          "confidence": {"type": "string", "enum": ["high", "medium", "low"]}
        }
      }
    },
    "core_modules": {
      "type": "array",
      "minItems": 1,
      "maxItems": 8,
      "items": {
        "type": "object",
        "required": ["module_path", "role", "evidence"],
        "properties": {
          "module_path": {"type": "string"},
          "role": {"type": "string", "minLength": 5, "maxLength": 20},
          "evidence": {"type": "string", "minLength": 5}
        }
      }
    }
  }
}
```

### 5.3 prompts 目录布局

```
backend/app/prompts/
└── behavior_inferer/
    ├── v1.txt          # 当前生产版本
    ├── v1.schema.json
    └── CHANGELOG.md    # 每次 prompt 变更必须记录
```

---

## 6. LLM Provider 抽象层

### 6.1 Protocol 定义

```python
# backend/app/llm/provider.py
from __future__ import annotations

from typing import Any, Protocol


class LLMProvider(Protocol):
    name: str
    model: str

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> str: ...
```

### 6.2 OpenAI 实现（默认）

```python
# backend/app/llm/openai_provider.py
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAIProvider:
    name = "openai"

    def __init__(self, model: str = "gpt-5.4", max_retries: int = 2) -> None:
        api_key = os.environ["OPENAI_API_KEY"]   # 强制环境变量
        self.model = model
        self.max_retries = max_retries
        self._client = AsyncOpenAI(api_key=api_key)

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> str:
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = await asyncio.wait_for(
                    self._client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        **kwargs,
                    ),
                    timeout=timeout,
                )
                return resp.choices[0].message.content or ""
            except (asyncio.TimeoutError, Exception) as exc:
                last_exc = exc
                logger.warning("OpenAI attempt %d failed: %s", attempt + 1, exc)
                await asyncio.sleep(1.5 ** attempt)
        raise RuntimeError(f"OpenAI all retries exhausted: {last_exc}")
```

### 6.3 Claude Provider（备份）

```python
# backend/app/llm/claude_provider.py
from __future__ import annotations

import asyncio
import os
from typing import Any

from anthropic import AsyncAnthropic


class ClaudeProvider:
    name = "claude"

    def __init__(self, model: str = "claude-opus-4-6") -> None:
        api_key = os.environ["ANTHROPIC_API_KEY"]
        self.model = model
        self._client = AsyncAnthropic(api_key=api_key)

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        timeout: float = 30.0,
        **kwargs: Any,
    ) -> str:
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_msgs = [m for m in messages if m["role"] != "system"]
        resp = await asyncio.wait_for(
            self._client.messages.create(
                model=self.model,
                system=system,
                messages=user_msgs,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            ),
            timeout=timeout,
        )
        return "".join(block.text for block in resp.content if hasattr(block, "text"))
```

### 6.4 超时与重试策略

| 维度 | 默认值 | 说明 |
|---|---|---|
| 单次调用超时 | 30s | BehaviorInferer 总预算 45s，预留 guardrail 时间 |
| 最大重试次数 | 2 | 指数退避 1.5^attempt |
| 重试触发 | 网络错误、5xx、Timeout | 4xx 不重试，直接上抛 |
| Guardrail 重试 | 2 | 与网络重试解耦，由 Planner 控制 |

### 6.5 缓存键设计

```python
# backend/app/llm/cache.py
import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class CacheKey:
    repo_url: str
    agent_name: str          # "behavior_inferer"
    file_contents_hash: str  # README + ISSUE + PR titles 的 sha256

    def to_string(self) -> str:
        raw = f"{self.repo_url}|{self.agent_name}|{self.file_contents_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_file_contents_hash(*texts: str) -> str:
    h = hashlib.sha256()
    for t in texts:
        h.update(t.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()
```

- 缓存载体：SQLite，TTL 24h
- 缓存粒度：单 Agent 调用结果，不缓存中间 token
- 缓存 miss 再走 LLM；命中直接走 Guardrail（仍需校验一次，避免历史污染）

---

## 后果

### 正面
- 双层 Guardrail 在网络/语义两个维度独立兜底，单层失效不影响整体
- Provider 抽象使 OpenAI/Claude 切换无需改动 Agent
- Prompt 版本化 + JSON Schema 输出便于自动化评估

### 负面
- sentence-transformers 80MB 模型增加首次启动延迟（约 3–5s）
- 语义层在中英混合短句上的阈值需持续校准
- LLM 重试 + Guardrail 重试可能将 BehaviorInferer 时延推至 30s+，需在 Planner 层设硬超时

### 待跟进
- 上线后 1 周内基于真实流量重新校准 0.35 阈值
- 评估是否引入 LLM-as-judge 作为第三层（成本与延迟权衡）
- Prompt v2 加入 few-shot 示例后再次评估幻觉率
