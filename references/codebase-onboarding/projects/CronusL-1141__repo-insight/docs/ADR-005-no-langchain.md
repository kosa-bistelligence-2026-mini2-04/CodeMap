# ADR-005：为什么不使用 LangChain

- 状态：Accepted
- 日期：2026-04
- 作者：RepoInsight 团队

## Context

RepoInsight 的核心执行路径是一个**固定的、一次性的并发管线**：

- 4 个角色固定（StaticAnalyzer / BehaviorInferer / CommunityAssessor / Reporter）
- 执行拓扑固定：前 3 个 Agent `asyncio.gather` 并发，Reporter 串行消费
- LLM 调用点极少：仅 BehaviorInferer 与 ConflictResolver 判官两个位置
- 无多轮对话、无工具路由、无 Agent 自主规划、无 ReAct 循环
- 总预算 120s，对依赖体积与冷启动时间敏感（Docker 镜像 + CI 分发）

在这种前提下，需要评估：是否引入 LangChain / LlamaIndex / CrewAI / LangGraph 等 Agent 编排框架。

## Decision

**不使用任何 Agent 编排框架，直接用 `asyncio.gather` + OpenAI SDK 原生调用构建管线。**

具体落地：

- 编排层：`app/orchestrator/planner.py` 自写，基于 `asyncio.gather` + `asyncio.wait_for`
- LLM 层：`app/llm/openai_provider.py` 直接封装 `openai` 官方 SDK，提供 `async generate(prompt) -> str` 抽象
- Prompt：每个 Agent 各自维护纯字符串模板（`f-string` + 显式拼装），不引入模板引擎
- 缓存：自写 `LLMCache`（SQLite + aiosqlite），详见 ADR-006

## Alternatives

| 候选 | 拒绝原因 |
|---|---|
| **LangChain** | 依赖体积大（含 transitive ~200MB+），抽象层深，堆栈难调试；固定管线用不上 Chains / Memory / Tools 的动态编排能力 |
| **LlamaIndex** | 定位是 RAG / 索引框架，RepoInsight 不做向量检索，核心价值点不匹配 |
| **CrewAI** | 面向"自主 Agent 角色扮演 + 多轮协商"，而 RepoInsight 的"协商"只是 ConflictResolver 一次 LLM 判官调用，用框架是杀鸡用牛刀 |
| **LangGraph** | 状态图编排适合分支/循环/回退的复杂工作流，而本项目拓扑是线性 DAG，`asyncio.gather` 16 行代码即可表达 |

## Consequences

### Pros

- **最小依赖**：核心运行时仅 `openai` + `aiosqlite` + `fastapi`，镜像层约 5MB 量级（vs LangChain 全家桶 ~200MB），冷启动与 CI 构建显著更快
- **完全可控**：重试、超时、缓存、审计、Token 计费全部在自己的代码里，无"框架黑盒"
- **清晰堆栈**：异常栈直接指向业务代码，不会穿过 3-5 层框架回调；调试 LLM 幻觉与缓存命中问题效率高
- **直接调试**：Prompt 就是普通字符串，可以直接 `print` 或写入 SQLite 审计表，无需 LangSmith 等额外工具
- **易于替换 Provider**：`Provider` 抽象层只有 `generate()` 一个方法，换 Anthropic / 本地模型只需新增一个文件

### Cons

- **手写 prompt 模板**：无 `PromptTemplate` / `ChatPromptTemplate` 等现成抽象，需要自己维护模板与变量注入（可接受：Agent 总数固定为 2 个 LLM 调用点）
- **无现成 memory 抽象**：如果未来需要多轮对话式 Agent，需要自己实现 `ConversationBufferMemory` 等能力（当前非目标）
- **无社区预制组件**：不能直接复用 LangChain Hub 的 Prompt / Tool，但本项目的 Prompt 都是领域特定（仓库风险评估），复用价值低

## 核心论点

> **固定 pipeline 不受益于动态 chain-of-thought 框架。**

LangChain 等框架的核心价值在于运行时动态组装 LLM 调用链（Tool Calling 路由、Agent 自主规划、状态回放）。RepoInsight 的执行计划在编译期就已完全确定——4 个 Agent、2 个 LLM 调用点、1 个冲突协商触发条件。把静态 DAG 放进动态编排框架，只会付出抽象层成本而拿不到任何动态收益。

当未来业务出现以下任一情形时，本决策应被重新评估：

1. Agent 数量变为动态发现（用户可插件化注册新 Agent）
2. 出现"Agent 调用 Agent"的多轮对话
3. 需要基于运行时结果做分支/回退的复杂工作流
