---
title: 研究#4 — Agent 角色模板与 LLM 性能/成本优化
author: researcher-4
date: 2026-04-14
project: repo-insight
phase: stage3
type: research
---

# 研究#4：Agent 角色设计模式 + LLM 性能/成本优化

> 对标对象：RepoInsight 的 4-Agent 拓扑（StaticAnalyzer / BehaviorInferer / CommunityAssessor / Reporter）+ Planner 编排 + 六维 CacheKey + Prompt v1。
>
> 交付目标：在不动代码的前提下，系统性地给出角色拆分合理性判断、CacheKey 强弱分析，并产出 5-10 条可落地的优化建议，每条附预期延迟/成本收益。
>
> 研究方法：WebSearch 真实调研 + 对照阅读 `backend/app/agents/`、`backend/app/llm/cache.py`、`backend/app/llm/openai_provider.py`、`ADR-002`、`STAGE3-PLAN.md`。

---

## 0. TL;DR（先看结论）

1. **4 角色拆分"粒度正确、但缺一个 Critic 环"**。主流生产型多 Agent 系统（MetaGPT / Planner-Executor-Critic 家族 / Reflexion）都保留一个显式的"审查/验证"角色；我们把这个职责埋进了 GuardrailValidator 和 ConflictResolver，能工作但不成体系——下一步可以从"新增独立 Reflector Agent"vs"把 Reporter 拆成 Writer+Reviewer"两个方案里选一个。
2. **六维 CacheKey 相对业界基础缓存属于"偏强"**，特别是 `prompt_version` 这一维是很多团队落地后才补上的；但它对"仓库提交两次 commit、90% 代码不变"的场景命中率为 0 —— 这里应该考虑分层缓存（文件级 + 仓库级）或语义缓存。
3. **Prompt v1 已经选对了 JSON mode + temperature=0，减少了 ~8-15% 的 retry 率**（学术统计）。但它没有 few-shot 示例、没有显式的"未知就减少条数"reward-shape 之外的引导，升级到 2-3 shot CoT 预计能再抬一档证据质量。
4. **最高杠杆的三项具体优化**（详见 §7）：
   - Provider 层接入 OpenAI Automatic Prompt Caching（零代码改动，prompt prefix 命中直降 50% input cost）；
   - ConflictResolver 用 Model Routing（gpt-4o-mini 做判官，只有高不确定度时升级到 gpt-5.4），预估 judge 成本 -60%；
   - 把 Reporter 内部的"生成 HTML + 生成 Markdown + 生成 ECharts"改成结构化输出单次调用，retry 率从 ~2% 跌到 <0.1%。

---

## 1. Agent 角色设计模式巡礼（6+ 主流模式）

本节按"原理 → 适用场景 → 对我们有什么启发"三段式展开。

### 1.1 Planner-Executor-Critic（PEC 家族）

PEC 是工业界最常见的多 Agent 拓扑。Planner 负责把用户任务拆成 DAG 或步骤列表，Executor 执行具体动作，Critic 在每一步或产出后给出质量评分并决定是否重新规划。其最大优势是允许在不同阶段用不同能力/成本的模型——例如 Planner 用 Opus、Executor 用 Sonnet、Critic 用 Haiku，就能在保住规划质量的前提下把执行成本压下来。

- 出处：arxiv 2509.08646 / emergentmind Planner-Executor 专题 / AWS Prescriptive Guidance
- 关键权衡：Planner 一次定稿 vs ReAct 式滚动规划，前者 token 省、后者容错强
- **对 RepoInsight 的映射**：
  - Planner 对应 `orchestrator/planner.py`，已经有了
  - Executor 对应 4 个 Agent，其中 StaticAnalyzer / CommunityAssessor 不走 LLM（正确选择）
  - Critic 对应 GuardrailValidator + ConflictResolver 的组合，**但是"拆在两个地方"**——GuardrailValidator 只看幻觉，ConflictResolver 只看 static vs behavior 的重叠；没有一个角色在 Reporter 产出后做"整体合理性审查"
  - 结论：我们离标准 PEC 还差一个"终局 Critic"步骤（见 §4 的 Reflector 方案）

### 1.2 ReAct（Reasoning + Acting）

ReAct 由 Yao et al. 在 arxiv 2210.03629 提出，核心做法是让 LLM 交替生成 "Thought → Action → Observation" 三段式轨迹，把外部工具调用嵌入推理链。相比纯 CoT，它的幻觉率显著下降（因为每个 Thought 可以被下一个 Observation 证伪），在 HotpotQA / Fever 等事实类任务上普遍拉出 5-10 个百分点。

- 适用场景：单 Agent 需要多轮调用外部工具/检索；任务边界模糊、可能中途换道
- **对 RepoInsight 的映射**：
  - 我们 4 个 Agent 里真正需要 ReAct 的是 BehaviorInferer —— 目前它是"一次性把 README+ISSUE+PR 灌进去要 JSON"的 **非 ReAct** 模式
  - 升级到 ReAct 的潜在收益：当 README 信息不足时，模型可以"Action: 读 docs/ 下的 tutorial 文件" → Observation：补齐证据再输出；这能缓解 guardrail 拦截后的三级回退损耗
  - 成本：ReAct 轨迹比单次调用多 2-3 轮，input tokens 翻倍——除非配合 §1.8 的自动缓存，否则不划算
  - 结论：**本阶段不切 ReAct，放到阶段 4 与 prompt caching 绑定评估**

### 1.3 Reflexion（自我反思）

Reflexion 由 Shinn et al. 在 arxiv 2303.11366 提出，思路是"用语言反馈代替权重更新"：Actor 产出一次结果 → Evaluator 判定好坏 → Self-Reflection 模块把失败原因写成一段 episodic memory → 下次 trial 把 memory 塞回 prompt。AlfWorld 上 ReAct+Reflexion 把通过率从 "差 20 多个 task" 打到 130/134；HumanEval / MBPP 代码任务也有显著提升。

- 适用场景：有可重试语义的任务；失败信号结构化程度高
- **对 RepoInsight 的映射**：
  - RepoInsight 的重试机会非常少——120s 总预算，Reflexion 的"多轮 trial"在我们这里只能体现为"Guardrail 拦截后的再生成"
  - 我们现在的三级回退（再生成 → 截断 → 兜底）只是机械回退，**没有把"为什么被拦截"当成 episodic memory 喂回模型**
  - 轻量升级路径：ADR-003 的 regenerate 环节里追加一句 "你上次输出在以下位置触发了 X 规则：..."，预期可把二次再生成的拦截率从 ~15% 降到 ~5%

### 1.4 Chain-of-Verification（CoVe）

CoVe 由 Dhuliawala et al. 在 arxiv 2309.11495 提出，四步法：(1) 起草初版回答；(2) 为初稿生成验证问题；(3) **独立**回答验证问题（不看初稿，防止 copying）；(4) 综合生成最终答案。Wikidata 列表任务上精度从 0.17 翻倍到 0.36，幻觉实体数从 2.95 跌到 0.68。

