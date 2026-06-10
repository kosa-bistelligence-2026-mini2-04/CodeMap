# ADR-006：多层缓存设计

- 状态：Accepted
- 日期：2026-04
- 作者：RepoInsight 团队

## Context

RepoInsight 的分析管线同时面对多种重复访问模式：

- 同一仓库在 24h 内被多次分析（开发者迭代调试）
- 同一 LLM Prompt 在不同任务间高度相似（Prompt 前缀 80%+ 重复）
- CommunityAssessor 可能超过 45s 预算，需要可回填的降级数据源
- 历史报告需要永久可查询（用户查看过往分析）

不同访问模式有完全不同的 TTL、Key 形状、一致性要求与失效策略，放在同一层缓存会互相污染。

## Decision

**采用 4 层独立缓存，各自解决一个明确问题，互不串线。**

### 缓存分层职责表

| 层 | 位置 | TTL | Key / Scope | 目的 |
|---|---|---|---|---|
| **L1 — OpenAI Prompt Cache** | 服务端（OpenAI 侧） | 由 OpenAI 管理（~5 分钟滑窗） | 基于 Prompt 前缀自动匹配 | 降低重复 Prompt 前缀的 Token 计费与首 token 延迟 |
| **L2 — LLMCache** | 本地 SQLite（`llm_cache.db`） | **24h** | SHA256(repo_url, agent, content_hash, prompt_version, model, temperature_int) | 响应级缓存：同仓库同 Agent 24h 内完全跳过 LLM 调用 |
| **L3 — TimeoutGuard community_cache** | 本地 SQLite（`community_cache.db`） | **24h** | SHA256(repo_path) | CommunityAssessor 超 45s 时的降级 fallback；命中即返回缓存值，未命中走历史均值 |
| **L4 — AnalysisStore** | 本地 SQLite（`analyses.db`） | **永久** | `job_id` 主键 | 历史报告持久化，支撑 `GET /api/analyses` 列表与详情查询 |

### 为何不统一

4 层看起来都是"缓存"，但它们的语义完全不同，强行合并会带来 Key 设计冲突与 TTL 策略打架：

- **访问模式不同**：L1 是前缀匹配（近似）、L2 是精确 6 维键、L3 是仓库级降级触发、L4 是主键持久化
- **TTL 不同**：L1 约 5 分钟、L2/L3 是 24 小时、L4 永久
- **失效代价不同**：L1 失效只是多付几个 token；L2 失效会重新烧钱调 LLM；L3 失效触发 45s 超时分支；L4 失效意味着历史丢失
- **一致性关切不同**：L4 要求强持久化（SQLite WAL），L1/L2 可容忍偶发 miss，L3 允许返回过期值（因为它本身就是降级分支）

分层的代价是"4 个 SQLite 文件"，收益是"每层关注点单一、可独立调优与清理"，工程上明显划算。

## Cache Key 设计（L2 LLMCache）

响应级缓存命中率直接决定 Token 成本，因此 Key 必须足够精确：

```python
CacheKey(
    repo_url: str,           # 仓库标识（见下方归一化）
    agent_name: str,         # "static_analyzer" / "behavior_inferer" / ...
    file_contents_hash: str, # SHA256(拼接后的源文件文本)，文件变化即失效
    prompt_version: str,     # "v1"，Prompt 模板升级时手动 bump
    model_name: str,         # "gpt-5.4"，换模型即换 Key
    temperature_int: int,    # int(temperature * 100)，避免浮点键
)
```

**组合成字符串后 SHA256 截取 32 字符作为最终 Key：**

```
hashlib.sha256("|".join([...])).hexdigest()[:32]
```

6 个维度缺一不可：

- 漏掉 `content_hash` → 文件改了还拿旧答案
- 漏掉 `prompt_version` → Prompt 升级后旧缓存污染
- 漏掉 `model_name` → 换模型拿到错误风格的回答
- 漏掉 `temperature` → 确定性调用和创意调用混用

## Repo URL 归一化

`repo_url` 在 Key 中必须先归一化，否则 `https://github.com/foo/bar`、`https://github.com/FOO/bar.git`、`https://github.com/foo/bar/` 会产生 3 个不同 Key，缓存命中率近乎为零（BUG-R4 修复点）。

```python
def _normalize_repo_url(url: str) -> str:
    normalized = url.strip().lower().replace("\\", "/").rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    return normalized
```

归一化规则：

1. `lower()` — Windows 路径与 GitHub URL 都大小写不敏感
2. `\\` → `/` — 统一路径分隔符（Windows 本地路径）
3. 去掉末尾 `/` — URL 末斜杠无语义差异
4. 去掉 `.git` 后缀 — `foo/bar` 与 `foo/bar.git` 是同一仓库

## Consequences

- 每层有独立的 SQLite 文件，便于 `rm` 单独清理（例如只清 L2 不影响历史记录）
- `LLMCache` 与 `TimeoutGuard` 的 Key 归一化逻辑需在单元测试中锁定，防止回归
- L1 依赖 OpenAI 侧实现，不可见但可通过 `cache_hit` 字段观测（已接入 `ObservabilityCollector`）
- 未来若接入 Redis，只需替换 L2 的存储后端，Key 结构保持不变
