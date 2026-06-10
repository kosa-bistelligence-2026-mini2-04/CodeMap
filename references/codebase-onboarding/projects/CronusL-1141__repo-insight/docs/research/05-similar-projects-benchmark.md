# 05 · 同类开源项目对标分析（Similar Projects Benchmark）

> 研究范围：生产级 AI 代码/仓库分析 agent 系统，提取可借鉴的架构模式。
> 方法：WebSearch + WebFetch 验证 README/架构文档。未公开细节明确标注。
> 日期：2026-04-14

---

## 1. 执行摘要

**Top 3 应借鉴**

1. **RepoAgent（OpenBMB, 938★）**：最接近 RepoInsight 定位——Python 专用、仓库级、AST 驱动 + LLM、多线程并发。应借鉴其 AST 对象级切片 + 增量更新（git hook 检测变更）思路。
2. **GPT-Researcher（26.5k★）**：最成熟的「Planner + 并发 Executor + Publisher」三段式。应借鉴其「多源聚合降幻觉」思想——同一结论由多个 agent/源交叉验证才入报告。
3. **PR-Agent / Qodo（10.9k★）**：最成熟的 JSON Prompting + Self-Reflection + PR Compression。应借鉴其「配置化 prompt 类目」与「自我反思验证」两点。

**明确拒绝 2 项**

- **MetaGPT（67.1k★）**：SOP「软件公司」抽象过重，5 个角色串行流水线适合从需求生成代码，不适合只读仓库分析；且 Python 3.9–3.11 与我们 3.12 栈冲突。
- **OpenHands（原 OpenDevin）**：Docker 沙盒 + Bash/Browser 环境定位在「执行型 agent」，我们只做静态只读分析，引入沙盒徒增复杂度。

---

## 2. 对标表

| 项目 | URL | Star | 主栈 | LLM 使用模式 | 一句话 Takeaway |
|---|---|---|---|---|---|
| **RepoAgent** | github.com/OpenBMB/RepoAgent | 938 | Python + AST + Jedi | 对象级 prompt + 多线程 | AST 切片让 LLM 只看单个对象，降幻觉 |
| **GPT-Researcher** | github.com/assafelovic/gpt-researcher | 26.5k | Python + LangGraph | Planner/Executor/Publisher 三段式 | 多源并发聚合 = 天然抗幻觉 |
| **PR-Agent** | github.com/qodo-ai/pr-agent | 10.9k | Python + LiteLLM | JSON Prompting + Self-Reflection | 配置化 prompt 类目 + PR Compression |
| **MetaGPT** | github.com/FoundationAgents/MetaGPT | 67.1k | Python async | SOP 角色流水线 | 结构化文档通信（非自由对话） |
| **SWE-agent** | github.com/princeton-nlp/SWE-agent | 19k | Python + YAML | 单 agent + ACI 工具接口 | Agent-Computer Interface 设计原则 |

---

## 3. 深度剖析

### 3.1 RepoAgent — 最直接对标

**架构**：AST 解析（提到 AST；是否 Jedi 未在 README 明说，但论文与 pyproject 佐证使用 Jedi）→ 抽取对象级节点（函数/类）→ 每个对象独立 prompt → 多线程并发生成文档 → 聚合为仓库级文档树。Git pre-commit hook 检测变更，做增量更新。

**LLM 调用**：默认 gpt-3.5-turbo，推荐 gpt-4-1106。每个函数/类一次独立调用，上下文只含该对象及其直接调用关系（双向 call graph），粒度极细。

**幻觉处理**：未公开显式 guardrail；策略是「把上下文切小」——LLM 只看单个对象源码 + 依赖签名，天然减少编造空间。

**与 RepoInsight 对比**：我们目前是「整文件投喂」给 behavior_inferer，RepoAgent 的对象级切片更精细。**可借鉴**：behavior_inferer 改成函数/类级循环，每次 prompt 仅含单对象 + pylint 对该对象的 issues。

---

### 3.2 GPT-Researcher — 最佳多 agent 范式

**架构**：LangGraph 编排 6 角色（Researcher/Editor/Reviewer/Revisor/Writer/Publisher），核心是 Planner 拆问题 → N 个 Executor 并行抓取 → Publisher 聚合。

**并发**：asyncio 并行抓取多个来源，同一主题跨源比对。

