# 阶段 5 v3 真实 e2e + 前端浏览器观察报告

- Task ID: `771c2263-3000-45c6-91ef-8c892aa8efcf`
- 执行人: stage5-v3-runner (QA Engineer)
- 执行日期: 2026-04-14
- 被测范围: 阶段 5 v3 最小修复集（6 处）+ 前端浏览器 UX 观察
- 前次报告: smoke-report-v4-integration.md（集成测试 PASS 151/151）
- 结论: **PART-PASS / 阶段 6 准入 = NO-GO**（1 个 Critical 修复未真正生效；1 个 Major 写入 wiring 仍缺失；前端端到端整体可用）

---

## 一、执行环境

| 项 | 值 |
|---|---|
| OS | Windows 11 Pro 10.0.26200 |
| Shell | git-bash |
| Python | 3.12.8 (uv venv) |
| uv | 0.9.18 (已同步 103 packages, Audited 77) |
| 前端 | Vite 5.4.21 + React 18, node_modules 已安装 |
| Playwright | 1.58.0, chromium headless |
| 后端 | uvicorn 127.0.0.1:8770, `SEMANTIC_VALIDATOR_BACKEND=stub` |
| 前端 | vite 127.0.0.1:5173, proxy /api→8770 |
| OPENAI_API_KEY | 已配置, 真实调用 gpt-5.4 |

**临时配置调整**: 本轮测试期间 `repo-insight/frontend/vite.config.ts` 的 proxy target 从 `http://127.0.0.1:8000` 改为 `http://127.0.0.1:8770`，因为系统 8000 端口被另一个无关 app 占用。测试完成后已恢复。

---

## 二、后端指标验证

### 2.1 /api/health
```
{"status":"ok","version":"0.1.0","timestamp":"2026-04-14T18:09:20Z","dependencies":{"sqlite":"ok","llm_provider":"ok"}}
```

### 2.2 /metrics (跑 records 成功后)
```
repoinsight_pipeline_duration_seconds_count   2
repoinsight_pipeline_duration_seconds_sum    35.062
repoinsight_llm_cost_usd_total                0.061460
repoinsight_llm_cost_usd{model="gpt-5.4"}     0.061460
repoinsight_cache_hit_rate                    0.0000
```

**观察**: LLM 成本透传链已打通（v4 v5real-runner 报告中 R1 BUG：llm_cost_usd_total 永远为 0 → v3 本轮 **PASS**），累计 $0.0615 符合预期。

### 2.3 llm_audit_log（R1 修复验证）
```
data/repo_insight_llm_audit.db
  tables: llm_audit_log, sqlite_sequence
  llm_audit_log rows: 0
  cols: id, timestamp, agent_name, model, prompt_tokens, completion_tokens, cost_usd, cache_hit, cache_key
```

**结果**: **PART-PASS** — 表已建（`_ensure_audit_table` 在 startup 正常运行），但**实际 LLM 调用后表依然 0 行**。
- 说明 v3 只修了 CREATE TABLE，没有真正接通 audit_logger.record() 到 SQL INSERT 的 wiring。
- /metrics 的 llm_cost_usd_total 显示 0.0615（透过 ObservabilityCollector 到 Prometheus 指标 wiring OK），而同一条链的 audit DB 分叉依然 broken。
- BUG-R1 部分修复，SQL 落库部分**未修复**。

### 2.4 Agent durations 4 键（R0 修复验证）
records 成功跑的报告 JSON:
```
agent_durations: {
  "static_analyzer": 6578,
  "behavior_inferer": 21734,
  "community_assessor": 2016,
  "reporter": 0
}
```
**结果**: **PASS** — 4 个键全部存在。`reporter: 0` 是因为 render 太快 int 取整为 0 ms，这是可接受的（v4 baseline 原 report 根本就没 reporter 键）。

---

## 三、e2e 端到端三场景

### TC-1 records (https://github.com/kennethreitz/records) — PASS

| 字段 | 值 | 期望 | 判定 |
|---|---|---|---|
| HTTP | 202 + job_id | 202 | PASS |
| total_pipeline_ms | 30328 | ≤ 120000 | PASS |
| recommendations | 3 条 | ≥ 3 | PASS |
| file_heatmap | 1 file | 非空 | PASS |
| emergency_mode | False | False | PASS |
| emergency_reason | null | null | PASS |
| guardrail.regenerate_count | 0 | ≥ 0 | PASS |
| community.commits_per_week | 0.0 | — | OBS（见 BUG-R2 持续） |
| community.unique_contributors | 0 | > 0 | **FAIL**（见 BUG-R2） |
| community.is_degraded | False | — | OBS |
| agent_durations 4 键 | ✓ | 4 键 | PASS |