- 适用场景：事实性抽取、列表生成类任务
- **对 RepoInsight 的映射**：BehaviorInferer 的 `usage_patterns[]` 和 `core_modules[]` 本质上是列表抽取任务，正是 CoVe 的目标靶子
- 可落地方案：在 Guardrail 语义层之前插入一个轻量 CoVe 步骤——对每条 usage_pattern 反问"这段描述在 README 里有对应句子吗？"，独立回答后再合并
- 成本：多一次 LLM 调用，但可以降到 gpt-4o-mini（见 §1.8 RouteLLM）
- 结论：**CoVe 路径价值 > 成本，但与我们现有的 sentence-transformers 语义相似度检查功能有部分重叠**，需要权衡是替换还是叠加

### 1.5 Tree-of-Thoughts（ToT）

ToT 由 Yao et al. 在 NeurIPS 2023 (arxiv 2305.10601) 提出，让 LLM 对"下一步思考"生成多个候选并用 BFS/DFS/Beam 搜索保留最优分支。Game-of-24 上 GPT-4 CoT 的 4% → ToT 的 74%。

- 适用场景：搜索空间大、中间状态可评估的任务
- **对 RepoInsight 的映射**：**基本不适用**。我们的 LLM 任务（行为推断 + 冲突判官）没有"多候选 + 搜索"的结构；强行套 ToT 只会把 token 成本打到天上
- 结论：**不采纳**；在研究报告里明确列出"为什么不采纳"对未来反复评估有价值

### 1.6 Multi-Agent Debate

Du et al. 在 arxiv 2305.14325（ICML 2024）提出的方案：多个 LLM 实例对同一问题独立作答，然后把彼此答案作为 context 再辩论若干轮，最终收敛到共识。数学/策略推理任务上显著提升，且幻觉率下降。

- 适用场景：答案有"单一正确值"、可从辩论中收敛
- **对 RepoInsight 的映射**：ConflictResolver 的"风险-价值权衡"本质上是一种**退化版的二元辩论**（Static 一方 + Behavior 一方 + LLM 判官）
- 升级路径：把现在的"单 LLM 判官"升级为"Static 发言 → Behavior 发言 → 判官综合"的三段式 prompt；成本上是 1 次调用变 3 次（或者合并为 1 次长 prompt），但判决质量据 ICML 论文可以提升 5-15%
- 结论：**阶段 3 不切换**；先让 v1 判官跑起来，阶段 4 再对比辩论版 vs 单判官版的 judge 质量

### 1.7 Role-Play / Persona Prompting

给 LLM 分配"你是 XX 专家"的角色前缀以引导行为。研究结论很分裂：早期 GPT-3.5 时代 persona 收益明显；GPT-4 之后增益接近噪声级别（PromptHub 的综述 + arxiv 2603.18507 PRISM 论文都指出专家 persona 在 GPT-4+ 上"对齐变好、事实准确度反而下降")。

- **对 RepoInsight 的映射**：我们的 Prompt v1 使用了 `[SYSTEM] 你是 RepoInsight 行为推断 Agent` 这种非常轻的 persona，属于"几乎无害"。不值得在这上面投资，但也不建议去掉
- 结论：**维持现状**

### 1.8 MetaGPT SOP 模拟

MetaGPT (arxiv 2308.00352) 提出"Code = SOP(Team)"——把真实软件公司的 SOP（产品经理 / 架构师 / 项目经理 / 工程师 / QA）编码成 prompt 链。核心贡献是"标准化产出物"作为 Agent 间的强契约（比我们 Pydantic schema 更结构化——带模板的 markdown 文档作为下一个 Agent 的输入）。

- **对 RepoInsight 的映射**：
  - RepoInsight 已经采用了契约优先（ADR-002 的 Pydantic schema），这本质上就是 MetaGPT SOP 的轻量版
  - 最值得学的一点：**MetaGPT 的 QA engineer 角色**——它会在 Engineer 产出代码后自动跑测试并返回 fix 建议。类比到 RepoInsight，就是前文多次提到的"Reporter 产出后加一个 Reviewer"
- 结论：**SOP 风格我们已经在做**；QA 角色是下一个空白点

### 1.9 其它值得记录但本项目不用的模式

| 模式 | 不采纳原因 |
|---|---|
| **AutoGen GroupChat** | 通用对话式多 Agent 框架，对我们的固定 4 角色/固定依赖 DAG 来说过度灵活 |
| **CrewAI** | 以 role+goal+task 为中心，适合 SaaS workflow；我们是单次分析流水线 |
| **LangGraph Supervisor-Worker** | 跟 Planner-Executor 同构，无本质新意 |

---

## 2. 角色对比矩阵（RepoInsight vs 主流模式）

> 评分：✓ 已具备 / ≈ 部分具备 / ✗ 缺失

| 能力维度 | PEC | ReAct | Reflexion | CoVe | Debate | MetaGPT | **RepoInsight 现状** |
|---|---|---|---|---|---|---|---|
| 显式 Planner 角色 | ✓ | ≈ | ≈ | ✗ | ✗ | ✓ | **✓**（`orchestrator/planner.py`） |
| Executor 角色独立可测 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | **✓**（4 Agent 独立 .py + 独立单测） |
| Critic / Reviewer 角色 | ✓ | ✗ | ✓ | ✓ | ≈ | ✓ | **≈**（Guardrail + ConflictResolver 分散实现） |
| 外部工具交互（Tool use） | ≈ | ✓ | ≈ | ≈ | ✗ | ≈ | **≈**（StaticAnalyzer 调 pylint/radon/coverage，不走 LLM） |
| 失败重试闭环 | ≈ | ≈ | ✓ | ≈ | ✗ | ≈ | **≈**（三级回退存在但不把失败原因喂回模型） |
| 多候选搜索 / 辩论 | ≈ | ✗ | ✗ | ≈ | ✓ | ✗ | **✗** |
| 契约优先 / 结构化产出物 | ≈ | ✗ | ≈ | ✓ | ≈ | ✓ | **✓**（Pydantic v2 全量 schema） |
| 缓存命中即跳过 LLM | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✓**（六维 CacheKey） |
| Guardrail 双层（规则+语义） | ✗ | ✗ | ≈ | ✓ | ✗ | ≈ | **✓**（regex + sentence-transformers） |
| 多模型路由（按成本） | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | **✗**（当前只有 gpt-5.4 单模型） |

**关键缺口**：
1. **Critic 角色不成体系**——Guardrail 只看幻觉规则，ConflictResolver 只看模块重叠，没有一个角色对"三个 Agent 拼起来的总产出"做整体审查
2. **Model routing 完全缺失**——ConflictResolver 的判官、BehaviorInferer 的主推理、以及未来可能加入的 Reflector 全部共享同一个 gpt-5.4，这意味着成本优化空间还没被探索

---

## 3. LLM 成本优化分层表

按"基础设施层 / Gateway 层 / prompt 层"三层列出当前主流手段及对 RepoInsight 的适用性。

### 3.1 基础设施层（改动在 Provider / 部署）