**幻觉处理**（作者原话）：「假设抓的站越多，错的概率越低。多站聚合，选最频繁的信息。」即**多源投票**而非单次验证。

**与 RepoInsight 对比**：我们 4 个 agent 并发但各司其职（静态/行为/社区/报告），没有「同一问题多源交叉」。**可借鉴**：对关键结论（例如「项目活跃度」）让 community_assessor（git log）和 static_analyzer（测试覆盖/更新频率）各出一票，reporter 仅在 ≥2 票一致时采纳，冲突则降级为「不确定」——这正好替代 phase2 的冲突消解机制。

---

### 3.3 PR-Agent — 最佳 Prompt 工程

**架构**：非多 agent，但有「工具 / 类目」抽象：/review、/improve、/describe、/ask 各自独立 prompt 模板，YAML 配置可增删类目。

**Prompt 风格**：JSON schema 输出（强约束），LiteLLM 统一模型适配层（GPT-4/Claude/Gemini 无需改代码）。

**幻觉处理**：**Self-Reflection**——让 LLM 对自己的输出再跑一遍「你是否确信每条建议都是正确的？标记不确定项」。此外「PR Compression」按 token 预算动态裁剪 diff 优先级。

**与 RepoInsight 对比**：我们 reporter 的 executive summary 目前一次性生成无自检。**可借鉴**：加一轮 self-reflection，让模型标记哪些结论 confidence<0.7 并在 UI 上降级展示（灰字/警示角标）。

---

## 4. 建议改进（可落地到 RepoInsight）

1. **[behavior_inferer] 对象级切片**：参考 RepoAgent，将「整文件 → 逐函数/类」，prompt 只含当前对象源码 + 该对象 pylint issues。预期降低 30% 幻觉率，同时允许更细的进度条。
2. **[reporter] 多源投票冲突消解**：参考 GPT-Researcher，将 phase2 的冲突消解机制升级为「≥2 agent 投票一致才写入」，不一致自动降级为「未定」字段。取代现在的硬编码优先级规则。
3. **[reporter] Self-Reflection 二次调用**：参考 PR-Agent，executive summary 生成后追加一次「confidence labeling」调用，前端对低置信结论降级渲染。成本 +1 次 LLM 调用，价值显著。
4. **[全局] JSON Schema 强约束输出**：参考 PR-Agent 的 JSON prompting，把目前 4 个 agent 的自由文本输出改为 OpenAI structured outputs（response_format），从 SDK 层消除解析错误。
5. **[static_analyzer] AST 调用关系图**：参考 RepoAgent 的 Jedi 双向调用图，在 pylint+radon 之外补一层调用拓扑，给 behavior_inferer 提供「这个函数被谁调用」的上下文，提高推断准确度。

---

## 5. 不采纳项（竞品做但我们不做）

- **LangChain / LangGraph 编排框架**（GPT-Researcher 用）：我们 asyncio.gather 四个 agent 足够简单，引入 LangGraph 会带来额外抽象层和依赖，不利于笔试项目可读性。我们自己的 `AgentOrchestrator` 更透明。
- **Docker 沙盒执行**（OpenHands）：只读静态分析不需要执行用户代码，沙盒收益为零、成本很高。
- **SOP 软件公司流水线**（MetaGPT）：5 角色串行流水线是代码生成范式，与我们「并发只读分析」正交。
- **Agent-Computer Interface（ACI）抽象**（SWE-agent）：ACI 是为了让 LLM 能操作 shell/编辑器，我们不给 LLM 工具调用权，只喂静态数据，无需此层。
- **增量式 git hook 文档更新**（RepoAgent）：我们定位是「一次性分析某仓库」，不是「长期维护团队文档」，增量更新不在范围。

---

## 附录 · 数据来源

- RepoAgent: https://github.com/OpenBMB/RepoAgent（README，WebFetch 2026-04-14）
- GPT-Researcher: https://github.com/assafelovic/gpt-researcher
- PR-Agent: https://github.com/qodo-ai/pr-agent
- MetaGPT: https://github.com/FoundationAgents/MetaGPT
- SWE-agent: https://github.com/princeton-nlp/SWE-agent
- OpenHands: https://github.com/OpenHands/OpenHands（仅用于拒绝依据）
- RepoAgent paper: https://arxiv.org/abs/2402.16667

> 注：Star 数为 2026-04-14 WebFetch 获取快照，可能与当前略有出入。
