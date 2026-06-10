# RepoInsight — Project Constraints (CLAUDE.md)

> Python开源仓库智能分析系统。通过4个专业Agent并行完成静态扫描、行为推断、社区健康评估、报告生成，产出带可交互热力图的HTML分析报告。

## 一、项目目标

用户粘贴**本地Git仓库路径**或**GitHub仓库URL**，点击"分析"，**120秒内**产出：
- 代码行级风险热力图（ECharts）
- 3条可执行改进建议
- 完整HTML报告（前端内嵌渲染）

## 二、严格四角色 Agent（每个一个独立 .py 文件）

| Agent | 文件 | 职责 | 输出Schema |
|---|---|---|---|
| **StaticAnalyzer** | `backend/app/agents/static_analyzer.py` | pylint+radon扫描 | `high_complexity_functions[]`, `low_coverage_modules[]` |
| **BehaviorInferer** | `backend/app/agents/behavior_inferer.py` | 读README/ISSUE模板/近3PR → LLM推理典型使用场景 | `usage_patterns[]`, `core_modules[]` |
| **CommunityAssessor** | `backend/app/agents/community_assessor.py` | 解析近30天git log | `commits_per_week`, `avg_issue_response_hours`, `unique_contributors` |
| **Reporter** | `backend/app/agents/reporter.py` | 聚合上述三者，生成HTML+ECharts热力图+Markdown建议 | `html_report`, `recommendations[]` |

**Planner**（`backend/app/orchestrator/planner.py`）：主协调者，负责并发调度、超时控制、冲突消解、Guardrail编织。

## 三、三大多智能体机制（必须实现）

### 3.1 结果冲突消解协商
- 场景：StaticAnalyzer 标 `utils.py` 高风险 vs BehaviorInferer 推断该模块高频调用
- 协议：Reporter 发起"风险-价值权衡"协商（调用 LLM 判官），产出平衡建议
- 实现：`backend/app/orchestrator/conflict_resolver.py`

### 3.2 异步聚合 + 超时降级
- CommunityAssessor 超 45s → Planner 触发缓存策略
- 降级话术："社区数据暂不可用，采用历史均值估算"
- 实现：`backend/app/orchestrator/timeout_guard.py`

### 3.3 幻觉防护链（GuardrailValidator）
- 所有 LLM 输出（仅 BehaviorInferer）必须经双层过滤：
  - **正则层**：禁止"2026年之后"等未来时态
  - **语义层**：与 README 原文相似度计算（sentence-transformers or TF-IDF cosine）
- 实现：`backend/app/guardrail/validator.py`

## 四、技术栈（已锁定）

| 层 | 技术 |
|---|---|
| Python | 3.12 + `uv` 管理 |
| Backend | FastAPI + asyncio + WebSocket + Pydantic v2 |
| 静态分析 | pylint, radon, coverage |
| LLM | OpenAI GPT-5.4（抽象 Provider 层便于切换） |
| 语义相似度 | sentence-transformers（all-MiniLM-L6-v2） |
| DB | SQLite（审计日志 + LLM 缓存） |
| Frontend | Vite + React 18 + TypeScript + TailwindCSS + shadcn/ui |
| 图表 | ECharts + react-echarts |
| 报告渲染 | react-html-parser + DOMPurify |
| 容器化 | Docker Compose |

## 五、目录结构

```
repo-insight/
├── backend/
│   ├── app/
│   │   ├── agents/           # 4个Agent（独立.py）
│   │   ├── orchestrator/     # Planner + 冲突消解 + 超时
│   │   ├── guardrail/        # 幻觉防护链
│   │   ├── llm/              # LLM Provider抽象
│   │   ├── api/              # FastAPI路由
│   │   ├── models/           # Pydantic Schema
│   │   ├── services/         # 仓库克隆/缓存
│   │   └── main.py
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/       # 输入框/进度条/报告渲染
│   │   ├── hooks/            # useWebSocket
│   │   ├── types/            # TS 类型（与后端 Pydantic 对齐）
│   │   └── App.tsx
│   ├── index.html
│   └── package.json
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ADR-*.md
│   └── API-CONTRACT.md
├── samples/                  # 测试仓库URL列表
├── scripts/                  # 一键启动脚本
├── tests/                    # e2e
├── docker-compose.yml
├── .env / .env.example
└── CLAUDE.md
```

## 六、开发约束

1. **语言**：默认中文响应
2. **Agent独立性**：4个Agent必须可独立运行、独立测试、独立替换
3. **契约优先**：Pydantic Schema 先行，前后端共享类型定义
4. **超时控制**：总预算 120s，单 Agent 不得超过自身预算
5. **安全**：LLM Key 只在 `.env`，禁止硬编码；克隆仓库只读、禁止执行
6. **缓存**：LLM 调用结果按 `(repo_hash, agent_name)` 缓存 24h
7. **测试**：单元测试覆盖率 ≥ 70%，e2e 至少 3 个不同技术栈样本仓库

## 七、验收标准

- [ ] 输入 `https://github.com/CronusL-1141/AI-company` 可在 120s 内产出报告
- [ ] 4 个 Agent 并发执行，前端实时看到进度
- [ ] 模拟 CommunityAssessor 超时 → 自动降级
- [ ] 模拟 LLM 输出含幻觉词 → Guardrail 拦截
- [ ] 模拟 Static/Behavior 冲突 → Reporter 协商产出平衡建议
- [ ] HTML 报告在前端正确渲染热力图
