# 研究 #2 — 多 Agent 编排框架对标与 RepoInsight Planner 优化建议

> 作者：researcher-2
> 日期：2026-04-14
> 关联：ADR-002（Agent 通信协议与 Planner 编排）、ARCHITECTURE.md、STAGE3-PLAN.md
> 对标文件：
> - `backend/app/orchestrator/planner.py`
> - `backend/app/orchestrator/conflict_resolver.py`
> - `backend/app/orchestrator/timeout_guard.py`

---

## 0. 概述与动机

RepoInsight 的 Planner 目前是一个"一次性 asyncio.gather + 事后降级"的轻量编排器。设计目标明确：

1. **120s 总预算 / 三采集 Agent 并行 + Reporter 串行**；
2. **单 Agent 失败不应阻塞整体**（CommunityAssessor 允许降级）；
3. **冲突消解通过 LLM Judge**（StaticAnalyzer 的 `high_risk_modules` ∩ BehaviorInferer 的 `core_modules` 触发）；
4. **Guardrail 仅在 Planner 层注入**，BI 不直接 import guardrail，保持依赖方向 DAG 干净；
5. **JudgeGuardrail 子类**（ai-13 R2 衍生 2）避免元循环误拦。

这些选择在「7 天笔试交付」场景下是合理的，但同时也意味着我们有意抛弃了许多主流框架提供的能力（状态持久化、断点恢复、conditional edges、动态 speaker 选举、debate 聚合……）。本研究针对 8 个主流多 Agent 编排框架逐一对标，目的不是"推翻自研 Planner"，而是**找到可以以小代价反向吸收的设计点**，并给出 10 条具体可操作的优化建议，分优先级（P0/P1/P2）标注。

研究覆盖的框架：

| # | 框架 | 主推定位 | 出品方 |
|---|---|---|---|
| 1 | LangGraph | 图式状态机 + Supersteps | LangChain |
| 2 | AutoGen / Microsoft Agent Framework | 会话式多 Agent + GroupChat | Microsoft |
| 3 | CrewAI | 角色协作 + 任务链 | CrewAI Inc. |
| 4 | LangChain Agents (AgentExecutor) | 单 Agent 工具调用循环 | LangChain |
| 5 | MetaGPT | SOP 驱动 + 软件公司模拟 | DeepWisdom / Foundation Agents |
| 6 | OpenAI Swarm / Agents SDK | 轻量 handoff 路由 | OpenAI |
| 7 | BabyAGI / AutoGPT | 自主循环 + 任务队列 | 社区 |
| 8 | Dify / Flowise | 低代码可视化编排 | Dify / FlowiseAI |

---

## 1. 我们自己的编排：基线快照

为了让对比有锚点，先固定 RepoInsight Planner 在阶段 3 (2026-04-14) 的关键实现细节。以下均来自 `backend/app/orchestrator/planner.py` 与 `conflict_resolver.py`、`timeout_guard.py`。

### 1.1 编排模型

- **单次 fan-out + Reporter 串行**。三个采集 Agent（Static / Behavior / Community）通过 `asyncio.create_task` 包裹 `asyncio.wait_for` 启动，然后 `asyncio.gather(..., return_exceptions=True)` 收集结果。Reporter 在三者完成后才串行运行。
- 没有 conditional edges、没有状态图、没有 super-steps 的概念。
- **预算（硬编码）**：
  - `BUDGET_TOTAL_S = 120`
  - `BUDGET_STATIC_S = 30`
  - `BUDGET_BEHAVIOR_S = 60`
  - `BUDGET_COMMUNITY_S = 45`
  - `BUDGET_REPORTER_S = 15`

> 注意：单 Agent 预算之和（30+60+45+15 = 150）> 120，这是设计层面的"软超卖"——预期 Community 总会降级或 Behavior LLM 不会用满 60s。后面 §9 会建议把这个做成显式的"预算池"而非 magic number。

### 1.2 并发机制

纯 asyncio，运行在 FastAPI 的事件循环上。三个 Agent 本质上是 I/O bound（pylint 子进程 / LLM HTTP 调用 / git log 子进程），因此单 event loop 足够。没有 process pool，没有分布式调度。

### 1.3 超时控制

两级：
- **单 Agent**：`asyncio.wait_for(agent.run(...), timeout=BUDGET_XXX_S)`。触发时抛 `TimeoutError` / `asyncio.TimeoutError`。
- **总预算**：在 Reporter 启动前检查 `elapsed >= BUDGET_TOTAL_S - 2`，超则抛 `BudgetExhaustedError`；Reporter 的超时用 `min(BUDGET_REPORTER_S, BUDGET_TOTAL_S - elapsed - 2)` 动态收窄。

### 1.4 降级策略（只对 Community 生效）

`_handle_community` 三分支：
```python
if isinstance(result, asyncio.CancelledError):
    raise result                      # 重抛，保留 event loop 取消语义
if isinstance(result, (TimeoutError, asyncio.TimeoutError)):
    return timeout_guard.get_degraded_community(...)
if isinstance(result, BaseException):
    return timeout_guard.get_degraded_community(...)  # 未知错误也降级
return result
```

`TimeoutGuard.get_degraded_community` 查 SQLite 缓存（`repo_hash`，24h TTL）→ 命中返回 cache；未命中返回**历史均值常量**（commits_per_week=3.5, unique_contributors=2）。
Static / Behavior / Reporter 失败**不**降级，直接上抛给 FastAPI 路由。

### 1.5 冲突消解（LLM Judge）

`ConflictResolver.detect_conflicts` 基于 **top-level 模块字符串集合运算**（`_normalize_module` 做路径规范化）。触发后对每个冲突模块独立调用一次 LLM（`temperature=0.0`，强制 JSON 输出）。
`JudgeGuardrail`（`ai-13 R2 衍生 2`）是 `GuardrailValidator` 的子类，source_text 改用 `static_view + behavior_view` 组合，跳过"未来时态"regex（避免 judge 输出含"monitor in the next quarter"被 regex 误杀），新增"判官越权"regex（禁止 judge 直接下 refactor 指令）。LLM 调用失败 → `final_recommendation` 回退为固定模板。

### 1.6 错误恢复

- Static/Behavior/Reporter 失败：**直接让 pipeline 死**，FastAPI 路由返回 5xx。
- Community 失败：降级为历史均值。
- LLM Judge 失败：返回固定模板文本。
- **没有重试、没有断点恢复、没有状态持久化**。一个 job 从 clone 到 report 全程在内存里走完，失败就重头来。

### 1.7 工具调用抽象

- 没有"工具"概念。每个 Agent 是直接 Python 类（`StaticAnalyzer.run` / `BehaviorInferer.infer` / `CommunityAssessor.run`），Planner 通过 `TYPE_CHECKING` 导入类型、构造函数接收实例（DI 友好）。
- LLM 调用在 `llm/provider.py` 抽象，所有 Agent（其实只有 BI 和 ConflictResolver）共享同一个 provider。
- Guardrail 调用**只在 Planner 层显式 await** `self.guardrail.validate(...)`，不走任何 middleware/hook。