**BUG-R2 仍然存在**：records 是真 git repo 但 unique_contributors=0, commits_per_week=0。CommunityAssessor 对浅克隆（`depth=50`）下的 git log 解析不充分；且 `is_degraded=False` 意味着它自认为数据有效 —— 这是一个错误的自我评估。

### TC-2 ai-quant-platform (本地真 git) — FAIL

| 字段 | 值 | 判定 |
|---|---|---|
| HTTP | 202 + job_id | PASS |
| 完成耗时 | 24.5s | — |
| total_pipeline_ms | 0 | **FAIL**（emergency fallback 覆盖） |
| emergency_mode | True | 不期望 |
| emergency_reason | planner_budget_exhausted | **错误标签** |
| agent_durations | `{}` 空 | FAIL |
| recommendations | 0 | FAIL |
| file_heatmap | 0 | FAIL |
| community.degraded_reason | "数据不可用（pipeline 降级）" | **非期望**，应该是 static 的真实原因 |

**真实根因**（已通过直连测试定位）：
- 直连 `BehaviorInferer.infer(ai-quant-platform)` = PASS, 2.7s 完成
- 直连 `StaticAnalyzer.run(ai-quant-platform)` = **FAIL**, 抛 `TimeoutError`（pylint 对 189 个非 .venv py 文件扫描超过 BUDGET_STATIC_S=30s）
- Planner 的 `asyncio.gather(return_exceptions=True)` 把 TimeoutError 放进 results[0]
- `_unwrap_or_raise(results[0], "StaticAnalyzer")` 直接 `raise` 该异常（见 planner.py:71-74）
- 因 Python 3.12 `TimeoutError is asyncio.TimeoutError`，冒泡到 `run_pipeline` 的外层 `except asyncio.TimeoutError:`（line 132）误贴 `planner_budget_exhausted` 标签

**这就是 BUG-NEW-2 的原始现场，v3 Fix 2 声称已修复但实际未修复。** v3 代码 line 133-134 的注释写着 "Only the outer wait_for's own TimeoutError reaches here; inner agent timeouts are consumed by _handle_community/_unwrap_or_raise"，但 `_unwrap_or_raise` 的实现（`raise result`）根本没有 consume inner timeout，它直接 re-raise。

正确修复方向：使用哨兵模式，将外层 `wait_for` 的 TimeoutError 转为自定义 `PipelineBudgetExhaustedError`，然后外层只 catch 这个类型；或在 `_unwrap_or_raise` 中把 TimeoutError 转换为一个非 TimeoutError 的 agent 特定异常。

### TC-3 AI团队框架 (非 git 目录，BUG-NEW-3 验收) — UNKNOWN / 不可验证

| 字段 | 值 | 期望 | 判定 |
|---|---|---|---|
| HTTP | 202 | 202 | PASS |
| community.is_degraded | True | True | 表面 PASS |
| community.degraded_reason | "数据不可用（pipeline 降级）" | "not a git repository" | **FAIL** |
| emergency_reason | planner_budget_exhausted | — | 与预期不符 |

**问题**：AI团队框架 同样有 182 个 .py 文件，StaticAnalyzer 同样会超时并冒到外层 emergency 路径。整个 pipeline 走了 emergency reporter，community 的 `degraded_reason` 被 EmergencyReporter 强制覆盖为"数据不可用（pipeline 降级）"，掩盖了 Fix 1 要验证的"not a git repository"原因。

**Fix 1 (BUG-NEW-3) 状态**：**不可验证** — 需要一个满足"非 git + py 文件数 ≤ 让 StaticAnalyzer 在 30s 内完成"的小仓库才能单独验证 community 的降级原因；或修复 TC-2 的 BUG-NEW-2 后重测。本轮找不到符合条件的 fixture 路径。

---

## 四、前端浏览器旅程（Playwright 观察）

基础环境: chromium headless, 1440x900 viewport, 目标仓库 `https://github.com/kennethreitz/records`