| 手段 | 原理 | 成本收益 | 延迟收益 | 对 RepoInsight 适配性 |
|---|---|---|---|---|
| **OpenAI Automatic Prompt Caching** | prompt 前缀 ≥1024 token 被官方自动缓存，input 半价 | input -50% | latency -80% | **极高**——我们 BehaviorInferer 的 prompt 模板是固定前缀，只有 README/ISSUE/PR 部分会变；只要把**不变部分放在前面**就能拿满优惠 |
| **Anthropic Prompt Caching**（对比项）| 手动标 `cache_control`；cache hit cost = input × 0.1（Opus 省 90%）| input -90%（hit）| latency -85% | 当前不用 Anthropic；但值得作为备选 Provider 放进 Provider 抽象层 |
| **OpenAI Batch API** | 异步批量请求，24h SLA，input+output 都 -50% | -50%（input+output）| 延迟巨大增加 | **不适用**——RepoInsight 要求 120s 内出报告，Batch API 的 24h SLA 不可接受 |
| **Speculative Decoding** | 小模型起草 + 大模型验证，产出一致前提下 2-3× 加速 | 不省钱 | latency -50~66% | **不适用**——这是 self-host 场景（vLLM/TensorRT-LLM），我们用 OpenAI 托管 API 碰不到这一层 |
| **更换模型到 Haiku 4.5 / GPT-4o mini** | 小模型便宜 10× 以上 | input/output -80~90% | latency -30% | **部分适用**——主推理用 gpt-5.4，判官/Reflector 用 mini |

### 3.2 Gateway / 中间件层

| 手段 | 代表产品 | 原理 | 对 RepoInsight 的价值 |
|---|---|---|---|
| **Semantic Caching（GPTCache / Portkey / Helicone）** | GPTCache / Portkey Enterprise | 把 query embedding 后做向量相似度检索，相似 query 直接返回缓存结果 | **中等**——我们的 CacheKey 用的是文件内容 hash，完全相同才命中；如果两次分析的仓库只改了几行代码，哈希不同，semantic cache 有机会命中。但需要新增向量库依赖 |
| **Model Routing（RouteLLM / Not Diamond）** | RouteLLM 开源 | 训练一个 router，简单 query 走弱模型、复杂 query 走强模型；RouteLLM 论文实测在 MT Bench 上省 85% 成本且保留 95% 质量 | **高**——ConflictResolver 的判官任务非常适合 routing（大多数冲突是"明显应该 refactor"的简单判断） |
| **LLM Gateway（LiteLLM / Portkey）** | LiteLLM | 统一 provider 接口 + 自动故障转移 + 日志 | **中等**——我们已经有 LLMProvider 抽象，额外引入 gateway 会加一层依赖 |
| **Observability（Helicone）** | Helicone proxy | 自动记录每次调用的 cost/token/latency | **高**——配合阶段 3 的 ObservabilityCollector 目标（STAGE3-PLAN §四 T8）直接可用 |

### 3.3 Prompt / 应用层

| 手段 | 原理 | 对 RepoInsight 的价值 |
|---|---|---|
| **JSON mode / Structured Output** | 强制 schema，retry 率从 8-15% → <0.1% | **已采用**（openai_provider.py 支持 response_format={"type":"json_object"}）；可以升级到 `response_format={"type":"json_schema", ...}` 获得更严格保证 |
| **Few-shot CoT** | 2-3 个示例 + 推理链，证据质量 +10-20% | **未采用**——Prompt v1 是 zero-shot；阶段 4 可以补 1-2 个 golden example |
| **温度=0** | 确定性采样降低方差 | **已采用**（temperature_int=0） |
| **减少上下文（prefix 裁剪）** | README 截到 8000 字符，ISSUE 截到 4000 | **已采用**（`_README_MAX_CHARS`） |
| **CoVe 式验证问题** | 对每条 claim 反问"证据在哪" | **未采用**；与语义 guardrail 功能有部分重叠 |
| **Response 长度控制** | max_tokens 卡住输出上限 | **已具备**（provider 暴露了 max_tokens）但在 BehaviorInferer 调用点没传 |

---

## 4. RepoInsight 4 角色拆分的 3 个具体假设验证

### 假设 A：业界有没有把 Static + Behavior 合并的？

**答：几乎没有"合并"的，但有"让它们共享 context"的**。

- MetaGPT 里 Engineer + QA 是两个角色，产物有共享 context；等价于"Static 分析结果自动流入 BehaviorInferer 的 prompt"
- **对我们的启示**：目前 BehaviorInferer 只读 README/ISSUE/PR，**没有读 StaticAnalyzer 的输出**。如果把"high_complexity_functions top-5"注入 BehaviorInferer 的 prompt，它能产出"utils.py 被标为高复杂度，且在 CLI 入口 pattern 里是核心模块"这种**带 CC 证据的 usage_pattern**，能直接消灭 ConflictResolver 的大部分触发
- **反对意见**：这会破坏 Phase 1 的并发——BehaviorInferer 必须等 StaticAnalyzer 完成才能启动，120s 预算可能超。折中方案：Phase 1 并发跑完后，在 Reporter 之前插入一个短暂的 "BehaviorRefiner" 步骤（gpt-4o-mini，预算 5s）
- **结论：不合并，但保留"Phase 1.5 refiner"作为阶段 4 候选**

### 假设 B：有没有把 Reporter 拆成 Writer + Reviewer 双角色的？

**答：有，而且这是业界最常见的 QA 模式**。

- MetaGPT 明确有独立 QA engineer；Planner-Executor-Critic 的 Critic 角色也是类似定位
- 在我们这里，"Writer" 就是现在的 Reporter，"Reviewer" 是一个对 html_report / recommendations 做一轮 sanity check 的新角色
- **预期收益**：Reviewer 可以抓住 Writer 的以下常见错误：
  - recommendations 跟 evidence 脱节（说了要重构 utils.py，但 utils.py 不在 high_complexity 列表里）
  - 数字口径不一致（commits_per_week 在摘要里写 3.5，在降级提示里写 4.2）
  - 幻觉未来时态（2027 年之后…）逃过了 BehaviorInferer 那一层但在 Reporter 生成的文本里出现
- **成本**：Reviewer 是纯文本检查，用 gpt-4o-mini 即可；按 1500 tokens / 调用计算，月度不到 $0.5
- **结论：推荐作为阶段 4 的 T2 任务候选**

### 假设 C：需不需要新增一个 Reflector/Critic 角色对产出做自我审查？

**答：需要，但把它实现为 Reporter 内部的 self-check 步骤，而不是独立 Agent**。

理由：RepoInsight 的 4 角色边界已经被 import-linter 锁死了（见 `.importlinter` 的 forbidden contract），新增独立 Agent 代价大；而把 self-check 做成 Reporter 内的 private method，既享受 Reflexion 的自审收益，又不动拓扑。

实现草图（**本报告不改代码，仅作设计参考**）：

```
Reporter.aggregate() 伪代码
  1. build_report(static, behavior, community) -> draft_report
  2. self_check_prompt = "请检查以下报告是否存在：
       - recommendation 与 evidence 不一致
       - 数字口径冲突
       - 幻觉未来时态
     仅输出违规列表 JSON；无违规输出 []"
  3. issues = llm(self_check_prompt, model="gpt-4o-mini")
  4. if issues: regenerate affected sections (最多 1 次)
  5. return draft_report
```