### 1.8 已有优势 vs 已知缺口

| 维度 | 现状评价 | 备注 |
|---|---|---|
| 并发简洁度 | **强** | 整个编排器 < 150 行 |
| 依赖方向清洁 | **强** | lint-imports DAG 零违规（arch-13 R1 §三） |
| 超时硬切 | **强** | 双层超时，Reporter 动态收窄 |
| 降级颗粒度 | 中 | 只有 Community 会降级，其他 Agent 失败 = 整体死 |
| 状态持久化 | **弱** | 无 checkpoint，失败必须重跑 |
| 观测性 | 中 | 依赖 ObservabilityCollector（ai-13 R2 衍生 3），但缺每节点细粒度 |
| 可扩展性 | 中 | 新增第 5 个 Agent 需要改 Planner 硬编码 |
| 动态路由 | **无** | 无 conditional edges / handoff |
| 重试策略 | 弱 | 只有 LLM Provider 层重试，编排层无 |

---

## 2. 框架对标 — LangGraph

### 2.1 编排模型

LangGraph 的核心抽象是 **StateGraph**：一个有向图，节点是函数（同步或 async），边可以是静态（`add_edge`）或条件（`add_conditional_edges`）。整个图有一个共享的 **State**，由用户用 `TypedDict` 或 Pydantic 定义，节点通过返回部分 state 更新驱动推进。

- **Super-step** 语义：编译后的图以 "super-step" 为单位推进，一个 super-step 内所有可并发的节点并行执行，全部完成后 state 更新一次性落盘，然后进入下一 super-step。这和 Google Pregel 的 bulk synchronous parallel 一脉相承。
- **Send API / map-reduce**：条件边可以返回 `Send(node_name, partial_state)` 对象列表，实现动态 fan-out（数量在运行时决定）。对应的 reducer（在 state 的 `Annotated[list, add]` 上声明）负责把 fan-in 结果合并。
- **Defer'd nodes** / deferred execution：可以声明"这个节点等所有其他分支完成再执行"，非常适合我们 Reporter 这种"等三个 Agent 都好了再跑"的场景。

### 2.2 并发机制

单 event loop + `asyncio.gather` 并行执行一个 super-step 内的节点。这和我们 Planner 的底层机制**完全一致**。差别是 LangGraph 在 gather 外面加了：
- Checkpoint（state 写入 SqliteSaver / PostgresSaver / MemorySaver）
- Interrupt 机制（human-in-the-loop）
- Streaming events（节点级进度）

### 2.3 超时控制

LangGraph 原生**没有**总预算硬切。它给每个节点传 `config={"configurable": {...}, "recursion_limit": 25}`，防止图走到无限循环；但没有"整图 120 秒死"。社区最佳实践：在顶层 `graph.ainvoke(...)` 外面包 `asyncio.wait_for` —— 和我们做法一样。

### 2.4 冲突消解

LangGraph 本身**不提供** conflict resolution 原语。想做多 Agent 结果仲裁，官方示例是"再加一个 node 用 LLM 比较两边"——本质上就是我们 `ConflictResolver.resolve`。近期社区讨论的 Multi-Agent Debate（MAD）框架（arxiv 2510.12697）也是在 LangGraph 上手写的。

### 2.5 错误恢复

这是 LangGraph 相对我们的**主要优势**：
- **Checkpoint 持久化**：每个 super-step 后 state 写入 checkpointer。单节点崩溃，重跑 `graph.ainvoke(..., config={"thread_id": ...})` 会从上次 checkpoint 继续，不是重头来。
- **Per-node retry policy**：`add_node(name, func, retry=RetryPolicy(max_attempts=3, backoff_factor=2.0))`。
- **Durable execution**：节点内部如果用 LangChain 的 `RunnableConfig` 呼叫 LLM，失败可自动按策略重试。

### 2.6 工具调用抽象

LangGraph 本身不定义工具——工具是 LangChain `Tool` 对象，在节点内通过 `ToolNode` 或 `.bind_tools(...)` 装入 LLM。对我们而言，工具这一层和我们无关（我们的 Agent 不需要让 LLM 决定"调用 pylint"还是"调用 radon"），但有个细节值得学：**LangChain 给 tool 定义了统一的 `args_schema`（Pydantic）**，天然可被 LLM function-calling 消费。我们现在的 Agent 输入 Schema 也是 Pydantic（`StaticAnalyzerInput` 等），只差一步"暴露成 LLM tool definition" 就能复用。

### 2.7 我们相对如何 / 可借鉴

| 点 | LangGraph | RepoInsight | 差距评估 |
|---|---|---|---|
| 并发底层 | asyncio.gather | asyncio.gather | 等 |
| 动态 fan-out | Send API | 无（Agent 数量编译期固定） | 我们暂时不需要 |
| Checkpoint | SqliteSaver | 无 | **差距大**，但 120s 单 job 场景下收益有限 |
| 节点级 retry | RetryPolicy | 无 | **可借鉴**：对 Community 失败先重试再降级 |
| 条件边 | add_conditional_edges | 无 | 可用于"BI 输出 guardrail_warnings > 3 则走兜底 prompt 重生成" |
| Defer'd node | deferred=True | Reporter 写死串行 | 语义等价，Reporter 无需改造 |
| 流式事件 | astream_events | ProgressBus 自造 | 等 |

**可借鉴的具体细节**：
1. 用 `dataclass` 或 `TypedDict` 显式建模 Planner 运行时 state（现在散落在局部变量），即便不上 checkpointer，也有利于 observability 和 debug replay。
2. 把 `_handle_community` 前置一次"指数退避重试"，再进降级分支——这个是 LangGraph `RetryPolicy` 的核心思路，我们完全可以用 tenacity 或自己 5 行写出来。
3. 学 Send API 的"reducer 合并"思想：未来如果增加第 5 个 Agent（比如 SecurityAuditor），把 `high_risk_modules` 的合并写成显式 reducer，避免散落的 `set()` 操作。

### 2.8 是否应该迁移到 LangGraph？

**不建议**。理由：
- 笔试项目代码量敏感，LangGraph 依赖链 > 20 个 sub-package，会让 `uv lock` 膨胀。
- 我们的场景是"一次性三路 fan-out + Reporter"，StateGraph 的全部威力（动态图、条件边、interrupt）都用不上，用了反而把 120 行的 Planner 变成 400 行。
- LangGraph 在 Windows 下 asyncio subprocess 的已知坑（LangGraph issue #5182 关于 defer-ed nodes 的 bug）尚未修复，我们 CI 包含 Windows runner。
- 我们现在的 Planner 实现和 LangGraph 的"super-step + gather + deferred"本质一致，**学习它的设计而不是依赖它的包**更划算。

---

## 3. 框架对标 — AutoGen / Microsoft Agent Framework

### 3.1 编排模型

