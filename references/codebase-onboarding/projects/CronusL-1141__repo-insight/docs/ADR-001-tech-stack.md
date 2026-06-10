# ADR-001: 技术栈与模块划分

## Status

Accepted — 2026-04-12

## Context

RepoInsight 需要在 120 秒内完成 Python 仓库的多维分析（静态质量、行为推断、社区健康），并通过浏览器实时展示进度与可交互报告。系统约束：

- 4 个 Agent 必须可独立运行/独立测试/独立替换
- 总预算 120s，必须支持 4 路并发
- 前端需要实时进度条（不能仅轮询）
- LLM 输出必须经幻觉防护，且 Provider 可替换
- 单机 Docker Compose 部署，无外部数据库依赖
- 团队 Python + React 经验充足，无 Rust/Go 储备

本 ADR 锁定项目的全部技术选型，是 [ARCHITECTURE.md](./ARCHITECTURE.md) 的决策依据。

## Decision Drivers

- **并发能力**：4 Agent 并行 + WebSocket 推送 → 必须原生支持 async I/O
- **契约一致**：前后端共享类型定义，避免接口漂移
- **可替换性**：LLM Provider、向量化模型、Agent 实现都需可替换
- **运维简洁**：单机 Compose、零外部依赖、开发即生产
- **团队熟悉度**：避免引入需要长学习曲线的新栈

## Decision

| 层 | 选型 | 关键理由（一句话） |
|---|---|---|
| Python 运行时 | **Python 3.12** | 性能最优、`asyncio` 改进、`TaskGroup` 原生支持 |
| 包管理 | **uv** | 比 pip/poetry 快 10-100 倍，单一 lockfile，CI 友好 |
| Web 框架 | **FastAPI + uvicorn** | 原生 async、Pydantic 集成、WebSocket 一等公民 |
| 并发模型 | **asyncio + asyncio.gather** | 4 Agent 天然并发，与 FastAPI 同事件循环 |
| 实时推送 | **WebSocket** | 双向、低延迟、浏览器原生支持 |
| 数据契约 | **Pydantic v2** | 性能 5-50 倍提升，前后端类型同源 |
| 静态分析 | **pylint + radon + coverage** | Python 生态事实标准，规则可调 |
| LLM | **OpenAI GPT-5.4（抽象 Provider 层）** | 主流能力最强；通过 `LLMProvider` 基类隔离便于切换 |
| 语义相似度 | **sentence-transformers all-MiniLM-L6-v2** | 22MB 小模型、CPU 可跑、384 维向量足够 Guardrail 阈值判定 |
| 持久化 | **SQLite** | 零运维、文件即数据库、满足审计 + LLM 缓存场景 |
| 前端构建 | **Vite + React 18 + TypeScript** | 冷启动 < 1s、HMR 极快、TS 与 Pydantic 类型对齐 |
| 样式 | **TailwindCSS + shadcn/ui** | 原子类 + 可拥有源码的组件，无运行时样式开销 |
| 图表 | **ECharts + react-echarts** | 热力图能力业界最强、社区活跃、配置驱动 |
| 报告渲染 | **react-html-parser + DOMPurify** | 后端产 HTML，前端安全注入，避免 XSS |
| 容器化 | **Docker Compose（3 服务）** | 单机部署、声明式、开发即生产 |

## Consequences

### Positive

- **开发速度快**：FastAPI + Pydantic + Vite 的组合让契约-到-UI 的反馈环 < 5s
- **Agent 解耦彻底**：`asyncio.gather` + Pydantic 输出 Schema 让 4 Agent 真正可独立替换
- **类型贯通**：Pydantic Schema → JSON Schema → TS 类型，前后端零类型漂移
- **零外部依赖**：SQLite + 本地 sentence-transformers，Compose `up` 即可演示
- **运维成本极低**：3 个容器、1 个 `.env`、2 个 volume

### Negative / Risks