### 截图清单
| # | 文件 | 大小 | 描述 |
|---|---|---|---|
| 01 | 01-initial.png | 31 KB | 初始界面：header + RepoInput + EmptyState |
| 02 | 02-path-entered.png | 33 KB | 输入 GitHub URL |
| 03 | 03-analyzing-early.png | 45 KB | 点击"开始分析"后 1.5s 的早期进度面板 |
| 04 | 04-agents-running.png | 45 KB | 提交后 7.5s（WS 进度更新迟滞，内容与 03 基本相同） |
| 05 | 05-near-complete.png | 83 KB | 提交后 15.5s，**完整报告已渲染** |
| 06 | 06-report-full.png | 83 KB | 完整报告 + 标题栏 |
| 07 | 07-heatmap.png | 83 KB | ECharts 热力图区域（canvas） |
| 08 | 08-agent-durations.png | 83 KB | AgentDurationsPanel（4 行 Agent 耗时表） |

### 浏览器 console 错误
`browser-console.log`: **`no errors`** — 0 JS errors, 0 warnings, 0 request failures

### UX 观察

**优点**:
1. 界面布局清晰：左 384px 侧栏（RepoInput + ProgressPanel），右主区（报告展示）
2. 输入模式切换正常（GitHub URL / 本地路径 tab）
3. 进度面板展示 4 个 Agent 的独立状态条（静态分析 / 行为推断 / 社区评估 / 报告生成），视觉一致
4. 报告渲染完整：
   - 风险总览卡片
   - **ECharts 彩色热力图**（canvas 渲染，无报错）
   - 社区健康（耗时 0.0, 贡献者 0 — 显示原始数据）
   - **改进建议 3 条**：`Refactor 'dl' in records.py (CC>12)` + 两条 `Add unit tests to improve coverage`
   - **AgentDurationsPanel 正确展示 4 个 Agent**：static_analyzer 6.57s / behavior_inferer 21.7s / community_assessor 2.0s / reporter 0.0s（**v3 新增组件 UX PASS**）
5. 0 console error / 0 network error

**问题**:
1. **U-1 (Minor) 进度面板 WS 事件延迟或更新不及时**：截图 03（提交后 1.5s）显示 4 个 Agent 全部 "等待中 0%"，然而后端已并行开始跑；截图 04（+6s）仍与 03 几乎完全一致，直到 05（+14s）才跳到 100% 完成态。用户看不到 "stage=analysis status=running" 的中间变化，给人卡顿错觉。
2. **U-2 (Minor) 分析中时主内容区仍显示"尚未生成报告"**：右侧主区在整个 analyzing 阶段一直是 EmptyState，没有一个 loading skeleton 或分析中动画，用户体验上"右边像卡死了"。
3. **U-3 (Minor) 改进建议有重复**：3 条中有 2 条完全相同的 "Add unit tests to improve coverage"，这是 v5-real BUG-R3 的延续，v3 未修复。
4. **U-4 (Observation) community 数据全 0 展示未警示**：即便 commits_per_week=0 / contributors=0 / is_degraded=False，前端把它当成有效数据渲染，没有一个 "数据可能不准确" 的 warning。

---

## 五、6 个 fix 逐项验证矩阵

| # | Fix 名 | 期望 | 实测证据 | 判定 |
|---|---|---|---|---|
| Fix 1 | BUG-NEW-3 CommunityAssessor 非 git 降级为 is_degraded=True + reason="not a git" | 非 git 目录 reason 含 "not a git" | TC-3 走 emergency 路径，community reason 被覆盖为 "数据不可用（pipeline 降级）"，无法单独验证 | **UNVERIFIABLE** |
| Fix 2 | BUG-NEW-2 Planner 顶层 except 不误贴 planner_budget_exhausted | 内层 static/behavior TimeoutError 不冒到外层 emergency 路径 | TC-2 ai-quant-platform 真实环境下，StaticAnalyzer 30s 超时 → 误贴 planner_budget_exhausted 标签走 emergency reporter。直连诊断已证实 v3 的 `_unwrap_or_raise` 实现与代码注释不一致 | **FAIL** |
| Fix 3 | R0 agent_durations 第 4 键（reporter） | ReportJsonResponse 含 reporter 键 | TC-1 records `agent_durations.keys() = [static_analyzer, behavior_inferer, community_assessor, reporter]` | **PASS** |
| Fix 4 | R1 llm_audit_log 表建表 | audit.db 含 llm_audit_log 表 | 表存在, cols=9；**但 0 rows**，INSERT wiring 依然 broken | **PART-PASS**（建表 OK，写入 wiring broken） |
| Fix 5 | 前端 AgentDurationsPanel 展示 4 Agent 耗时 | UI 可见耗时表 | 截图 05/08 可见 "各 Agent 耗时" 表, 4 行数据正确 | **PASS** |
| Fix 6 | BUG-NEW-6 取消 max/sum<0.7 SLA 硬门禁 | 不作为 FAIL 条件 | ReportJsonResponse 无 max/sum 计算（默认放行），前端也没有硬门禁 | **PASS** |