AutoGen 0.2 的核心是 `ConversableAgent` + `GroupChat` + `GroupChatManager`。**编排模型是会话式**的：agents 轮流说话，GroupChatManager 决定"下一个说话的是谁"，整个过程是一个消息队列而不是图。

- **Speaker selection** 策略：`auto`（默认，由 manager LLM 选择）、`round_robin`、`random`、或自定义函数。
- **Termination condition**：`is_termination_msg` lambda，当某条消息满足条件（"TERMINATE" 关键词、max_round 达到、自定义 predicate）就停。
- AutoGen v0.4+ 引入了 `SelectorGroupChat`、声明式终止条件（`TextMentionTermination & MaxMessageTermination`），更接近 state machine。

**MAF（Microsoft Agent Framework，AutoGen 继任者）**：企业级重写，内建 error handling / retry / recovery、跨 runtime 互操作（.NET + Python）、多 provider 模型支持。

### 3.2 并发机制

AutoGen 0.2 本质是**单线程会话循环**，多 agent 是"按顺序轮流说话"，并不并发。要做并发得用 `GroupChat` 的变体或 AutoGen 0.4 的 actor 模型。MAF 宣称支持 actor-style 并发。

### 3.3 超时控制

通过 `llm_config` 的 `timeout` 和 `max_retries` 参数（issue #4904）。**没有 per-agent 运行预算**——这是会话式框架的通病，因为"一次对话多长"本质上是未知的。

### 3.4 冲突消解

AutoGen 没有内建 conflict resolution，但它的会话模型**天然适合 debate**：让两个 Agent 各说一遍，让第三个 Agent（judge）总结。这和学术界的 Multi-Agent Debate 框架一致，也是我们 ConflictResolver 的原型。差别是 AutoGen 把"谁先说话"交给 LLM 决策，我们是静态定好顺序。

### 3.5 错误恢复

AutoGen 0.2 issue #4904 明确承认"单 Agent 异常会级联"，推荐的做法是 try/except 包裹 initiate_chat。MAF 宣传"built-in error handling, retries, recovery"，但具体 API 还在早期。

### 3.6 工具调用抽象

`ConversableAgent.register_for_llm` / `register_for_execution`，把 Python 函数注册成 tool，LLM 通过 function calling 触发。抽象层次合理，但比 LangChain Tool 更散（每个 agent 可以有自己的 tool 集，也可以共享）。

### 3.7 我们相对如何 / 可借鉴

我们的场景**不是会话式**的（Agent 之间不聊天，只是各自出结果然后聚合），所以 AutoGen 的会话编排模型基本用不上。但有两点可借鉴：

1. **声明式终止条件（MaxMessageTermination / TextMentionTermination）**：我们的"120s 预算耗尽"是 if-elif 散落在代码里，可以抽象成一个 `BudgetTerminationCondition` 对象，传给 Planner 更清晰。
2. **Speaker selection 的"自定义函数"**：让我们的 ConflictResolver 触发逻辑（"哪些模块需要 judge"）从硬编码 `detect_conflicts` 升级为可插拔策略函数，比如按覆盖率 × 调用频率加权，只 judge top-3 最严重的冲突模块，控制 LLM 调用预算。

### 3.8 是否应该迁移到 AutoGen？

**坚决不**。AutoGen 的会话模型和我们的"三路 fan-out + Reporter"完全错位，迁移成本巨大且收益为零。MAF 尚在早期，企业特性对笔试交付没用。

---

## 4. 框架对标 — CrewAI

### 4.1 编排模型

CrewAI 把多 Agent 抽象为"人类团队"：Agent 有 `role` / `goal` / `backstory`，Task 有 `description` / `expected_output` / `agent`。Crew 把一组 Agent 和 Task 组装起来，通过 `process=Process.sequential` 或 `Process.hierarchical` 决定执行方式。

- Sequential：任务按顺序执行，上一个 task 的输出可以作为下一个 task 的 context。
- Hierarchical：manager agent 决定哪个 worker 处理哪个 task（但 GitHub issue #4783 报告了 hierarchical delegation 在近期版本的 bug）。
- **Async kickoff**：`crew.kickoff_async()` 支持异步运行，单 Crew 内部的 task 可以 `async_execution=True` 并发。

### 4.2 并发机制

`async_execution=True` 的 task 会用 asyncio 并发；底层仍然单 event loop。可以把三个 task 都标 async，然后用一个 sync task 做 aggregator。

### 4.3 超时控制

Agent 层 `max_execution_time`、LLM 层 `request_timeout`；Crew 层**没有**总预算。A2AClientConfig 支持 per-remote-agent 的 timeout（120s / 90s 示例），适合分布式场景。

### 4.4 冲突消解

**无原生 conflict resolution**。CrewAI 的哲学是"明确 role 边界"，假设 agents 不会冲突。出现冲突时的推荐做法是：再加一个 reviewer Agent 作为 hierarchical manager。这和 AutoGen 的 debate 模式类似。

### 4.5 错误恢复

`fail_fast` 参数控制 A2A 连接失败是否整体中止。单 task 失败没有原生重试；文档建议用 `max_iter` 限制 agent 自身循环次数，然后 try/except 包裹 kickoff。

### 4.6 工具调用抽象

LangChain 兼容的 `@tool` 装饰器 + CrewAI 自己的 `BaseTool`。Agent 创建时 `tools=[...]` 注入。比 AutoGen 的 register-based 模式更声明式。

### 4.7 我们相对如何 / 可借鉴

CrewAI 的 **`role/goal/backstory` 抽象** 是最有借鉴价值的点——它把 Agent 的系统 prompt 从一坨硬编码变成结构化 metadata，可以被 observability tooling 读取（"这次任务里 StaticAnalyzer 的 goal 是什么"）。我们现在 BehaviorInferer 的 system prompt 是写在 `prompts.py` 里的字符串常量，没法被前端或 audit 面板引用。

具体可借鉴：
1. 给每个 Agent 类加 `role: str`、`goal: str` 属性（不改实际逻辑），让 ObservabilityCollector 输出包含这些字段。
2. `async_execution=True` 的思想 = 我们 `asyncio.create_task`，完全等价，无需改造。
3. `Process.hierarchical` 的"manager 决定谁先跑"——我们的 Planner 其实是"编译期决定三者并发"，更快更简单。

### 4.8 是否应该迁移到 CrewAI？

**不建议**。同样的理由：依赖膨胀、hierarchical 有已知 bug、我们的场景不需要 dynamic delegation。

---

## 5. 框架对标 — LangChain Agents (AgentExecutor)

### 5.1 编排模型

传统 LangChain `AgentExecutor` 是**单个 Agent 的 ReAct loop**：LLM 输出 thought → action → observation → thought → ...，直到 `FinalAnswer` 或触发停止条件。不是真正的多 Agent 编排器，但在我们的上下文里值得对标，因为"LLM 决定下一步调用哪个工具"是很多现代 agent 的底层机制。

### 5.2 并发机制

单 agent 单循环，没有并发。如果要多 Agent，通常把 AgentExecutor 包成 LangGraph 的 node。