- **SQLite 写并发上限**：单机单写者，若未来日均分析量 > 10k 需迁移 Postgres（已记录为待评估项）
- **sentence-transformers 冷启动**：首次加载模型约 3-5s，需预热（在 `main.py` lifespan 钩子中 warmup）
- **OpenAI 单点**：网络异常 → BehaviorInferer 完全失败；通过 LLM 缓存 + Provider 抽象缓解，未来可加 Anthropic 备用
- **WebSocket 与 nginx**：需在 nginx 配置 `proxy_set_header Upgrade`，部署文档需明确

## Alternatives Considered

### Python 包管理：pip vs poetry vs **uv**
- **pip**：无 lockfile、依赖解析慢、CI 缓存复杂 → 弃
- **poetry**：成熟但解析慢（大依赖图 30s+）、虚拟环境管理重 → 弃
- **uv**：Rust 实现、速度碾压、原生 lockfile → **选**

### Web 框架：Flask + SSE vs **FastAPI + WebSocket**
- **Flask + SSE**：单向推送够用，但 Flask 原生不支持 async，需 gevent monkey patch；Pydantic 集成需手写 → 弃
- **FastAPI + WebSocket**：原生 async、Pydantic 一等公民、WebSocket 双向（未来支持用户中断分析）→ **选**

### 数据契约：dataclass / attrs vs **Pydantic v2**
- **dataclass / attrs**：轻量但无校验、无 JSON Schema 导出、与 FastAPI 集成需额外转换 → 弃
- **Pydantic v2**：v2 用 Rust 重写性能反超、原生 JSON Schema、FastAPI 深度集成 → **选**

### 持久化：PostgreSQL vs **SQLite**
- **PostgreSQL**：并发写强、生态丰富，但需独立容器、独立卷、独立运维；当前场景无并发写需求 → 弃
- **SQLite**：单文件、零运维、`aiosqlite` 支持 async、写并发瓶颈在远期 → **选**（已为迁移留出 Repository 接口层）

### 静态分析：ruff + pyright vs **pylint + radon**
- **ruff + pyright**：极快但 ruff 不产圈复杂度指标、pyright 偏类型不偏质量；二者均不输出 radon 风格的可维护性指数 → 弃
- **pylint + radon**：pylint 规则覆盖最广、radon 是圈复杂度/MI 的事实标准；速度劣势可由缓存 + 并发抵消 → **选**

### LLM 接入：直接 SDK vs **抽象 Provider 层**
- **直接调用 openai SDK**：开发最快，但更换模型需全局改动；测试需要真实 API → 弃
- **抽象 Provider 基类**：增加 < 100 行代码，换来可替换性 + Mock 测试能力 + 多 Provider 故障转移空间 → **选**

### 语义层：TF-IDF cosine vs **sentence-transformers MiniLM**
- **TF-IDF**：纯统计、无依赖，但对同义改写无能（"使用方法" vs "调用方式"会被判低相似）→ 弃
- **MiniLM all-MiniLM-L6-v2**：22MB、CPU < 50ms/句、语义对齐能力足够 Guardrail 阈值判定 → **选**

### 前端构建：Next.js vs Create React App vs **Vite**
- **Next.js**：SSR/SSG 能力对纯 SPA 报告浏览过度 → 弃
- **CRA**：已被 React 团队归档、构建慢 → 弃
- **Vite**：冷启动 < 1s、HMR 毫秒级、TS 开箱即用 → **选**

### 部署：Kubernetes vs 裸进程 vs **Docker Compose**
- **Kubernetes**：单机演示场景过重，运维成本失衡 → 弃
- **裸进程**：环境差异大、缺乏隔离 → 弃
- **Docker Compose**：3 服务、1 文件、`up` 即跑、开发即生产 → **选**

## References

- [ARCHITECTURE.md](./ARCHITECTURE.md) — 模块职责清单与时序图
- [CLAUDE.md](../CLAUDE.md) — 项目约束（已锁定的技术栈表格）
- 后续 ADR 占位：ADR-002 Agent 通信协议 / ADR-003 Guardrail 设计 / ADR-004 前端实时进度协议