---

## 六、前端 console errors 清单

```
(browser-console.log)
no errors
```

---

## 七、阶段 6 准入建议

### 结论: **NO-GO**

**Blocker**（必须修复）:
1. **BUG-NEW-2 真修**（Fix 2 FAIL）: Planner `run_pipeline` 的外层 `except asyncio.TimeoutError` 依然会吞下内层 agent 超时异常并误贴 planner_budget_exhausted。需要用哨兵模式分离外层/内层 TimeoutError，或 `_unwrap_or_raise` 把内层 TimeoutError 转换为 agent-specific exception。这是**阻塞 CLAUDE.md 验收标准 #1**（AI-company 120s 产出报告）的根本原因，也是本轮发现的**唯一 Critical 级 v3 回归**。

2. **BUG-R1 真修**（Fix 4 部分 FAIL）: `llm_audit_log` 表建了但 0 rows。LLM 调用 → ObservabilityCollector → metrics 这条链 OK（$0.0615 已计数），但 LLM 调用 → audit_logger → SQLite INSERT 这条链依然断裂。需要在 `app.llm.audit.audit_logger.record()` 里真的 INSERT。

**Major**（推荐修复）:
3. **BUG-R2 持续**: records 真 git repo 的 community 数据全 0 且 `is_degraded=False`（自认为有效）。CommunityAssessor 对浅克隆 git log 的解析有 bug，且缺少 "data empty → 降级" 的自我评估。
4. **BUG-R3 持续**: recommendations 中出现重复条目（records 报告："Add unit tests" 出现 2 次）。
5. **U-1 前端进度 WS 更新迟滞**: 用户观察不到 Agent running 中间态。

**Minor/Observation**:
6. **U-2 EmptyState 在分析中显示不友好**: 建议加 loading skeleton。
7. **U-3 无降级数据 UX 警示**: 当 community 全 0 时前端应有 warning label。
8. **Fix 1 未真正验证**: 修复 BUG-NEW-2 后用小非 git 仓库单独跑才能验证。

### 已 PASS 项（可进入下一轮）
- 前端基础端到端（records 成功路径）：0 console errors, 0 network errors, 报告 + 热力图 + AgentDurationsPanel 完整渲染
- /metrics 含 llm_cost_usd 真实值（透过 Observability → Prometheus wiring OK）
- R0 4 键 PASS, Fix 5 前端展示 PASS, Fix 6 SLA 解绑 PASS

### 总评: **6 个 fix 实际 2 完整 PASS / 2 部分 PASS / 1 FAIL / 1 UNVERIFIABLE**
本轮证实 v3 的 Fix 2 和 Fix 4 只改了表象，没改根本。阶段 6 准入需要先让 v4 再修这两条。

---

## 八、证据文件清单

- `repo-insight/tests/e2e/screenshots/01-initial.png`（31 KB）
- `repo-insight/tests/e2e/screenshots/02-path-entered.png`（33 KB）
- `repo-insight/tests/e2e/screenshots/03-analyzing-early.png`（45 KB）
- `repo-insight/tests/e2e/screenshots/04-agents-running.png`（45 KB）
- `repo-insight/tests/e2e/screenshots/05-near-complete.png`（83 KB，含 ReportViewer + HeatmapChart + AgentDurationsPanel）
- `repo-insight/tests/e2e/screenshots/06-report-full.png`（83 KB）
- `repo-insight/tests/e2e/screenshots/07-heatmap.png`（83 KB）
- `repo-insight/tests/e2e/screenshots/08-agent-durations.png`（83 KB）
- `repo-insight/tests/e2e/browser-console.log`（"no errors"）
- `repo-insight/tests/e2e/smoke-report-v5-v3-local.md`（本报告）

### Playwright 脚本（临时，测试完清理）
- `repo-insight/tests/e2e/_stage5_v3_browser_observe.py`

### 临时配置
- `repo-insight/frontend/vite.config.ts` proxy target 由 `127.0.0.1:8000` 暂改为 `127.0.0.1:8770`（测试后恢复）