### 5.3 超时控制

两个参数：`max_iterations`（默认 15，超出返回"Agent stopped due to max iterations"）和 `max_execution_time`（wall-clock 秒数）。触发时有两种 early stopping 策略：
- `"force"`：直接返回固定字符串（默认）
- `"generate"`：再跑一次 LLM 让它生成一个兜底答复

### 5.4 冲突消解

N/A（单 agent）。

### 5.5 错误恢复

Middleware 层可以装 "retry model call" / "retry tool call"（LangChain v0.2+ 新加）。**工具调用失败时 observation 会把错误文本传回 LLM**，让 LLM 自己决定是否改用其他工具——这是 ReAct 的固有自愈机制，但不保证收敛。

### 5.6 工具调用抽象

这是 LangChain 的强项：`@tool` 装饰器、`BaseTool` 基类、Pydantic `args_schema` 自动转 OpenAI function calling。所有工具统一接口 `run(input: str) -> str` 或 `invoke(input: dict) -> Any`。

### 5.7 可借鉴

1. **`max_execution_time` + `early_stopping_method="generate"`**：我们现在 Reporter 超时就直接抛 `BudgetExhaustedError`，用户看到 500。如果借鉴 "generate" 策略——LLM 生成一份带"部分结果 + 超时说明"的兜底 HTML——用户体验会好很多。
2. **Middleware 风格的 retry**：我们 LLM Provider 已经有 `MAX_RETRIES=2`（ai-13 R1 §1），这个思想在编排层也可以用——把 `_handle_community` 的降级分支改成 `retry + fallback` 两段式。

### 5.8 是否应该迁移？

N/A——AgentExecutor 不是多 agent 框架，对标意义在于 early-stopping 策略和 retry middleware。

---

## 6. 框架对标 — MetaGPT

### 6.1 编排模型

MetaGPT 把"一个软件公司"建模成多 Agent 系统：Product Manager / Architect / Project Manager / Engineer / QA Engineer 五个角色。核心哲学：**Code = SOP(Team)**。SOP（Standard Operating Procedure）被硬编码成 prompt 序列，每个角色有明确的 input/output 文档类型（PRD / Design / Task List / Code / Test Report）。

- **Environment**：共享的 message bus，角色之间发消息通信。
- **Role**：每个 role 有 `_observe`（订阅消息）、`_think`（决定动作）、`_act`（执行动作）的三段生命周期。
- **Assembly line** 范式：任务从 PM → Architect → PjM → Engineer → QA 顺序流动。

### 6.2 并发机制

不是传统并发——MetaGPT 通过 `asyncio` 让 role 的 `_think/_act` 异步，但 assembly line 本质上是串行的。

### 6.3 超时控制

`Role.run` 有可配置的 `max_turns`；没有全局预算。

### 6.4 冲突消解

**无原生机制**。MetaGPT 的假设是 SOP 充分明确了每个角色的 output schema，角色之间不会 output 冲突。要做冲突消解得自己写。

### 6.5 错误恢复

Message bus 可以重试；Role 级别的异常会冒泡到 Environment。没有 checkpoint。

### 6.6 工具调用抽象

每个 Role 自己定义 `Action` 类（subclass of `Action`），封装一次 LLM 调用。`Action` 有结构化的 `run(context) -> message`，相当于"一个 Role 可以做的动作集合"。

### 6.7 可借鉴

MetaGPT 最值得借鉴的是**"SOP 硬编码成 prompt 模板"的思想**。我们现在 BehaviorInferer 的 prompt 是一个大字符串，含 "few-shot 示例" 和 "guardrail 禁词清单"。完全可以学 MetaGPT 把 prompt 切成结构化模板（role prompt / context prompt / output schema prompt），好处：
- prompt_version 可以单独升级每一段而不动其他；
- 前端 audit 面板可以展示"这次调用用了哪个版本的 output schema prompt"；
- A/B 测试时更容易控制变量。

### 6.8 是否应该迁移？

**不**。MetaGPT 的 5 角色模型和我们的 4 agent 模型完全错位，强迁移会产生大量适配代码。

---

## 7. 框架对标 — OpenAI Swarm / Agents SDK

### 7.1 编排模型

Swarm 是 OpenAI 2024 年发布的实验性轻量框架，API surface 极简：
- **Agent** = system prompt + function list
- **Handoff** = 一个函数，返回另一个 Agent 对象（等价于 "switch speaker"）
- 没有 checkpoint、没有 state graph、没有显式超时

核心理念：**agent 无状态、handoff 显式**。所有状态都在"对话历史"里。

**Agents SDK**（Swarm 的生产继任者，2025 年发布）加入了：
- 声明式 handoff 带 metadata
- Guardrails（输入 / 输出过滤器）
- Tracing（OpenTelemetry-ish）
- Streaming
- 仍然不做状态持久化

### 7.2 并发机制

纯 Python sync 或 asyncio；没有"多 agent 同时跑"的概念，handoff 是顺序的。

### 7.3 超时控制

无框架级超时。外层 `asyncio.wait_for` 自理。

### 7.4 冲突消解

Swarm 没有原生机制；多 Agent 讨论需要手写 routing logic。

### 7.5 错误恢复

无。handoff 之间没有 retry，失败直接抛。

### 7.6 工具调用抽象

Agent 的 `functions=[...]` 直接传 Python 函数，OpenAI SDK 自动转 function calling schema。**极其轻量**——比 LangChain 的 Tool 类少了一个抽象层。

### 7.7 可借鉴

Swarm / Agents SDK 的**最大价值是"极简"本身**。它证明了一个观点：**对于任务边界清晰的多 agent 场景，handoff 模型 + 几十行编排代码就够，不需要图/状态机/消息总线**。我们的 Planner 正好是这种风格，不需要向 Swarm "学"什么具体 API，但可以从 Agents SDK 借鉴：

1. **Guardrails as first-class primitives**：Agents SDK 把 guardrail 做成 Agent 上的声明式属性 `input_guardrails=[...]` / `output_guardrails=[...]`，而不是编排器里的 `await guardrail.validate(...)` 调用。
   - 我们现在的做法：Planner 层 `await self.guardrail.validate(behavior_raw.to_text(), readme_text)`。
   - Agents SDK 风格：`BehaviorInferer(output_guardrails=[GuardrailValidator()])`，框架自动在 output 返回前调用。
   - 为什么不这么做：因为 ADR-003 明确要求"BI 不 import guardrail"（保持 lint-imports DAG），guardrail 必须从 Planner 层注入。折中方案：让 Planner 持有一个 `guardrail_registry`，通过构造参数传入 Agent 实例，而不是在 Planner 内 await。这是我们后面 §9 会提的 P1 建议之一。
2. **Tracing**：Agents SDK 内建了 OpenTelemetry 风格 tracing，每个 handoff 一个 span。我们的 ObservabilityCollector 也记录三维指标，但没有 span 树。对 debug 和 cost attribution 有帮助。

### 7.8 是否应该迁移？

