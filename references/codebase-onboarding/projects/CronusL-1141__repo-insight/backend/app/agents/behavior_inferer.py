from __future__ import annotations

import glob
import hashlib
import json
import logging
import os
import time
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

from app.agents.base import BaseAgent
from app.llm.cache import CacheKey, LLMCache
from app.llm.provider import LLMProvider
from app.models.agent_schemas import BehaviorInfererInput, BehaviorResult
from app.services.input_sanitizer import InputGuardrail, InputScanResult
from app.services.repo_map import RepoMap, RepoMapResult

# NOTE: app.guardrail import is forbidden here by .importlinter forbidden
# contract "BehaviorInferer must route through Planner for Guardrail".
# Raw LLM output is returned and the Planner layer wires in the guardrail.
# The input-side guardrail lives in app.services.input_sanitizer (NOT in
# app.guardrail) so this import does not cross the forbidden boundary.

_README_MAX_CHARS = 8000
_ISSUE_TEMPLATE_MAX_CHARS = 4000
_PROMPT_VERSION = "v1"


class BehaviorInferenceError(RuntimeError):
    """Raised when the LLM output cannot be parsed into a BehaviorResult."""


# Static prefix — must remain identical across all calls so OpenAI Automatic Prompt
# Caching can reuse the KV cache. Dynamic repo data is appended at the end.
_STATIC_PREFIX = """[SYSTEM]
你是 RepoInsight 行为推断 Agent。根据用户提供的 README / ISSUE 模板 / 近期 PR 标题推断仓库的典型使用模式和核心模块。

## 输出规则
- 输出必须是合法 JSON
- 禁止输出 ```json 代码块包裹
- 禁止编造不存在的功能
- 若 README 信息不足以支撑某条 usage_pattern，直接减少条数（最少 1 条），不要补足
- 每条 usage_pattern.evidence 必须至少 8 字符且来自 README/ISSUE 原文

## 输出 JSON 格式
{{
  "usage_patterns": [{{"title": str, "description": str, "evidence": str}}],
  "core_modules": [{{"path": str, "role": str, "evidence": str}}],
  "inference_evidence": {{"claim1": "source_snippet1"}}
}}

## 示例（仅说明格式，非真实内容）

### 示例 A — 数据处理工具库
输入摘要：README 描述了一个 ETL 管道库，ISSUE 模板包含"pipeline_name"字段。
输出：
{{
  "usage_patterns": [
    {{
      "title": "构建批量 ETL 管道",
      "description": "用户通过 Pipeline.run() 串联 Source / Transform / Sink 三阶段",
      "evidence": "Pipeline.run() chains Source → Transform → Sink"
    }}
  ],
  "core_modules": [
    {{"path": "pipeline/core.py", "role": "主调度器，协调三阶段执行", "evidence": "core.py orchestrates Source → Transform → Sink"}}
  ],
  "inference_evidence": {{"etl_flow": "Pipeline.run() chains Source → Transform → Sink"}}
}}

### 示例 B — Web 框架
输入摘要：README 描述了轻量级 ASGI 框架，ISSUE 模板含"reproduction_steps"。
输出：
{{
  "usage_patterns": [
    {{
      "title": "定义路由与处理器",
      "description": "开发者通过 @app.route 装饰器注册 HTTP 端点",
      "evidence": "@app.route decorator registers HTTP endpoints"
    }},
    {{
      "title": "中间件注入",
      "description": "通过 app.use(middleware) 挂载跨切面逻辑",
      "evidence": "app.use(middleware) mounts cross-cutting logic"
    }}
  ],
  "core_modules": [
    {{"path": "framework/router.py", "role": "路由注册与分发", "evidence": "router.py dispatches requests to handlers"}},
    {{"path": "framework/middleware.py", "role": "中间件链管理", "evidence": "middleware.py manages the middleware chain"}}
  ],
  "inference_evidence": {{"routing": "@app.route decorator registers HTTP endpoints"}}
}}

### 示例 C — CLI 工具
输入摘要：README 描述了命令行代码格式化工具，PR 标题含 "fix: handle nested dicts"。
输出：
{{
  "usage_patterns": [
    {{
      "title": "格式化单文件",
      "description": "用户执行 `tool fmt <file>` 对单个 Python 文件进行格式化",
      "evidence": "tool fmt <file> formats a single Python file"
    }}
  ],
  "core_modules": [
    {{"path": "formatter/engine.py", "role": "AST 重写核心", "evidence": "engine.py rewrites AST nodes for formatting"}}
  ],
  "inference_evidence": {{"cli_usage": "tool fmt <file> formats a single Python file"}}
}}

### 示例 D — 消息队列客户端
输入摘要：README 描述了异步消息队列 SDK，ISSUE 模板含 "queue_name" 和 "message_payload" 字段。PR 标题含 "feat: dead-letter queue support"。
输出：
{{
  "usage_patterns": [
    {{
      "title": "发布消息到队列",
      "description": "生产者通过 `queue.publish(msg)` 将消息异步推送到指定队列",
      "evidence": "queue.publish(msg) pushes messages asynchronously to the named queue"
    }},
    {{
      "title": "消费并确认消息",
      "description": "消费者通过 `queue.consume(handler)` 注册回调，处理后调用 `ack()` 确认",
      "evidence": "queue.consume(handler) registers callback; ack() confirms processing"
    }},
    {{
      "title": "死信队列重试",
      "description": "超过重试次数的消息自动路由到死信队列，可通过 DLQ 检视器重放",
      "evidence": "dead-letter queue support added in recent PR: feat: dead-letter queue support"
    }}
  ],
  "core_modules": [
    {{"path": "client/producer.py", "role": "消息发布与序列化", "evidence": "producer.py handles publish and serialization"}},
    {{"path": "client/consumer.py", "role": "消息消费与 ACK 管理", "evidence": "consumer.py manages consume loop and ack"}},
    {{"path": "client/dlq.py", "role": "死信队列检视与重放", "evidence": "dlq.py implements dead-letter queue inspection"}}
  ],
  "inference_evidence": {{
    "publish_flow": "queue.publish(msg) pushes messages asynchronously to the named queue",
    "consume_flow": "queue.consume(handler) registers callback; ack() confirms processing",
    "dlq": "dead-letter queue support added in recent PR"
  }}
}}

### 示例 E — 数据库 ORM
输入摘要：README 描述了 Python 异步 ORM，ISSUE 模板含 "model_definition" 和 "query_expression" 字段。PR 标题含 "fix: N+1 eager load" 和 "feat: bulk_insert"。
输出：
{{
  "usage_patterns": [
    {{
      "title": "定义数据模型",
      "description": "开发者继承 `Model` 基类并声明字段，框架自动生成 DDL",
      "evidence": "class User(Model): id = IntField(primary=True) — Model DDL auto-generated"
    }},
    {{
      "title": "执行异步查询",
      "description": "通过 `await Model.filter(...).all()` 构造链式查询，返回 Pydantic 对象列表",
      "evidence": "await Model.filter(...).all() returns list of Pydantic objects"
    }},
    {{
      "title": "批量写入优化",
      "description": "通过 `Model.bulk_insert(records)` 一次性插入大批数据，避免逐条 INSERT 的性能瓶颈",
      "evidence": "feat: bulk_insert — single-call batch insert for large datasets"
    }}
  ],
  "core_modules": [
    {{"path": "orm/base_model.py", "role": "Model 基类与字段描述符", "evidence": "base_model.py defines Model base class and field descriptors"}},
    {{"path": "orm/queryset.py", "role": "链式查询构建器", "evidence": "queryset.py implements chainable query builder"}},
    {{"path": "orm/executor.py", "role": "SQL 生成与异步执行", "evidence": "executor.py generates SQL and runs async DB calls"}}
  ],
  "inference_evidence": {{
    "model_definition": "class User(Model) DDL auto-generated from field declarations",
    "async_query": "await Model.filter(...).all() returns list of Pydantic objects",
    "bulk_insert": "feat: bulk_insert — single-call batch insert for large datasets"
  }}
}}

[USER]
请根据以下仓库数据进行推断：
"""