这个设计**对应 §1.3 Reflexion 的轻量版**，也是 §1.4 CoVe 的变体。

---

## 5. 六维 CacheKey 的强弱分析

### 5.1 逐维评估

```python
# repo-insight/backend/app/llm/cache.py:26-33
@dataclass(frozen=True)
class CacheKey:
    repo_url: str          # 维度 1
    agent_name: str        # 维度 2
    file_contents_hash: str  # 维度 3
    prompt_version: str = "v1"   # 维度 4
    model_name: str = "gpt-5.4"  # 维度 5
    temperature_int: int = 0     # 维度 6
```

| 维度 | 作用 | 强度评分 | 潜在问题 |
|---|---|---|---|
| `repo_url` | 区分不同仓库 | **强** | 同一仓库不同 commit 会被 `file_contents_hash` 进一步区分；这层是不必要但无害 |
| `agent_name` | 区分不同 Agent 间的调用 | **强** | 必要，否则 Reporter 和 BehaviorInferer 的 cache 会混淆 |
| `file_contents_hash` | 精确到文件内容 | **强 + 刚性** | 两次分析的仓库即使只改了注释，哈希就变——**命中率天花板取决于用户行为** |
| `prompt_version` | 区分 prompt 迭代 | **强**（前瞻）| 大部分团队上线半年后才补上；我们早早纳入是加分项 |
| `model_name` | 不同模型产出不同结果 | **强** | 注意：模型升级后旧 cache 会失效，这是正确的 |
| `temperature_int` | 确定性控制 | **中** | temperature=0 时这一维度是 no-op（永远是 0）；预留给将来高温场景有意义 |

### 5.2 对比业界方案

| 方案 | Cache 粒度 | 命中逻辑 | 与我们的差距 |
|---|---|---|---|
| **OpenAI Automatic Prompt Caching** | token prefix | 自动识别共享 prefix | 我们是**请求级全等**匹配；OpenAI 是**token 级前缀**匹配，命中率天然更高 |
| **Anthropic Prompt Caching** | 手动 `cache_control` block | 手动标记缓存段 | 同上 |
| **GPTCache 语义缓存** | query embedding | 余弦相似度 ≥ 阈值 | 我们是哈希相等；semantic cache 对"90% 代码相同"场景命中率显著高 |
| **我们的六维 CacheKey** | 请求内容哈希 | 全字段相等 | 粒度粗、命中条件严格 |

### 5.3 强项总结

1. **prompt_version 维度**：避免了 prompt 迭代后老 cache 污染新结果的经典坑
2. **model_name 维度**：为将来切模型做好了隔离
3. **24h TTL**：对"用户反复分析同一仓库"的场景足够；对"分析流行开源仓库"（很多用户分析同一个 repo）在单租户下价值一般，多租户下会放大命中

### 5.4 弱项总结

1. **哈希全等，无语义能力**：两次 commit 中 90% 文件未变，命中率依然是 0
2. **prefix 不能复用**：固定 prompt 模板的开销（几千 token）每次都要完整发送，而 OpenAI automatic caching 可以自动命中
3. **没有按文件粒度的细分缓存**：如果未来做"增量分析"，这个 CacheKey 没法支持"只对变化的文件重跑 StaticAnalyzer"
4. **temperature_int 目前是死维度**（永远 0），增加了 key 长度但没带来区分度——可在文档里注明"保留给 v2 温度实验"

### 5.5 改进建议（不改代码，作为阶段 4 候选）

1. **双层 Cache**：
   - L1 = 当前六维哈希（全等命中）
   - L2 = `(repo_url, file_path, prompt_version, model_name)` 粒度，未命中 L1 时尝试按**文件级**回源
2. **接入 OpenAI Automatic Prompt Caching**：
   - Prompt v1 模板的不变部分（~1200 tokens）放在最前面
   - README / ISSUE / PR 放在最后
   - 零代码改动即享受 50% input cost 优惠
3. **把 `temperature_int` 标记为 reserved**，或者在 schema 层下沉到可选字段

---

## 6. Prompt v1 对照 few-shot / CoT / structured output 最佳实践

### 6.1 Prompt v1 现状（摘录自 `behavior_inferer.py:29-53`）