**不建议**。Agents SDK 要求 OpenAI SDK >= v1.50，我们 LLM Provider 已经抽象了；强迁移会让 provider 抽象层失效。但**精神上对齐**（极简、声明式 guardrail、tracing）是合理方向。

---

## 8. 框架对标 — BabyAGI / AutoGPT / Dify / Flowise

这四个一起讲，因为它们和 RepoInsight 的场景错位最严重，对标意义主要是"**为什么我们不应该做成它们那样**"。

### 8.1 BabyAGI / AutoGPT — 自主循环范式

- **BabyAGI**：三角色（Execution / Task Creation / Prioritization）+ 向量数据库记忆 + 任务队列。用户给 objective，agent 不断 create/execute/reprioritize 直到任务队列清空或满足停止条件。
- **AutoGPT**：类似，但把"tool use + file system + web browsing"全部集成，目标更泛。

**为什么和我们错位**：我们的任务边界是**强结构化**的（输入：Git 仓库；输出：HTML 报告；步骤：固定 4 Agent 并行 + Reporter 聚合）。自主循环范式解决的是"任务分解不确定"的场景，用在我们这里等于给固定工序套一个"让 LLM 决定下一步"的壳，毫无价值且不可控。

**唯一可借鉴点**：BabyAGI 的**向量数据库短/长期记忆**思想。如果我们未来要做"跨 job 的洞察积累"（比如"同一个 repo 上次分析结论 vs 这次"），向量 store + repo_hash 检索是个合理的架构；但这属于阶段 4+ 的事。

### 8.2 Dify / Flowise — 低代码可视化编排

- **Dify**：drag-and-drop workflow，内建 RAG + LLM + tool 节点。核心约 15 种节点类型（v0.15），适合非程序员快速搭一个 "LLM + 一堆 tool" 的应用。
- **Flowise**：类似，但节点库更大（LangChain 生态的可视化包装）。支持 supervisor/worker 多 agent 模式。

**为什么和我们错位**：这两者的目标是"把 LangChain/LangGraph 变成拖拽工具给业务人用"，我们是"写一个严格 SLA 的分析 Pipeline 给技术用户"。拖拽带来的灵活性对我们是负担：
- 120s 硬切在可视化工具里很难表达；
- 我们的 Agent 里 StaticAnalyzer 要跑 pylint 子进程，Flowise 的节点沙箱不支持；
- 版本管理对代码友好，对 JSON 图不友好。

**唯一可借鉴点**：Dify/Flowise 的**执行轨迹可视化**对调试用户友好。我们未来可以考虑给 ObservabilityCollector 输出一个 "Mermaid gantt / timeline" 风格的可视化，展示三路 Agent 的 wall-clock 时序和占用比例——纯前端渲染，零后端成本。

### 8.3 是否应该迁移？

BabyAGI/AutoGPT：不。Dify/Flowise：不。对标意义仅在于"引以为戒"和个别特性借鉴（向量记忆、时序可视化）。

---

## 9. 与 RepoInsight Planner 的对比总表

下表把 §2–§8 的关键维度横向对比。✓ = 原生支持，○ = 需手写，✗ = 无。

| 维度 | RepoInsight | LangGraph | AutoGen / MAF | CrewAI | LC Agents | MetaGPT | Swarm/SDK | BabyAGI | Dify/Flowise |
|---|---|---|---|---|---|---|---|---|---|
| 编排模型 | fan-out + 串行 | 状态图 | 会话 | 角色/任务 | 单 agent loop | SOP 流水线 | handoff | 自主循环 | 可视化图 |
| 并发机制 | asyncio.gather | super-step | 单线程会话 | async_execution | 无 | 有限 async | 顺序 | 顺序 | 节点并行 |
| 总预算硬切 | ✓ (120s) | ○ | ✗ | ✗ | ✗ | ✗ | ○ | ✗ | 有限 |
| 单 Agent 超时 | ✓ | ✓ (节点级) | ✓ (LLM) | ✓ | ✓ | ○ | ○ | ✗ | ✓ |
| 动态降级 | ✓ (Community) | ○ | ○ | ○ | 生成式兜底 | ✗ | ○ | ✗ | ○ |
| 重试策略 | ✗ | ✓ (RetryPolicy) | ✓ (llm) | ✗ | ✓ (middleware) | ○ | ✗ | ✗ | ○ |
| Checkpoint / 断点恢复 | ✗ | ✓ | 0.4+ | ✗ | ✗ | ✗ | ✗ | ✗ | ○ |
| 条件路由 | ✗ | ✓ | ✓ | hierarchical | ReAct | ✗ | handoff | 内部 | ✓ |
| 多 Agent 结果冲突消解 | ✓ (LLM Judge) | ○ | ○ (debate) | ○ (manager) | N/A | ✗ | ✗ | ✗ | ○ |
| Guardrail 层 | ✓ (Planner 注入) | ○ | ○ | ○ | middleware | ✗ | ✓ (声明式) | ✗ | ○ |
| 工具调用抽象 | 无（Agent 直调） | Tool + Pydantic | register_for_llm | CrewAI Tool | Tool + Pydantic | Action 类 | function 直接传 | 内置 | 节点化 |
| 依赖方向约束 | 强 (lint-imports) | 弱 | 弱 | 弱 | 弱 | 中 | 弱 | 弱 | N/A |

### 关键发现

1. **没有任何主流框架同时满足"总预算硬切 + 多 Agent 结果冲突消解 + 依赖方向 lint 约束"这三件事**。我们的 Planner 不是在重造轮子，而是在"针对一个市面上没有现成轮子的组合需求"做定制。
2. **checkpoint 和节点级 retry 是我们相对主流框架最大的两个缺口**，但前者在 120s 单 job 场景下收益有限，后者只需要几十行代码就能补上。
3. **Guardrail 做成声明式**（Agents SDK 风格）是真正的设计升级，但受 ADR-003 的依赖方向约束，我们只能做到"Planner 侧声明式注入"而不是"Agent 上声明式挂载"。
4. **工具调用抽象**对我们不适用——我们的 Agent 是 Python 类，不是 LLM 决策的工具。

---

## 10. 优化建议（10 条，分 P0 / P1 / P2）

每条包含：**参考框架**、**具体改动**、**优先级**、**预估工作量**、**理由 / 风险**。注意：以下建议都**不改 CLAUDE.md 的"4 角色固定"约束**，也不破坏 ADR-003 的依赖方向 DAG。

### P0 — 阶段 3 内必做

#### 建议 1：`_handle_community` 前置指数退避重试