_DYNAMIC_TEMPLATE = """README:
{readme}

ISSUE 模板:
{issue_templates}

近期 PR 标题:
{pr_titles}
"""


class BehaviorInferer(BaseAgent):
    """Reads README/ISSUE templates/recent PRs and calls LLM to infer usage patterns."""

    name = "behavior_inferer"

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        cache: LLMCache | None = None,
        input_guardrail: InputGuardrail | None = None,
        repo_map: RepoMap | None = None,
    ) -> None:
        self.llm_provider = llm_provider
        self.cache = cache
        self.input_guardrail = input_guardrail or InputGuardrail()
        self.repo_map = repo_map or RepoMap()
        # Counters populated by the most recent _build_prompt call so the
        # Planner can fold them into GuardrailTelemetry.
        self.last_input_secrets_redacted: int = 0
        self.last_input_injections_blocked: int = 0

    async def run(self, input_data: BehaviorInfererInput) -> BehaviorResult:
        return await self.infer(input_data)

    async def infer(self, input_data: BehaviorInfererInput) -> BehaviorResult:
        if self.llm_provider is None or self.cache is None:
            raise BehaviorInferenceError(
                "BehaviorInferer requires llm_provider and cache to be configured"
            )

        start_ms = time.monotonic()

        readme = self._load_readme(input_data.repo_path, input_data.readme_path)
        issue_templates = self._load_issue_templates(input_data.repo_path)
        pr_titles = await self._load_pr_titles(input_data)

        repo_map_result: RepoMapResult = await self.repo_map.build(input_data.repo_path)
        prompt = self._build_prompt(readme, issue_templates, pr_titles, repo_map_result)

        cache_key = CacheKey(
            repo_url=input_data.source_url or input_data.repo_path,
            agent_name=self.name,
            file_contents_hash=hashlib.sha256(
                "\x00".join([readme, issue_templates, "\n".join(pr_titles)]).encode("utf-8")
            ).hexdigest(),
            prompt_version=_PROMPT_VERSION,
            model_name=input_data.llm_model,
            temperature_int=0,
        )
        cache_key_str = cache_key.to_string()

        cached = None if input_data.force_refresh else await self.cache.get(cache_key_str)
        if cached is not None:
            raw_output = cached
        else:
            raw_output = await self.llm_provider.complete(
                prompt=prompt,
                response_format={"type": "json_object"},
                temperature=0.0,
                model=input_data.llm_model,
            )
            await self.cache.set(cache_key_str, raw_output)

        duration_ms = int((time.monotonic() - start_ms) * 1000)
        return self._parse_to_behavior_result(
            raw_output,
            job_id=input_data.job_id,
            duration_ms=duration_ms,
            repo_map_result=repo_map_result,
        )

    # ------------------------------------------------------------------
    # Data collection helpers
    # ------------------------------------------------------------------

    def _load_readme(self, repo_path: str, override_path: str | None = None) -> str:
        if override_path:
            try:
                text = Path(override_path).read_text(encoding="utf-8", errors="replace")
                return text[:_README_MAX_CHARS]
            except OSError:
                return ""

        if not repo_path or not os.path.isdir(repo_path):
            return ""

        matches = sorted(glob.glob(os.path.join(repo_path, "README*")))
        if not matches:
            return ""
        try:
            text = Path(matches[0]).read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
        return text[:_README_MAX_CHARS]

    def _load_issue_templates(self, repo_path: str) -> str:
        if not repo_path or not os.path.isdir(repo_path):
            return ""
        patterns = [
            os.path.join(repo_path, ".github", "ISSUE_TEMPLATE", "*.md"),
            os.path.join(repo_path, ".github", "ISSUE_TEMPLATE", "*.yml"),
            os.path.join(repo_path, ".github", "ISSUE_TEMPLATE", "*.yaml"),
        ]
        chunks: list[str] = []
        for pattern in patterns:
            for path in sorted(glob.glob(pattern)):
                try:
                    chunks.append(Path(path).read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    continue
        joined = "\n---\n".join(chunks)
        return joined[:_ISSUE_TEMPLATE_MAX_CHARS]

    async def _load_pr_titles(self, input_data: BehaviorInfererInput) -> list[str]:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            return []

        owner, repo = self._extract_owner_repo(input_data.repo_path)
        if not owner or not repo:
            return []

        try:
            import aiohttp

            url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
            headers = {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github.v3+json",
            }
            params = {"state": "all", "per_page": str(input_data.max_pr_count)}
            timeout = aiohttp.ClientTimeout(total=15)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status != 200:
                        logger.warning(
                            "github pulls API returned status %d for %s/%s",
                            resp.status, owner, repo,
                        )
                        return []
                    payload = await resp.json()
        except Exception as exc:
            logger.warning(
                "github pulls API fetch failed (best-effort, PR titles omitted): %s: %s",
                exc.__class__.__name__, exc,
            )
            return []

        titles: list[str] = []
        for pr in payload or []:
            title = pr.get("title") if isinstance(pr, dict) else None
            if title:
                titles.append(str(title))
        return titles[: input_data.max_pr_count]

    def _extract_owner_repo(self, repo_path: str) -> tuple[str | None, str | None]:
        if not repo_path:
            return None, None
        if repo_path.startswith("git@github.com:"):
            path = repo_path.replace("git@github.com:", "").rstrip("/").removesuffix(".git")
        elif repo_path.startswith("http://") or repo_path.startswith("https://"):
            parsed = urlparse(repo_path)
            if "github.com" not in parsed.netloc:
                return None, None
            path = parsed.path.lstrip("/").rstrip("/").removesuffix(".git")
        else:
            return None, None

        parts = path.split("/")
        if len(parts) >= 2 and parts[0] and parts[1]:
            return parts[0], parts[1]
        return None, None

    # ------------------------------------------------------------------
    # Prompt + parsing
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        readme: str,
        issue_templates: str,
        pr_titles: list[str],
        repo_map_result: RepoMapResult | None = None,
    ) -> str:
        secrets_redacted = 0
        injections_blocked = 0

        def _sanitize(text: str) -> str:
            nonlocal secrets_redacted, injections_blocked
            if not text:
                return text
            result: InputScanResult = self.input_guardrail.scan(text)
            if result.has_injection:
                injections_blocked += 1
            secrets_redacted += len(result.secrets)
            return result.cleaned_text

        readme_clean = _sanitize(readme)
        issue_clean = _sanitize(issue_templates)
        pr_clean: list[str] = []
        for title in pr_titles:
            pr_clean.append(_sanitize(title))

        self.last_input_secrets_redacted = secrets_redacted
        self.last_input_injections_blocked = injections_blocked

        candidate_hint = ""
        if repo_map_result and repo_map_result.candidate_core_modules:
            candidate_hint = (
                "\n\n[来自静态依赖图分析的可能核心模块候选（按被 import 次数排序）]\n"
                + "\n".join(
                    f"- {m}" for m in repo_map_result.candidate_core_modules[:10]
                )
                + "\n\n请优先从上述候选中选择核心模块。若选择候选外的模块，需在 evidence 中说明理由。"
            )

        readme_section = readme_clean or "(未找到 README)"
        issue_section = issue_clean or "(未找到 ISSUE 模板)"
        pr_section = "\n".join(f"- {t}" for t in pr_clean) if pr_clean else "(无)"
        dynamic = _DYNAMIC_TEMPLATE.format(
            readme=readme_section,
            issue_templates=issue_section,
            pr_titles=pr_section,
        )
        return _STATIC_PREFIX + dynamic + candidate_hint

    def _parse_to_behavior_result(
        self,
        raw_output: str,
        *,
        job_id: str,
        duration_ms: int,
        repo_map_result: RepoMapResult | None = None,
    ) -> BehaviorResult:
        try:
            payload = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            raise BehaviorInferenceError(
                f"LLM output is not valid JSON: {exc}"
            ) from exc

        if not isinstance(payload, dict):
            raise BehaviorInferenceError(
                "LLM output JSON root must be an object"
            )

        usage_raw = payload.get("usage_patterns") or []
        modules_raw = payload.get("core_modules") or []
        evidence_raw = payload.get("inference_evidence") or {}

        if not isinstance(usage_raw, list) or not isinstance(modules_raw, list):
            raise BehaviorInferenceError(
                "usage_patterns / core_modules must be arrays"
            )

        usage_patterns: list[str] = []
        inference_evidence: dict[str, str] = {}
        for idx, item in enumerate(usage_raw):
            if isinstance(item, dict):
                title = str(item.get("title", "")).strip()
                description = str(item.get("description", "")).strip()
                evidence = str(item.get("evidence", "")).strip()
                label = title or f"usage_pattern_{idx + 1}"
                rendered = f"{label}: {description}" if description else label
                usage_patterns.append(rendered)
                if evidence:
                    inference_evidence[label] = evidence
            elif isinstance(item, str):
                usage_patterns.append(item.strip())

        candidates_set: set[str] = set(
            repo_map_result.candidate_core_modules if repo_map_result else []
        )
        core_modules: list[str] = []
        for idx, item in enumerate(modules_raw):
            if isinstance(item, dict):
                path_value = str(
                    item.get("path") or item.get("module_path") or ""
                ).strip()
                role = str(item.get("role", "")).strip()
                evidence = str(item.get("evidence", "")).strip()
                if not path_value:
                    continue
                label = f"{path_value} ({role})" if role else path_value
                core_modules.append(label)
                evidence_key = f"core_module::{path_value}"
                if evidence:
                    inference_evidence[evidence_key] = evidence
                # Annotate whether this module was anchored by the static repo map
                in_candidates = any(
                    path_value == c or path_value.endswith(c) or c.endswith(path_value)
                    for c in candidates_set
                )
                inference_evidence[f"{evidence_key}::from_repo_map"] = str(in_candidates)
            elif isinstance(item, str):
                core_modules.append(item.strip())

        if isinstance(evidence_raw, dict):
            for k, v in evidence_raw.items():
                if isinstance(k, str) and isinstance(v, str) and k and v:
                    inference_evidence.setdefault(k, v)

        try:
            return BehaviorResult(
                job_id=job_id,
                usage_patterns=usage_patterns,
                core_modules=core_modules,
                inference_evidence=inference_evidence,
                guardrail_passed=False,
                guardrail_warnings=[],
                duration_ms=duration_ms,
            )
        except Exception as exc:  # pydantic ValidationError
            raise BehaviorInferenceError(
                f"Failed to validate BehaviorResult from LLM output: {exc}"
            ) from exc


__all__ = ["BehaviorInferer", "BehaviorInferenceError"]