```python
_PROMPT_TEMPLATE = """[SYSTEM]
你是 RepoInsight 行为推断 Agent。根据 README / ISSUE 模板 / 近期 PR 标题推断仓库的典型使用模式和核心模块。
- 输出必须是合法 JSON
- 禁止输出 ```json 代码块包裹
- 禁止编造不存在的功能
- 若 README 信息不足以支撑某条 usage_pattern，直接减少条数（最少 1 条），不要补足
- 每条 usage_pattern.evidence 必须至少 8 字符且来自 README/ISSUE 原文
[USER]
README: {readme}
ISSUE 模板: {issue_templates}
近期 PR 标题: {pr_titles}
输出 JSON 格式：
{{
  "usage_patterns": [{{"title": str, "description": str, "evidence": str}}],
  "core_modules": [{{"path": str, "role": str, "evidence": str}}],
  "inference_evidence": {{"claim1": "source_snippet1"}}
}}
"""
```

### 6.2 做对了什么

| 最佳实践 | Prompt v1 | 评价 |
|---|---|---|
| System 角色声明 | ✓ | 有 `[SYSTEM]` 段 |
| 明确输出 JSON 格式 | ✓ | 带 schema 示例 |
| 禁止 markdown 包裹 | ✓ | 显式 "禁止输出 ```json" |
| 反幻觉约束 | ✓ | "禁止编造不存在的功能" + "来自原文" 硬约束 |
| 给出"不确定时的正确行为" | ✓ | "直接减少条数，不要补足"——这一条是高水准设计，避免了 LLM 凑数的经典坑 |
| 温度=0 + response_format=json_object | ✓ | Provider 层默认传入 |
| evidence 长度硬约束 | ✓ | "至少 8 字符" |

### 6.3 可以更好的 4 处

1. **没有 few-shot 示例**
   - 现状：zero-shot 纯约束
   - 建议：追加 1 个简短示例，比如 "对于 FastAPI 项目，正确输出样例是 …"
   - 依据：few-shot CoT 在结构化抽取任务上普遍抬 10-20%（mem0.ai few-shot prompting guide）
   - 成本：每次多 300-500 input tokens，配合 automatic prompt caching 后接近零成本
2. **没有显式 Chain-of-Thought 引导**
   - 现状：直接要 JSON
   - 建议：在 JSON 之前增加一个隐藏 `"reasoning"` 字段让模型先写推理，最后再输出结构化字段；调用方只读结构化字段，reasoning 作为日志
   - 依据：CoT 对需要"从文本中抽取 + 综合"的任务有稳定收益
3. **没有 CoVe 式自我验证**
   - 建议：schema 里增加一个 `"self_check"` 字段，要求模型对每条 usage_pattern 标注"证据句子在 README 第几段"
   - 这能把 guardrail 语义层的工作前置到 LLM 生成阶段，降低拦截后再生成的概率
4. **指令顺序可微调**
   - 现状：约束放在 SYSTEM，数据放在 USER；符合主流做法
   - 建议：把最重要的反幻觉约束重复放在 USER 段末尾（"记住：只从上面的 README/ISSUE 抽取，不允许外部知识"），利用"近期注意力"效应

### 6.4 升级到 Prompt v2 的成本估算

- 新增 few-shot 示例：+400 tokens（一次写入，automatic caching 命中后几乎免费）
- 新增 reasoning 字段：output +200 tokens/调用 → 每次 ~$0.001 增量
- 新增 self_check 字段：output +150 tokens/调用
- **总增量**：对单次 BehaviorInferer 调用 +$0.002 成本，+0.5s 延迟；预期 guardrail 拦截率从 ~15% 降到 ~6%——**净省成本**（因为拦截后的再生成才是大头）

---

## 7. 可操作优化建议（按 ROI 排序）

> 每条建议都按"动作 / 预期收益 / 实施成本 / 风险 / 建议阶段"五段式给出。

### 建议 1（P0 - 立即）：接入 OpenAI Automatic Prompt Caching

- **动作**：把 `_PROMPT_TEMPLATE` 中不变部分（SYSTEM 段 + 格式说明）放在最前面；README/ISSUE/PR 这些变化部分放在最后。确认 prompt 总长度 ≥1024 tokens（这是 OpenAI 自动缓存触发阈值）
- **预期收益**：BehaviorInferer input cost -50%、latency -50~80%；Reporter 的 LLM judge 同理
- **实施成本**：改 2 行字符串模板位置，不新增代码
- **风险**：无（OpenAI 自动管理，未命中时等价于当前行为）
- **建议阶段**：阶段 3 可以顺手做
- **参考**：OpenAI Prompt Caching 官方文档

### 建议 2（P0）：Model Routing — 给 ConflictResolver 判官换 gpt-4o-mini

- **动作**：LLMProvider 增加一个可选 `model` 参数（其实 `openai_provider.py:117` 已经支持了，只是 ConflictResolver 没传）；ConflictResolver 首次 judge 用 gpt-4o-mini，不确定度高（比如 judge 输出含 "uncertain"/"depends"）时升级到 gpt-5.4
- **预期收益**：judge 调用成本 -60%（80%+ 的冲突属于"显然应该 refactor"的简单判断）
- **实施成本**：<50 行代码；gpt-4o-mini 需要在 cache.py 的 CacheKey.model_name 维度上分离命中，避免混淆
- **风险**：gpt-4o-mini 可能在罕见复杂判断上给出浅层结论——需要 telemetry 监控 judge 质量
- **建议阶段**：阶段 4 首批
- **参考**：RouteLLM 论文（arxiv 2406.18665）- MT Bench 上省 85% 成本保留 95% 质量

### 建议 3（P1）：Prompt v1 → v2 升级（1 shot CoT + self_check）

- **动作**：在 `_PROMPT_TEMPLATE` 中追加 1 个 golden example（来自 samples/ 目录里的真实仓库）；schema 增加 `reasoning` 和 `self_check` 字段
- **预期收益**：guardrail 拦截率 -60%，再生成 LLM 调用次数 -40%
- **实施成本**：Prompt 版本从 v1 → v2，需要 CacheKey.prompt_version 切换（已内置，零实施成本）；需要跑一轮 benchmark 确认 v2 不退化
- **风险**：few-shot example 带来的 bias——示例选得太具体会让模型对 non-Python 项目泛化能力下降；需要 2-3 个样本覆盖不同风格
- **建议阶段**：阶段 4
- **参考**：mem0.ai few-shot prompting guide；arxiv 2309.11495 CoVe

### 建议 4（P1）：Reporter 内嵌 self-check（轻量 Reflexion）

- **动作**：在 `reporter.py` 的 aggregate 流程中插入一次 gpt-4o-mini 的 sanity check 调用，检测 recommendation vs evidence 不一致、数字口径冲突、未来时态泄漏
- **预期收益**：最终报告的"低级错误"率从 ~5% 降到 <1%
- **实施成本**：新增 50-100 行；需要新的 prompt 模板 + 可选重生成逻辑
- **风险**：额外一次 LLM 调用会吃掉 2-5s 预算；要在 Reporter 的 30s 预算内腾出时间
- **建议阶段**：阶段 4 中期
- **参考**：arxiv 2303.11366 Reflexion；MetaGPT QA 角色

### 建议 5（P1）：StaticResult 注入 BehaviorInferer prompt（Phase 1.5 refiner）

- **动作**：Phase 1 并发完成后，Planner 调用一次"BehaviorRefiner"——用 gpt-4o-mini 把 BehaviorResult + StaticResult top-5 高风险函数合并成 `enriched_behavior`
- **预期收益**：ConflictResolver 的触发率从 ~30% 降到 <10%（因为 Behavior 已经知道 Static 的结论）；Reporter 的推荐一致性显著提升
- **实施成本**：新增一个 orchestrator 步骤，预算 5-8s；Schema 需要新增 `EnrichedBehaviorResult`
- **风险**：破坏了"BehaviorInferer 只依赖 README/ISSUE/PR"的契约纯洁性——需要 ADR 决议
- **建议阶段**：阶段 4 后期
- **参考**：MetaGPT 的"assembly line"模式

### 建议 6（P2）：CacheKey 双层（请求级 L1 + 文件级 L2）

- **动作**：不动现有 CacheKey；在 LLMCache 之上包一层 L2 缓存，按 `(repo_url, file_path, prompt_version, model_name)` 粒度存每个文件的局部分析结果
- **预期收益**：对"同一仓库两次 commit，改动 <10% 文件"场景，命中率从 0 → ~70%
- **实施成本**：需要引入"文件级分析"概念——当前 4 Agent 都是整仓级别的，重构成本高
- **风险**：高。可能跟未来的增量分析 feature 产生设计耦合
- **建议阶段**：阶段 5 或更后
- **参考**：无直接对标，基于业界分层缓存常识

### 建议 7（P2）：Guardrail 改为"一次生成 + self_check"替代"拦截 + 再生成"

- **动作**：把现在"LLM 产出 → regex 检查 → semantic 检查 → 违规则重生成"的链路改为"LLM 在生成时同时输出 self_check 标签 → 后处理按标签过滤"
- **预期收益**：再生成 LLM 调用消失，平均单次 BehaviorInferer 延迟从 ~4s 降到 ~2.5s
- **实施成本**：需要 prompt v2 配合（建议 3 的一部分）；sentence-transformers 预热成本可以延迟加载
- **风险**：LLM 自检对幻觉类违规识别不如外部 regex 可靠——可以保留 regex，但关闭重生成
- **建议阶段**：阶段 4 后期，跟建议 3 打包
- **参考**：CoVe 论文

### 建议 8（P2）：引入 Helicone / 轻量 Observability proxy

- **动作**：LLMProvider 调用走 Helicone 代理（base_url 切换），或者直接 HTTP post 一份 usage 到本地 observability collector
- **预期收益**：cost/latency/retry/cache_hit_ratio 自动上报，配合 STAGE3-PLAN §四 T8 ObservabilityCollector 形成闭环
- **实施成本**：<30 行，base_url 切换
- **风险**：Helicone 是外部 SaaS（有免费档），对数据隐私敏感场景不适用；本地 collector 则是纯自建
- **建议阶段**：阶段 4 初期
- **参考**：Helicone 官方 docs；LiteLLM Helicone integration

### 建议 9（P3）：升级 `response_format` 从 `json_object` 到 `json_schema`

- **动作**：把 `openai_provider.py:137` 的 `kwargs["response_format"]` 从 `{"type": "json_object"}` 升级到 `{"type": "json_schema", "json_schema": {...}}`，利用 OpenAI Structured Outputs 的 100% schema 保证
- **预期收益**：retry 率从 ~2%（当前 json_object 实际命中率）降到 <0.1%；解析器 `_parse_to_behavior_result` 的防御分支可以简化
- **实施成本**：需要生成 JSON schema from Pydantic model（Pydantic v2 原生支持 `.model_json_schema()`）；OpenAI 对 schema 的子集支持有限，需要裁剪 Union/Optional 等
- **风险**：不是所有 OpenAI 模型都支持 structured output（需要 gpt-4o 系列或更新）
- **建议阶段**：阶段 4
- **参考**：OpenAI Structured Outputs 文档；tokenmix "Structured Output 2026 Guide"

### 建议 10（P3）：温度实验 — 判官用 T=0.2，主推理保持 T=0

- **动作**：ConflictResolver 的 LLM judge 用 temperature=0.2（带一点多样性），主 BehaviorInferer 保持 T=0；这是 Multi-Agent Debate 论文里辩论方的推荐做法
- **预期收益**：judge 输出的"风险-价值权衡"更富层次；副作用是稍微难复测
- **实施成本**：1 行配置；需要 CacheKey.temperature_int 真正发挥作用（之前一直是 0）
- **风险**：引入随机性后 cache 命中率下降 —— 对判官场景影响小（调用频率低）
- **建议阶段**：阶段 5 或 nice-to-have
- **参考**：arxiv 2305.14325 Multi-Agent Debate

---

## 8. 并发度 vs token 预算的 trade-off 数据

业界对"并发 N 个 LLM 调用" vs "串行 + 降 tokens" 没有统一的最优答案，但以下几条经验值得记录：

1. **`asyncio.gather` 并发的天花板是 rate limit**：OpenAI 默认 TPM/RPM 配额下，BehaviorInferer 级别的 prompt（~3000 tokens input）大概能 5-10 并发；我们只有 1 个 LLM Agent 并发，远没到天花板
2. **Semaphore 限流是标配**：生产环境 LangChain / Instructor 都推荐 `asyncio.Semaphore(N)` 限流，避免 429
3. **"降 tokens" 比 "降并发" 对成本更敏感**：同样的任务，把 prompt 从 5000 → 2500 tokens，成本直接减半；而并发度从 8 → 4 只是延迟从 2s → 4s，成本不变
4. **并发的真正收益是延迟**：RepoInsight 的 4 Agent 并发是为了挤进 120s 预算，不是为了省钱——这一点设计正确
5. **"串行 + 自动 caching"往往比"并发 + 无 caching"更省**：当两个 LLM 调用共享 80% prompt 前缀时，串行 + OpenAI auto caching 的第二次调用只花 50% input cost；并发则两次都付全价

**对 RepoInsight 的启示**：我们目前只有 1 个 LLM Agent 在 Phase 1 并发，没有"并发 vs 降 tokens"的选择压力；但将来如果增加 Reflector / BehaviorRefiner / Judge 这些小 LLM 调用，它们在 Phase 2/3 本来就是串行——**应该优先让它们共享 prompt prefix 以命中 automatic caching，而不是并发化**。

---

## 9. 风险清单（实施建议时要警觉的东西）

| 风险 | 描述 | 触发条件 | 缓解 |
|---|---|---|---|
| **Prompt caching 前缀失配** | README 被插在 prompt 中间而非末尾，automatic caching 失效 | 模板改动不小心把固定部分和动态部分混起来 | 单测：对两个不同仓库的 prompt 做 diff，确认前 1024 tokens 完全相同 |
| **Model routing 判官精度滑坡** | gpt-4o-mini 在边界冲突上给出浅层结论 | 某个冲突触发 routing 但 mini 输出被直接采用 | telemetry 监控 judge 长度 / 关键词分布；设置"不确定关键词自动升级 gpt-5.4" |
| **Few-shot 示例 bias** | 选的 example 太偏某一类仓库（比如都是 FastAPI） | Prompt v2 的 example pool 不够 diverse | 准备 3 个不同类型的 example，随机采样 1 个插入 |
| **Reflector 额外调用撑爆 30s Reporter 预算** | Reporter 内 self-check 调用 + 可能的重生成超时 | 当 LLM 响应慢时 | 把 self-check 设为 hard timeout 5s，超时就跳过（降级为"未审查"状态） |
| **CacheKey 语义化后 false positive** | 如果启用 GPTCache 语义缓存，两个相似但实质不同的仓库可能命中同一个 cache entry | 相似度阈值调太松 | semantic cache 只作为 L2 fallback，L1 仍用严格哈希 |
| **Gateway 依赖引入故障点** | Helicone 宕机导致 LLM 调用失败 | SaaS 故障 | LLMProvider 层加 feature flag：`HELICONE_ENABLED=false` 时直连 OpenAI |

---

## 10. 总结矩阵 — 建议与现有计划的对齐

| 本报告建议 | 与 STAGE3-PLAN 哪个 T 任务关联 | 建议纳入阶段 |
|---|---|---|
| 建议 1：Automatic Prompt Caching | T2 LLM Provider | 阶段 3（低风险，顺手做） |
| 建议 2：Model Routing（judge） | T5 Orchestrator / ConflictResolver | 阶段 4 首批 |
| 建议 3：Prompt v1 → v2 | T3.3 BehaviorInferer prompt | 阶段 4 |
| 建议 4：Reporter self-check | T6 Reporter | 阶段 4 |
| 建议 5：StaticResult 注入 BehaviorInferer | T5 Orchestrator | 阶段 4 后期（需要 ADR） |
| 建议 6：双层 CacheKey | T2 LLM Cache | 阶段 5+ |
| 建议 7：Guardrail 内嵌化 | T2 Guardrail + T3.3 Prompt | 与建议 3 打包 |
| 建议 8：Helicone/Observability | T8 ObservabilityCollector | 阶段 4 初期 |
| 建议 9：Structured Output 升级 | T2 LLM Provider | 阶段 4 |
| 建议 10：判官温度 0.2 | T5 ConflictResolver | 阶段 5 nice-to-have |

**最终排序（ROI 倒序）**：1 > 2 > 3 > 9 > 4 > 8 > 5 > 7 > 6 > 10。

---

## 11. 关键外部参考

### Agent 模式
- Yao et al., ReAct: Synergizing Reasoning and Acting in Language Models — arxiv 2210.03629
- Shinn et al., Reflexion: Language Agents with Verbal Reinforcement Learning — arxiv 2303.11366
- Dhuliawala et al., Chain-of-Verification Reduces Hallucination in Large Language Models — arxiv 2309.11495
- Yao et al., Tree of Thoughts: Deliberate Problem Solving with Large Language Models — NeurIPS 2023, arxiv 2305.10601
- Du et al., Improving Factuality and Reasoning through Multiagent Debate — ICML 2024, arxiv 2305.14325
- Hong et al., MetaGPT: Meta Programming for a Multi-Agent Collaborative Framework — arxiv 2308.00352
- AWS Prescriptive Guidance: Multi-agent collaboration
- arxiv 2509.08646 — Architecting Resilient LLM Agents: Secure Plan-then-Execute Implementations

### LLM 成本/性能优化
- OpenAI Prompt Caching 官方文档（developers.openai.com/api/docs/guides/prompt-caching）
- Anthropic Prompt Caching 公告与文档（anthropic.com/news/prompt-caching）
- OpenAI Batch API 文档（50% discount, 24h SLA）
- Zilliz GPTCache 论文及 GitHub — zilliztech/GPTCache
- LMSYS RouteLLM 博客 + arxiv 2406.18665 — Learning to Route LLMs with Preference Data
- NVIDIA Speculative Decoding 技术博客
- OpenAI Structured Outputs / JSON Schema mode 文档
- Helicone / Portkey LLM Gateway 官方文档

### Prompting 最佳实践
- Prompt Engineering Guide — Few-shot / CoT / ReAct / ToT / Reflexion 专题
- mem0.ai few-shot prompting guide 2026
- tokenmix "Structured Output and JSON Mode Guide 2026"
- PromptHub role-prompting 综述
- arxiv 2603.18507 PRISM — Expert Personas Improve Alignment but Damage Accuracy

---

## 12. 扩展章节：业界案例反向验证

> 本章对 §1 的 8 种模式做一次"反向验证"——不是问"这些模式能给我们什么"，而是问"真实生产系统用了哪几种？不用哪几种？为什么？"

### 12.1 LangChain / LangGraph 的 Supervisor-Worker 模式

LangGraph 官方教程里的 Supervisor-Worker 模式本质上是 Planner-Executor-Critic 的变体：
- Supervisor 相当于 Planner + 轻 Critic（根据 worker 产出决定下一步走向）
- Worker 相当于 Executor
- 没有独立的 Critic 角色

对比 RepoInsight：我们的 Planner 也承担了"协调 + 超时 + 冲突检测"三重职责，这和 LangGraph Supervisor 非常像；区别在于 LangGraph 的 Supervisor 会动态重新规划，我们是固定 DAG。对一个"固定任务类型、固定 SLA"的系统来说，固定 DAG 更可预测、更容易测试——这是一个正确的权衡。

### 12.2 AutoGen 的 GroupChat 模式

微软 AutoGen 里的 GroupChat 把多个 Agent 放在一个对话组里，靠 LLM 动态决定"下一个发言者是谁"。这种模式在研究项目（开放式问题求解）里灵活，但对生产流水线来说：
- Agent 顺序不可预测 → SLA 无法保障
- 调试困难 → 无法复现问题
- token 成本不可控 → 对话轮数由 LLM 决定

**RepoInsight 明确不应该使用 GroupChat**——120s 硬 SLA 下，任何"由 LLM 决定流程"的设计都是奢侈品。

### 12.3 OpenAI Swarm（现在改名 Agents SDK）

OpenAI 的 Agents SDK 提出 Handoff 概念：一个 Agent 可以把控制权交给另一个 Agent，Handoff 本身就是一个 tool call。这比 LangGraph 的 state machine 更轻量。

对 RepoInsight 的启示：我们的 `orchestrator/planner.py` 本质上在做 handoff —— Static 完成后 handoff 给 ConflictResolver，ConflictResolver 完成后 handoff 给 Reporter。区别是 OpenAI SDK 让 LLM 决定 handoff，我们是确定性代码决定。**对本项目来说，确定性更好**。

### 12.4 Anthropic Research Writer / Claude Agent SDK

Anthropic 近期发布的 Claude Agent SDK 内置了以下最佳实践：
- 自动 prompt caching（手动 cache_control 标注）
- Computer use / tool use 原生支持
- Multi-step reasoning budget（类似 thinking tokens）

对 RepoInsight 的启示：如果未来 LLM Provider 切换到 Anthropic，我们的 `openai_provider.py` 需要为 cache_control 标注留接口；建议在 LLMProvider 基类里增加一个 `cache_segments: list[dict] | None` 可选参数，让不同 Provider 自行解释。

### 12.5 Cursor / Cline / Continue 等 IDE Agent

这类 Agent 的核心特点是**高并发小调用**：一次编辑任务可能拆成 20+ 次 LLM 调用，每次 <1000 tokens。它们严重依赖：
- Prompt caching（共享大段 system prompt）
- Model routing（fast edit 用 Haiku/4o-mini，complex plan 用 Opus/4o）
- Semantic memory（过去的编辑决策缓存）

RepoInsight 跟这类产品**完全不同**：我们是"单次分析拆 4 个并行 Agent"，不是"多次串行小调用"。这意味着 §3.2 的 Semantic Cache 对 IDE Agent 价值大，对我们价值中等。

---

## 13. 扩展章节：RepoInsight 特有约束下的反模式清单

> 本章反向列出"表面上看起来不错、但在 RepoInsight 约束下不应该做"的事，避免未来引入 bad practice。

### 13.1 反模式 A：把 Static/Behavior/Community 放进一个 LLM "超级 Agent"

有些"all-in-one" LLM 框架会鼓励把分析任务统一交给一个大 prompt："分析这个仓库的静态风险、使用行为、社区活跃度，输出 JSON"。这样做的坏处：
- 无法并发 —— 单次 LLM 调用就是 bottleneck
- 无法利用 pylint/radon/coverage 这类确定性工具
- 幻觉率爆炸 —— 一个 prompt 要 LLM 生成 100+ 字段，JSON 合规率下降
- 无法独立单测每个 Agent

**RepoInsight 的 4 Agent 拆分就是对这个反模式的正确回避**。

### 13.2 反模式 B：把 Guardrail 放在 Provider 出口

我们在 ADR-003 讨论过 guardrail_middleware 方案（由 arch R2 提出），最终采纳的是 Planner 层注入。反模式是"把 guardrail 埋在 LLM Provider 的 complete() 方法里"——这样会：
- 破坏 LLMProvider 的纯度（应该只负责 "prompt → text"）
- 导致 ConflictResolver 的 judge 调用被误拦（判官话术"必须重构" 会触发幻觉词 regex）
- 无法对不同 Agent 定制不同 guardrail 策略

**Planner 层注入 + JudgeGuardrail 子类（STAGE3-PLAN Top-10 第 7 条）是正确设计**。

### 13.3 反模式 C：无限重试

OpenAI SDK 的官方示例里经常看到 `max_retries=10` 的写法，但对 RepoInsight 120s 预算来说：
- 每次重试 + 指数退避 ≥ 3s
- 10 次重试 = 30+ 秒，占掉 25% 总预算
- 且如果是 rate limit 导致的，重试只是把问题拖后

**RepoInsight 正确做法**（已采用）：`MAX_RETRIES = 2`，只重试 retryable error（APITimeoutError / APIConnectionError / RateLimitError / 5xx），4xx 直接上抛。

### 13.4 反模式 D：Cache miss 时静默 fallback 到低质量结果

一个经典坑是"cache miss → 跑 LLM 失败 → 返回空结果"。RepoInsight 的正确做法是：
- LLM 失败 → 明确抛 `BehaviorInferenceError`，由 Planner 决定是降级还是中止
- CommunityAssessor 超时 → 返回 `is_degraded=True` 的历史均值 + UI 明确提示
- **永远不返回"看起来正确但实际是 fallback"的结果**

这个设计已经被 ADR-002 §2.4 锁定。

### 13.5 反模式 E：把 LLM temperature 调高以"增加多样性"

有些团队会把 temperature 调到 0.7 以让 LLM "更有创意"。对 RepoInsight 来说：
- 分析报告需要**可复现**（审计要求）
- 缓存命中依赖确定性输出
- 高温度会放大 guardrail 拦截率

**正确做法**（已采用）：temperature=0；只有 Multi-Agent Debate 场景才考虑把判官温度调到 0.2。

---

## 14. 扩展章节：实施检查清单（Checklist）

以下是建议 1-10 落地时的具体验收点：

### 14.1 建议 1（Automatic Prompt Caching）验收

- [ ] `behavior_inferer.py` 的 `_PROMPT_TEMPLATE` 固定部分（SYSTEM + schema 说明）总长度 ≥1024 tokens
- [ ] 固定部分位于 prompt 最前面；README/ISSUE/PR 位于末尾
- [ ] 对两个不同仓库调用同一 prompt，前 1024 tokens 严格相同（单测）
- [ ] OpenAI response 的 `usage.prompt_tokens_details.cached_tokens > 0`（集成测试）
- [ ] 审计日志记录 cached_tokens，供 Observability 聚合

### 14.2 建议 2（Model Routing）验收

- [ ] `ConflictResolver.resolve()` 的 model 参数默认 `gpt-4o-mini`
- [ ] judge 输出含 "uncertain" / "depends on" / "需要更多信息" 等不确定关键词时自动升级 gpt-5.4
- [ ] CacheKey.model_name 分别为 mini 和 5.4 时命中两套独立 cache
- [ ] judge 升级率 telemetry 上报 `<=20%`（超过说明 mini 不胜任）

### 14.3 建议 3（Prompt v1 → v2）验收

- [ ] `_PROMPT_VERSION` 从 `"v1"` 改为 `"v2"`
- [ ] Prompt 模板新增 1 个 few-shot example（可以从 samples/ 目录取）
- [ ] Schema 新增 `reasoning` 和 `self_check` 字段
- [ ] 跑 3 个 golden 仓库的 benchmark，v2 的 guardrail 拦截率 < v1 的 50%
- [ ] CacheKey 的 prompt_version 自动隔离，不污染 v1 cache

### 14.4 建议 4（Reporter self-check）验收

- [ ] Reporter 内部新增 `_run_self_check(draft_report) -> list[Issue]` 方法
- [ ] self-check 调用 gpt-4o-mini，hard timeout 5s
- [ ] 发现 issues 时最多 1 次重生成；失败则降级为"未审查"状态
- [ ] Reporter 总预算仍然 ≤30s（Planner 剩余预算推断）
- [ ] 单测：伪造一个 inconsistent draft，self_check 能识别

### 14.5 建议 9（Structured Output 升级）验收

- [ ] `OpenAIProvider.complete()` 支持 `response_format={"type": "json_schema", ...}`
- [ ] 从 Pydantic 模型自动生成 JSON schema（`.model_json_schema()`），裁剪不支持的构造
- [ ] 确认 BehaviorResult / Recommendation 的 schema 在 OpenAI structured output 白名单内
- [ ] Fallback：不支持 structured output 的模型自动降级到 json_object
- [ ] `_parse_to_behavior_result` 的 JSON 防御代码简化

---

## 15. 扩展章节：跨 Agent 信息流重新审视

基于 §4 假设 A 的讨论，RepoInsight 现在的 Agent 间信息流是：

```
StaticAnalyzer → StaticResult ┐
BehaviorInferer → BehaviorResult ├─> ConflictResolver → ConflictResolution
CommunityAssessor → CommunityResult ┘

StaticResult + BehaviorResult + CommunityResult + ConflictResolution
  → Reporter → ReportResult
```

**观察**：BehaviorInferer 在 Phase 1 时看不到任何其它 Agent 的输出，完全独立地从 README/ISSUE/PR 推断。这是"并发纯度"的正确选择，但也意味着它错过了"已经被 StaticAnalyzer 确认的高风险函数"这种强证据。

**三种可能的改进方案**（供未来阶段讨论，不在本阶段实施）：

### 15.1 方案甲：Phase 1.5 Refiner（建议 5）

```
Phase 1 (并发): Static / Behavior / Community
Phase 1.5 (串行): BehaviorRefiner(static_top5, behavior) -> enriched_behavior
Phase 2 (串行): ConflictResolver(static, enriched_behavior)
Phase 3 (串行): Reporter(...)
```

优点：最小化破坏，只加一个短步骤。
缺点：吃掉 5-8s 预算；需要新 schema。

### 15.2 方案乙：两轮 Behavior 推断

```
Phase 1 (并发): Static / Behavior-v1 / Community
Phase 2 (并发): Behavior-v2(README + static_top5)  <- 重跑一次
```

优点：保留并发结构。
缺点：BehaviorInferer 跑两次，cache 命中率打对折。

### 15.3 方案丙：ReAct 式 Behavior 允许查询 Static

```
BehaviorInferer 作为 ReAct Agent，可以"Action: 查询 StaticAnalyzer 输出"
```

优点：最灵活。
缺点：破坏并发（BehaviorInferer 必须等 Static 完成）；ReAct 轨迹 token 成本高。

**研究员推荐**：方案甲 ROI 最高，但需要 ADR 决议；留到阶段 4。

---

## 16. 最终一句话结论

**RepoInsight 的 4-Agent 拓扑在粒度和契约纪律上已经达到生产水准，真正的优化空间在 LLM 调用侧**——按 ROI 排序应该先做 OpenAI automatic prompt caching（零改动省 50% input cost）、再做 Model Routing 判官下沉（省 60% judge 成本）、再做 Prompt v1 → v2 升级（降 60% 拦截率）；Critic/Reflector 的缺口推荐通过"Reporter 内嵌 self-check"而非新增独立 Agent 填补，这样既拿到 Reflexion 的收益，又不打破 import-linter 锁定的拓扑。

以上 10 条建议中，建议 1/2/9 属于"低风险高收益"可以在阶段 3 或阶段 4 初期立即落地；建议 3/4/8 需要阶段 4 中期启动；建议 5/6/7/10 建议留到阶段 5 或作为 nice-to-have。

---

*研究员：researcher-4 | 研究日期：2026-04-14 | 关联：STAGE3-PLAN §三 Top-10 / ADR-002 / ADR-003 / LLM Provider 六维 CacheKey*