- **参考**：LangGraph `RetryPolicy(max_attempts=3, backoff_factor=2.0)`；LangChain middleware retry。
- **改动**：`_handle_community` 接收 `result` 之前，在 `community_task` 外层再包一层 "失败 → 重试一次 → 再失败才降级"。实现可以用 tenacity 的 `AsyncRetrying` 或手写 15 行循环。预算分配：重试吃 community budget 的 30%（最多 13s），原始任务 70%（32s）。
- **理由**：当前 `_handle_community` 对所有异常一视同仁直接降级，导致瞬时网络抖动（GitHub API 500）→ 立即历史均值回退，浪费一次本可成功的调用。
- **风险**：重试把实际等待时间拉长，可能和总预算 120s 打架。mitigations：只对 `TimeoutError` 以外的异常重试；重试次数 ≤ 1。
- **工作量**：0.5 人日。
- **涉及文件**：`backend/app/orchestrator/planner.py:44-67`。

#### 建议 2：Reporter 超时走"generate"式降级而不是 500

- **参考**：LangChain `early_stopping_method="generate"`。
- **改动**：Reporter 的 `asyncio.wait_for` 超时后，不抛 `BudgetExhaustedError`，而是调用一个 `_emergency_reporter(static, behavior, community)` 生成"部分结果 + 超时说明"的兜底 HTML。这个 emergency reporter 不调用 LLM（零预算），只用预置模板 + ECharts 配置。
- **理由**：120s 是用户可见的硬切点。现状下一旦 Reporter 超时，用户看到 500 页面，前面 3 个 Agent 的所有工作成果全部丢失——用户体验完全崩盘。即使只输出"覆盖率图 + 高风险函数列表 + 社区降级 banner"，也比 500 强。
- **风险**：emergency reporter 的 HTML 和正常 reporter 的 HTML schema 要一致，否则前端解析器爆。解决：两者共用同一个 Jinja 模板基类。
- **工作量**：1 人日。
- **涉及文件**：`backend/app/orchestrator/planner.py:191-214`、新增 `backend/app/agents/emergency_reporter.py`。

#### 建议 3：把 Planner 的运行时 state 抽成 dataclass

- **参考**：LangGraph State 建模。
- **改动**：创建 `backend/app/orchestrator/state.py`:
  ```python
  @dataclass
  class PipelineState:
      job_id: str
      cloned_path: str | None = None
      static_result: StaticResult | None = None
      behavior_raw: BehaviorResult | None = None
      behavior_result: BehaviorResult | None = None
      community_result: CommunityResult | None = None
      guardrail_telemetry: GuardrailTelemetry | None = None
      t_start: float = 0.0
      stage_timings: dict[str, int] = field(default_factory=dict)
  ```
  Planner 维护一个 `state` 实例，所有阶段从读局部变量改为读 `state.xxx`。
- **理由**：
  1. 当前的局部变量散落（`static_result`, `behavior_raw`, `community_result`...）使得 observability 难以序列化当前进度；
  2. 未来上 checkpoint 时这个 dataclass 直接就是序列化单位；
  3. 测试时可以用 `PipelineState(...)` 构造任意中间态，而不是重跑整个 pipeline；
  4. **不引入任何外部依赖，就是一个 dataclass**。
- **工作量**：0.5 人日（纯重构，无功能变更）。
- **涉及文件**：`backend/app/orchestrator/planner.py`（全文重构），新增 `state.py`。

---

### P1 — 阶段 3-4 过渡期做

#### 建议 4：BudgetTerminationCondition 对象化

- **参考**：AutoGen 0.4 `MaxMessageTermination & TextMentionTermination`（声明式）。
- **改动**：把 `BUDGET_TOTAL_S = 120`、`if elapsed >= BUDGET_TOTAL_S - 2: raise BudgetExhaustedError` 这类散落的逻辑抽成一个 `BudgetGuard` 对象：
  ```python
  class BudgetGuard:
      def __init__(self, total_s: float, reserved_s: float = 2.0):
          self._total_s, self._reserved_s = total_s, reserved_s
          self._t_start = time.monotonic()
      def remaining(self) -> float: ...
      def check_or_raise(self) -> None: ...
      def budget_for(self, agent: str, default: float) -> float: ...
  ```
- **理由**：
  1. 当前 Planner 里 `BUDGET_*` 常量 + 手写减法在 3 个地方重复，容易漂移；
  2. `budget_for(agent, default)` 让 Reporter 动态收窄逻辑从 `min(15, elapsed - 2)` 变成明确的 API；
  3. 未来如果要改成"总预算可配置"（CLI flag / 环境变量），只改一处。
- **工作量**：0.5 人日。
- **涉及文件**：`backend/app/orchestrator/planner.py`，新增 `backend/app/orchestrator/budget.py`。

#### 建议 5：Guardrail 声明式注入 + guardrail_registry

- **参考**：Agents SDK `output_guardrails=[...]`；ADR-003（我们自己的依赖方向约束）。
- **改动**：在 Planner 构造函数增加 `guardrail_registry: dict[str, GuardrailValidator]`，key 是 Agent 名字。调用时 Planner 根据 Agent 结束后自动查注册表、自动调用 guardrail。
  ```python
  async def _run_with_guardrail(self, agent_name: str, coro):
      result = await coro
      gr = self.guardrail_registry.get(agent_name)
      if gr is not None:
          return await gr.validate(result, ...)
      return result
  ```
- **理由**：
  1. 当前 Planner 只对 BI 的输出 guardrail；未来要给 ConflictResolver 输出也 guardrail（防 judge 幻觉），就要再复制一遍 await。注册表一次性解决；
  2. **不违反 ADR-003**——BI 依然不 import guardrail，guardrail 是 Planner 的依赖。
- **风险**：注册表 key 打错 → silent skip。mitigation：Planner `__init__` 做一次 `assert set(registry.keys()) <= KNOWN_AGENT_NAMES`。
- **工作量**：0.5 人日。
- **涉及文件**：`backend/app/orchestrator/planner.py`、`backend/app/main.py`（DI 装配）。

#### 建议 6：ConflictResolver 加"优先级 top-K"策略

- **参考**：AutoGen 自定义 speaker selection 函数。
- **改动**：`ConflictResolver.detect_conflicts` 返回排序后的冲突列表（当前是 `sorted(overlap)`，字典序），增加一个 `score(module)` 函数，按"该模块最高 CC × 覆盖率缺口 × 出现在 core_modules 的次数"加权，然后 `resolve` 只对 top-K（默认 3）调用 LLM Judge。
- **理由**：
  1. 当前每个冲突模块独立调用一次 LLM（每次 ~500 tokens）。如果一个大仓库有 8 个冲突模块，LLM 成本 = 4000 tokens × 价格，而且耗时可能把 Reporter 预算挤没；
  2. Top-K 策略天然符合 Pareto 法则——前 3 个最严重的占了 90% 的价值；
  3. K 可以作为 `CommunityAssessorInput`-类似的可配置参数，CLI debug 时可以 K=10 看全量。
- **风险**：top-K 外的冲突模块完全被忽略，用户不知道它们的存在。mitigation：在 HTML 报告里加"其余 N 个冲突模块未分析（按当前策略）"提示。
- **工作量**：0.5 人日。
- **涉及文件**：`backend/app/orchestrator/conflict_resolver.py:57-79`。

#### 建议 7：Agent role/goal 结构化 metadata 暴露到 Telemetry

- **参考**：CrewAI `role/goal/backstory`；Agents SDK tracing。
- **改动**：每个 Agent 类加 class-level attribute：
  ```python
  class BehaviorInferer:
      role: ClassVar[str] = "behavior_inferer"
      goal: ClassVar[str] = "Infer typical usage patterns from README/PR/Issue corpus"
      prompt_version: ClassVar[str] = "v1.2"
  ```
  `ObservabilityCollector.record_pipeline` 扩展为带上每 Agent 的 `{role, goal, prompt_version, duration_ms}` 结构，前端 Audit 面板显示。
- **理由**：
  1. prompt_version 已经在 ai-13 R1 §2 的 CacheKey 里用，但没暴露给用户；
  2. 未来 A/B 测试 prompt 时，直接用 Telemetry 数据做统计分析；
  3. **零功能变更，纯元数据暴露**。
- **工作量**：0.5 人日。
- **涉及文件**：4 个 agent 文件 + `services/observability.py`。

---

### P2 — 阶段 4 再考虑

#### 建议 8：PipelineState 序列化 + 最小 checkpoint

- **参考**：LangGraph SqliteSaver。
- **改动**：在建议 3 的 `PipelineState` 上加一个方法 `to_json()` / `from_json()`，每个阶段结束后写入 SQLite（表 `pipeline_checkpoints`）。`POST /analyze` 新增 `?resume_from=<job_id>` 查询参数，从上次 checkpoint 恢复。
- **理由**：对 120s 单 job **收益有限**，但对未来"长尾任务"（比如给 AI-company 这种大 repo 做 5 分钟深度分析）是基础设施。
- **风险**：
  - SQLite 写入 3 次/job 会增加 ~5ms 开销；
  - `StaticResult` / `BehaviorResult` 含 Pydantic model，`model_dump_json()` 可能不稳定（Pydantic v2 的 Union discriminator 问题）；
  - 需要 schema migration 基础设施，当前没有。
- **工作量**：1 人日（最小实现），3 人日（含 migration）。
- **涉及文件**：新增 `backend/app/orchestrator/checkpoint.py`，`services/audit.py` 扩展。

#### 建议 9：ConflictResolver debate 模式（2-轮最小实现）

- **参考**：Multi-Agent Debate (arxiv 2510.12697)；AutoGen GroupChat。
- **改动**：现状是一次性 LLM judge（temperature=0.0）。升级为：
  1. 让 judge 先出 verdict
  2. 把 verdict 再喂给一个 `critic_guardrail_judge`，问"这个 verdict 是否矛盾于 static_view / behavior_view 的证据"
  3. 如果 critic 反对，重跑一次 judge（temperature=0.3，带 critic 的反馈）
  最多 2 轮就收敛或接受。
- **理由**：学术界 MAD 论文一致表明 "2-round debate > single judge" 在准确性上有 5-15% 提升，尤其在边界案例。
- **风险**：
  - LLM 调用 × 2，成本翻倍；
  - 延迟翻倍，会和 120s 预算打架；
  - 只在 "top-K 冲突模块" 场景做（见建议 6），控制住成本。
- **工作量**：1 人日。
- **涉及文件**：`conflict_resolver.py`。

#### 建议 10：Pipeline 时序可视化（Mermaid Gantt 风格）

- **参考**：Dify/Flowise 执行轨迹可视化。
- **改动**：利用建议 7 的 role/goal 结构化 metadata + 现有的 `stage_timings`，在 ReportJsonResponse 顶层加一个 `pipeline_timeline: list[{agent, start_ms, end_ms}]`。前端用简单的 SVG 或 Mermaid gantt 渲染。
- **理由**：
  1. **调试用户最想知道的是"为什么这次跑了 85 秒"**，一个可视化时序一目了然；
  2. 对运维人员做 SLA 分析非常有用（哪个 Agent 是长尾）；
  3. 零 LLM 成本，纯数据转换。
- **风险**：前端 Mermaid 渲染对某些老浏览器不兼容，改用原生 SVG 更稳。
- **工作量**：0.5 人日后端 + 1 人日前端 = 1.5 人日。
- **涉及文件**：`backend/app/models/api_schemas.py`、`frontend/src/components/PipelineTimeline.tsx`（新增）。

---

## 11. 综合结论

### 11.1 我们的 Planner 在市面上是什么位置

- **极简派**：编排代码 < 150 行，和 Swarm / Agents SDK 同档；
- **严格派**：总预算硬切 + lint-imports DAG + Guardrail 注入位置约束，比 LangGraph / AutoGen 等主流框架都"紧"；
- **场景驱动派**：不追求通用性，面向"Git 仓库分析" 这个具体场景做特化，特化程度接近 MetaGPT 对"软件开发" 的特化；
- **缺口**：checkpoint、节点级 retry、Agent metadata 暴露——前两者在 120s 场景收益有限，最后一个是纯元数据工作。

### 11.2 我们不应该做什么

1. **不要迁移到任何现成框架**。每一个都会把"lint-imports 零违规 + 总预算硬切 + Planner 注入 guardrail"这三件事里的至少一件破坏掉，收益小于损失。
2. **不要引入状态图抽象**。我们只有一次 fan-out + 一次串行，StateGraph 的复杂度换不回对应的收益。
3. **不要引入会话式编排**。4 个 Agent 不需要互相说话，强塞 GroupChat 只会增加延迟。
4. **不要做自主循环**。任务边界强结构化，让 LLM 决定下一步 = 把 120s SLA 扔进垃圾桶。

### 11.3 我们应该做什么（按优先级汇总）

| # | 建议 | 优先级 | 工作量 | 风险 |
|---|---|---|---|---|
| 1 | `_handle_community` 前置重试 | **P0** | 0.5d | 低 |
| 2 | Reporter 超时走 generate 降级 | **P0** | 1d | 低 |
| 3 | PipelineState dataclass | **P0** | 0.5d | 零 |
| 4 | BudgetGuard 对象化 | P1 | 0.5d | 低 |
| 5 | Guardrail registry 声明式 | P1 | 0.5d | 低 |
| 6 | ConflictResolver top-K | P1 | 0.5d | 低 |
| 7 | Agent role/goal 元数据 | P1 | 0.5d | 零 |
| 8 | 最小 checkpoint | P2 | 1d | 中 |
| 9 | Debate 2-round judge | P2 | 1d | 中（LLM 成本） |
| 10 | Pipeline timeline 可视化 | P2 | 1.5d | 低 |

**P0 合计 2 人日**，可以在阶段 3 的 T4/T5 窗口内吃掉，不挤占 T1/T2/T3 关键路径。
**P1 合计 2 人日**，建议在阶段 3 收尾或阶段 4 开始时做。
**P2 合计 3.5 人日**，属于"长期投资"，等总预算有余量或 RepoInsight 有长尾任务需求时再上。

### 11.4 最后一句

对标完 8 个框架，最强烈的感受是：**大厂开源框架针对的是"业务人员拖拽 + 动态任务分解"这种泛需求，而我们针对的是"强 SLA + 固定工序 + 严格依赖 DAG"这种工业级细分需求**。没有框架完美匹配，但每个框架都有 1-2 个设计细节值得"抽走精神，不引依赖"。上述 10 条建议就是这种精神抽取的结果。

---

## 附录 A — 参考资料

### LangGraph
- [LangGraph: Agent Orchestration Framework for Reliable AI Agents (LangChain)](https://www.langchain.com/langgraph)
- [LangGraph State Machines: Managing Complex Agent Task Flows in Production (DEV Community)](https://dev.to/jamesli/langgraph-state-machines-managing-complex-agent-task-flows-in-production-36f4)
- [LangGraph State Machine: Complex Branching Logic Guide (Markaicode)](https://markaicode.com/langgraph-state-machine-branching-logic/)
- [Advanced LangGraph: Conditional Edges and Tool-Calling Agents (DEV Community)](https://dev.to/jamesli/advanced-langgraph-implementing-conditional-edges-and-tool-calling-agents-3pdn)
- [Production Multi-Agent System with LangGraph (Markaicode)](https://markaicode.com/langgraph-production-agent/)
- [Scaling LangGraph Agents: Parallelization, Subgraphs, and Map-Reduce Trade-Offs](https://aipractitioner.substack.com/p/scaling-langgraph-agents-parallelization)
- [Map-Reduce with the Send() API in LangGraph (AI Engineering BootCamp)](https://medium.com/ai-engineering-bootcamp/map-reduce-with-the-send-api-in-langgraph-29b92078b47d)
- [Graph broken with defer-ed nodes + Command + conditional edges (langgraph issue #5182)](https://github.com/langchain-ai/langgraph/issues/5182)
- [Build multi-agent systems with LangGraph and Amazon Bedrock (AWS Blog)](https://aws.amazon.com/blogs/machine-learning/build-multi-agent-systems-with-langgraph-and-amazon-bedrock/)

### AutoGen / Microsoft Agent Framework
- [microsoft/autogen (GitHub)](https://github.com/microsoft/autogen)
- [Multi-agent Conversation Framework (AutoGen 0.2)](https://microsoft.github.io/autogen/0.2/docs/Use-Cases/agent_chat/)
- [Handling policy for unhandled agent exceptions (issue #4904)](https://github.com/microsoft/autogen/issues/4904)
- [Selector Group Chat (AutoGen)](https://microsoft.github.io/autogen/dev//user-guide/agentchat-user-guide/selector-group-chat.html)
- [Introducing Microsoft Agent Framework (Azure Blog)](https://azure.microsoft.com/en-us/blog/introducing-microsoft-agent-framework/)
- [Microsoft AutoGen: Orchestrating Multi-Agent LLM Systems (Tribe AI)](https://www.tribe.ai/applied-ai/microsoft-autogen-orchestrating-multi-agent-llm-systems)

### CrewAI
- [crewAIInc/crewAI (GitHub)](https://github.com/crewaiinc/crewai)
- [CrewAI: A Practical Guide to Role-Based Agent Orchestration (DigitalOcean)](https://www.digitalocean.com/community/tutorials/crewai-crash-course-role-based-agent-orchestration)
- [Agent-to-Agent (A2A) Protocol (CrewAI Docs)](https://docs.crewai.com/en/learn/a2a-agent-delegation)
- [How Agents Collaborate in CrewAI (CrewAI Docs)](https://docs.crewai.com/core-concepts/Collaboration/)
- [Hierarchical process delegation fails (issue #4783)](https://github.com/crewAIInc/crewAI/issues/4783)

### LangChain Agents
- [AgentExecutor API reference](https://python.langchain.com/api_reference/langchain/agents/langchain.agents.agent.AgentExecutor.html)
- [Cap the max number of iterations](https://python.langchain.com/v0.1/docs/modules/agents/how_to/max_iterations/)
- [How to use a timeout for the agent](https://langchain-cn.readthedocs.io/en/latest/modules/agents/agent_executors/examples/max_time_limit.html)

### MetaGPT
- [FoundationAgents/MetaGPT (GitHub)](https://github.com/FoundationAgents/MetaGPT)
- [MetaGPT: The Multi-Agent Framework (Official Docs)](https://docs.deepwisdom.ai/main/en/guide/get_started/introduction.html)
- [What is MetaGPT (IBM Think)](https://www.ibm.com/think/topics/metagpt)
- [MetaGPT: Meta Programming for a Multi-Agent Collaborative Framework (OpenReview)](https://openreview.net/forum?id=VtmBAGCN7o)

### OpenAI Swarm / Agents SDK
- [openai/swarm (GitHub)](https://github.com/openai/swarm)
- [Orchestrating Agents: Routines and Handoffs (OpenAI Cookbook)](https://developers.openai.com/cookbook/examples/orchestrating_agents)
- [OpenAI Swarm Framework Guide (Galileo)](https://galileo.ai/blog/openai-swarm-framework-multi-agents)
- [Swarm: OpenAI's Experimental Approach to Multi-Agent Systems (Arize AI)](https://arize.com/blog/swarm-openai-experimental-approach-to-multi-agent-systems/)

### BabyAGI / AutoGPT
- [BabyAGI (official)](http://babyagi.org/)
- [What is BabyAGI (IBM Think)](https://www.ibm.com/think/topics/babyagi)
- [yoheinakajima/babyagi (GitHub)](https://github.com/yoheinakajima/babyagi)
- [The Rise of Autonomous Agents: AutoGPT, AgentGPT, and BabyAGI (BairesDev)](https://www.bairesdev.com/blog/the-rise-of-autonomous-agents-autogpt-agentgpt-and-babyagi/)

### Dify / Flowise
- [Dify: Leading Agentic Workflow Builder](https://dify.ai/)
- [Flowise - Build AI Agents, Visually](https://flowiseai.com/)
- [Comparative Analysis of Dify, Langflow, and Flowise (Scribd)](https://www.scribd.com/document/876528820/Comparative-Analysis-of-Dify-Langflow-And-Flowise-for-a-Government-AI-Platform)
- [No-Code AI App Builders Compared: Dify vs Flowise vs Stack AI (Conbersa)](https://www.conbersa.ai/learn/no-code-ai-builders-comparison)

### Multi-Agent Debate / Judge 学术论文
- [Multi-Agent Debate for LLM Judges with Adaptive Stability Detection (arXiv 2510.12697)](https://arxiv.org/pdf/2510.12697)
- [Voting or Consensus? Decision-Making in Multi-Agent Debate (ACL 2025)](https://aclanthology.org/2025.findings-acl.606.pdf)
- [When AIs Judge AIs: Agent-as-a-Judge Evaluation for LLMs (arXiv 2508.02994)](https://arxiv.org/html/2508.02994v1)
- [Auditing Multi-Agent LLM Reasoning Trees Outperforms Majority Vote (arXiv 2602.09341)](https://arxiv.org/pdf/2602.09341)

---

**（文档结束）**
