# RepoInsight 阶段4 集成测试报告 v4-integration

- **Task ID**: `3dd30d54-1677-4769-890c-eadc96b7af16`
- **执行人**: integration-runner (QA Engineer)
- **执行日期**: 2026-04-14
- **被测范围**: 阶段3 (4 Agent + Guardrail + Planner + Reporter) + 阶段4 (P0-2 Input Guardrail / P0-3 Emergency Reporter / P0-4 Judge Model Routing / P0-5 Tree-sitter RepoMap)
- **前次报告**: smoke-report-v3.md (15.7/16, PASS, 94 tests)
- **结论**: **PASS — pytest 151/151, 9/9 必做验证 PASS, 发现 1 个非阻塞行为 gap，建议进入阶段5**

---

## 一、执行环境

| 项 | 值 |
|---|---|
| OS | Windows 11 Pro 10.0.26200 |
| Shell | git-bash (MSYS) |
| Python | 3.12.8（系统直装） |
| 后端根目录 | `repo-insight/backend` |
| pytest 命令 | `python -m pytest -q --ignore=tests/fixtures` |
| 集成脚本 | `tests/e2e_stage4_integration.py`（本次新增，独立运行，非 pytest 收集） |
| tree_sitter | **未装**（RepoMap 真实构建走 fallback；测试用 `FakeRepoMap` 注入候选） |
| pylint / radon | **未装**（真 StaticAnalyzer 子进程静默 fallback；集成脚本用 `RecordingStaticAnalyzer` 注入） |
| OpenAI API Key | 未设置（走 `FakeLLMProvider`） |
| SEMANTIC_VALIDATOR_BACKEND | `stub`（默认值，不加载 sentence-transformers） |

**mock 边界矩阵**（遵循原 prompt「mock IO boundaries + 真 Planner pipeline」原则）：

| 组件 | 真/Mock | 说明 |
|---|---|---|
| `Planner` | **真** | `app.orchestrator.planner.Planner` |
| `GuardrailValidator` + RegexValidator + SemanticValidator | **真** | `app.guardrail.*` |
| `Reporter` + `_build_recommendations` + `_build_html_report` | **真** | `app.agents.reporter.Reporter` |
| `EmergencyReporter` | **真** | `app.agents.emergency_reporter.EmergencyReporter` |
| `ConflictResolver` | **真**（llm_provider=None → static fallback 路径） | `app.orchestrator.conflict_resolver.ConflictResolver` |
| `TimeoutGuard` | **真**（`:memory:` SQLite） | `app.orchestrator.timeout_guard.TimeoutGuard` |
| `InputGuardrail` | **真**（BehaviorInferer 内部真调用） | `app.services.input_sanitizer.InputGuardrail` |
| `ProgressBus` / WebSocket | **真** | `app.api.progress_bus.ProgressBus` + `routes.ws_progress` |
| FastAPI `/api/analyze` / `/api/report/{id}` / `/ws/progress/{id}` | **真** | `app.api.routes` |
| `BehaviorInferer.infer` 内部流程 | **真**（通过 `RecordingBehaviorInferer` thin wrapper 调用真 inner 实例） | `app.agents.behavior_inferer.BehaviorInferer` |
| `LLMProvider` | **Mock** (`FakeLLMProvider`) | 返回 canned JSON / override 可注入幻觉 |
| `LLMCache` | **Mock** (`FakeCache` in-memory dict) | 保留 get/set 异步接口与命中计数 |
| `RepoMap` | **Mock** (`FakeRepoMap` 返回 3 候选 / `FakeEmptyRepoMap` 返回空) | 绕过 tree_sitter 依赖 |
| `StaticAnalyzer` | **Mock** (`RecordingStaticAnalyzer`) | 返回合法 StaticResult，注入可控 delay |
| `CommunityAssessor` | **Mock** (`RecordingCommunityAssessor`) | 返回合法 CommunityResult 或按需抛异常 |
| `RepoCloner` | **Mock** (`PathThroughRepoCloner`) | 任何 source/path 直接返回 `tiny_repo` 本地路径 |

---

## 二、第 1 阶段 pytest 全量回归

### 2.1 执行

```bash
$ cd repo-insight/backend && python -m pytest -q --ignore=tests/fixtures
........................................................................ [ 47%]
........................................................................ [ 95%]
.......                                                                  [100%]
151 passed in 2.36s
```

### 2.2 与 v3 对比

| 项 | v3 基线 | v4 本次 | 变化 |
|---|---|---|---|
| 总测试数 | 94 | **151** | +57 |
| Pass | 94 | **151** | +57 |
| Fail / Skip / Error | 0 / 0 / 0 | 0 / 0 / 0 | 无变化 |
| 运行时 | 2.16s | 2.36s | +0.2s |

### 2.3 新增测试文件（相对 v3）

基于 v3 报告中列出的 16 个测试文件与当前 `backend/tests` 目录比对，本轮新增或扩展：

| 新增/扩展文件 | 对应阶段4 能力 |
|---|---|
| `test_input_guardrail.py` | **P0-2** Input Guardrail（secrets + prompt injection） |
| `test_emergency_reporter.py` | **P0-3** Emergency Reporter 降级输出 |
| `test_conflict_resolver_model_routing.py` | **P0-4** 判官模型路由 + confidence escalation |
| `test_repo_map.py` | **P0-5** Tree-sitter RepoMap 候选模块 |
| `test_prompt_caching.py` | 阶段4 LLM 成本治理 |
| `test_reporter_self_check.py` | 阶段4 Reporter self-check warnings 通道 |
| `test_schemas_report_json.py` | P0 契约扩展（多个新字段） |

这些新增测试文件的存在与全部通过，直接证实阶段4 的 P0-2/P0-3/P0-4/P0-5 功能已落地。

---

## 三、第 2 阶段 静态契约一致性校验

### 3.1 `GuardrailTelemetry` 前后端对齐

读取 `backend/app/models/api_schemas.py:12-33` 与 `frontend/src/types/contracts.ts:80-102`：

| 字段 | 后端 Pydantic | 前端 TS interface | 一致性 |
|---|---|---|---|
| `regex_blocked: list[GuardrailRegexBlock]` | 默认 `[]` | `GuardrailRegexBlock[]` | **PASS** |
| `semantic_filtered: list[GuardrailSemanticFilter]` | 默认 `[]` | `GuardrailSemanticFilter[]` | **PASS** |
| `regenerate_count: int` | 默认 0 | `number` | **PASS** |
| `fallback_triggered: bool` | 默认 False | `boolean` | **PASS** |
| `self_check_warnings: list[str]` | 默认 `[]` | `string[]` | **PASS（P0 新字段）** |
| `emergency_mode: bool` | 默认 False | `boolean` | **PASS（P0-3 新字段）** |
| `emergency_reason: str \| None` | 默认 None | `string \| null` | **PASS（P0-3 新字段）** |
| `input_secrets_redacted: int` | 默认 0 | `number?`（optional） | **PASS（P0-2 新字段，前端可选，非阻塞漂移）** |
| `input_injections_blocked: int` | 默认 0 | `number?`（optional） | **PASS（P0-2 新字段，同上）** |

**非阻塞漂移**：`input_secrets_redacted` / `input_injections_blocked` 前端标记为 `?`（optional），后端为 required with default。前端宽松，兼容后端输出，反向新客户端若省略字段也可被后端 Pydantic 默认值填充。v3 的 `community` 可选性漂移仍然存在（v3 §6.1 列为非阻塞，阶段4 未修复）。

### 3.2 `ConflictResolution` 前后端对齐

读取 `backend/app/models/agent_schemas.py:48-57` 与 `frontend/src/types/contracts.ts:49-57`：

| 字段 | 后端 | 前端 | 一致性 |
|---|---|---|---|
| `module` | `str` | `string` | **PASS** |
| `static_view` | `str` | `string` | **PASS** |
| `behavior_view` | `str` | `string` | **PASS** |
| `final_recommendation` | `str` | `string` | **PASS** |
| `judge_model` | `str`, default `"gpt-4o-mini"` | `string?`（optional） | **PASS（P0-4 新字段）** |
| `escalated` | `bool`, default False | `boolean?`（optional） | **PASS（P0-4 新字段）** |
| `confidence` | `float [0,1]`, default 0.5 | `number?`（optional） | **PASS（P0-4 新字段）** |

### 3.3 `ReportJsonResponse` 无漂移

| 顶层字段 | 后端 | 前端 | 一致性 |
|---|---|---|---|
| `job_id` / `status` / `completed_at` / `total_pipeline_ms` | 核心字段 | 对齐 | **PASS** |
| `recommendations` / `conflicts_resolved` | 数组类型 | 对齐 | **PASS** |
| `community` | required `CommunityMetrics` | `community?` optional | **Trivial 漂移**（v3 已记录，未修复） |
| `html_report` / `file_heatmap` / `guardrail_telemetry` | nullable | nullable | **PASS** |

**结论**：契约对齐整体 **PASS**，核心字段集与 P0-2/P0-3/P0-4 所有新增字段前后端同步落地。v3 两个 trivial 漂移（community 可选性、LineRisk.metric 前端独有）保持现状，非阻塞。

---

## 四、第 3 阶段 端到端模拟集成 — 9 项必做验证

### 4.1 执行命令

```bash
$ cd repo-insight/backend && PYTHONPATH=. python tests/e2e_stage4_integration.py
```

### 4.2 9 项 PASS/FAIL 汇总表

| # | 验证项 | 状态 | 证据 |
|---|---|---|---|
| **V1** | 端到端（POST /api/analyze → Planner pipeline → WebSocket → GET /api/report/{id}?format=json） | **PASS** | POST → 202 + `ws_url=/ws/progress/<uuid>`；Planner 跑完真 pipeline；WebSocket 收到 5 个事件（4 agent_status + 1 completed）；Report JSON 字段集齐（`job_id/status=completed/completed_at/total_pipeline_ms/recommendations/conflicts_resolved/community/guardrail_telemetry`） |
| **V2** | 120s SLA（mock 环境断言 `total_pipeline_ms < 10000`） | **PASS** | `total_pipeline_ms=61` < 10000（mock 路径无真 LLM 延迟，远低于 10s 门槛） |
| **V3** | 并发度（`max / sum < 0.7`） | **PASS** | per-agent delays `[static=150, community=120, behavior=180]`ms；实测 `wall=188ms` < `sum=450ms`；`max/sum = 180/450 = 0.400` < 0.7，且 wall≈max，证实 `asyncio.gather` 真并行 |
| **V4** | 缓存命中（同 repo_path 二次跑 LLM 调用数不增） | **PASS** | Run 1：`llm_calls=1, cache_hits=0`；Run 2：`llm_delta=0, cache_hits_delta=+1`。CacheKey 三维（repo_path/file_contents_hash/prompt_version+model+temp）稳定命中 |
| **V5** | Input Guardrail（`sk-proj-*` secret 被识别/脱敏） | **PASS (with gap)** | poisoned README 含 `sk-proj-` + 43×A；`BehaviorInferer.last_input_secrets_redacted=1`；`InputGuardrail().scan()` 返回 `scan.secrets[]` 长度=1；**但** Planner 未把 `BI.last_input_secrets_redacted` 折叠进 `GuardrailTelemetry.input_secrets_redacted`（值为 0）。核心拦截能力已验证，telemetry 折叠是独立行为 gap（见 §七） |
| **V6** | Emergency Reporter（`behavior_inferer` 抛 RuntimeError → 200 + `emergency_mode=True`） | **PASS** | Planner 捕获异常后构造 `PartialReporterInput` → `EmergencyReporter.render()`；HTTP 200；`guardrail_telemetry.emergency_mode=True`；`guardrail_telemetry.emergency_reason="behavior_inferer_failed"` |
| **V7** | Tree-sitter RepoMap（候选注入 + BI 输出 `from_repo_map=True`） | **PASS** | `FakeRepoMap` 返回 3 候选 `[analyzer.py, parser.py, router.py]`；直接调用真 `BehaviorInferer.infer()` 后 `result.inference_evidence` 有 2 条 `core_module::<path>::from_repo_map == "True"`（core_modules 命中率 2/2） |
| **V8** | 幻觉 regex 拦截（LLM 输出含 `"下一代"` → `regex_blocked` 非空） | **PASS** | canned LLM 注入 `core_modules[0].role = "下一代主调度器，2030年将发布"`；Planner 把 `str(behavior_raw.core_modules)` 喂给 Guardrail；`regex_blocked` count=2，rules=`['future_tense', 'future_tense']`（`next_generation` 规则归类为 future_tense 组） |
| **V9** | Planner 分支（CA TimeoutError 降级 / CA CancelledError 重抛） | **PASS** | (a) `community_assessor` 抛 `TimeoutError` → `report.community.is_degraded=True`；(b) `_handle_community(asyncio.CancelledError())` 被正确重抛（不降级），符合 PATCH-PLAN 2.4 的互斥语义 |

**总计**：**9/9 PASS**（含 V5 附带 1 个行为 gap，不构成 FAIL）

### 4.3 V5 行为 gap 详情（Planner ↔ Telemetry 折叠缺失）

**观察**：
- `BehaviorInferer._build_prompt` 正确调用 `InputGuardrail.scan()` 并累加计数到 `self.last_input_secrets_redacted / last_input_injections_blocked`（源码 `backend/app/agents/behavior_inferer.py:372-389`）。
- `Planner.run_pipeline` 在 guardrail 调用后构造 `ReportJsonResponse` 时，**未读取** `behavior_inferer.last_input_secrets_redacted` 并写入 `guardrail_telemetry.input_secrets_redacted`。telemetry 里这两个字段保持默认 0。
- `api_schemas.py:24-33` 的 `GuardrailTelemetry` 已正确声明 `input_secrets_redacted` 和 `input_injections_blocked` 字段。

**影响**：
- 核心安全能力正常（secret 在进入 LLM prompt 前被 `[REDACTED:openai_key]` 替换）。
- 但最终报告里的 telemetry 不反映 input-side 拦截，前端 UI 若基于 `telemetry.input_secrets_redacted > 0` 来显示「输入已脱敏 N 条」徽章，则该徽章永不触发。

**归类**：**Minor**（非阻塞，安全能力未失效，仅 observability 透传链路未闭环）。建议阶段4.5 或阶段5 初补 2 行代码：在 Planner guardrail 调用后 `telemetry.input_secrets_redacted = self.behavior_inferer.last_input_secrets_redacted`。

---

## 五、第 4 阶段 非功能指标

| 指标 | v3 基线 | v4 实测 | 门槛 | 达标 |
|---|---|---|---|---|
| `total_pipeline_ms` (mock) | n/a（真 clone 未执行） | **61 ms** | < 10000 | **PASS** |
| `gather_wall_ms` (controlled 150/120/180 delays) | n/a | **188 ms** | < 450 (sum) | **PASS** |
| `max/sum ratio` | n/a | **0.400** | < 0.7 | **PASS** |
| `cache_hit_rate` (second run same repo) | n/a | **100%** (1/1 hit) | > 0% 增量 | **PASS** |
| LLM 调用数 (run 2 delta) | n/a | **0** | == 0 | **PASS** |

**并发度结论**：`max/sum = 0.400` 远低于阈值 0.7，`wall/max = 188/180 = 1.04`，调度开销仅 4%，证实 Planner 的 `asyncio.gather` 真实并行且无意外串行化。

---

## 六、阶段4 评分

### 6.1 评分维度调整说明

v3 满分 16 分，新增 P0-2 / P0-3 / P0-5（P0-4 在 ConflictResolution 字段对齐中已覆盖），满分变为 **19 分**。

| 维度 | 满分 | v3 评分 | v4 评分 | 说明 |
|---|---|---|---|---|
| HTTP API 可用（health/analyze/report） | 2 | 2.0 | 2.0 | V1 POST 202 + GET 200 验证 |
| WebSocket 推送闭环 | 2 | 2.0 | 2.0 | V1 收到 5 个 ws 事件 |
| Pydantic Schema 完整度 | 1 | 1.0 | 1.0 | 新字段全部落地 |
| 前后端契约一致性 | 2 | 2.0 | 2.0 | GuardrailTelemetry / ConflictResolution 前后端同步 |
| 前端 TS 编译 | 1 | 1.0 | 1.0 | v2 已验证，v4 未触碰 |
| Docker/启动脚本 | 1 | 0.7 | 0.7 | 未再测 |
| 输入校验稳健度 | 1 | 1.0 | 1.0 | 路由 422 + GITHUB_URL_RE 正常 |
| CI 门禁与 DAG 守卫 | 1 | 1.0 | 1.0 | test_import_boundaries 仍 PASS |
| 运行期异常安全 | 1 | 1.0 | 1.0 | test_planner_py312_cancelled_fallback + V9 双重验证 |
| LLM Provider + Guardrail 双层 | 1 | 1.0 | 1.0 | test_guardrail + test_llm_provider 继续 PASS |
| 三采集 Agent 并行实施 | 1 | 1.0 | 1.0 | V3 并行度 0.400 |
| Planner + ConflictResolver | 1 | 1.0 | 1.0 | test_conflict_resolver_model_routing + V9 |
| Reporter + guardrail_telemetry 透传 | 1 | 1.0 | 1.0 | test_reporter_self_check + V1 字段集 |
| `/metrics` 三维指标 | 1 | 1.0 | 1.0 | v3 已验 Prometheus 格式 |
| **阶段4 新维度** |||||
| **P0-2 Input Guardrail**（secrets + injection） | 1 (新增) | — | **0.8** | V5 核心能力 PASS，但 Planner→Telemetry 折叠 gap 扣 0.2 |
| **P0-3 Emergency Reporter** | 1 (新增) | — | **1.0** | V6 HTTP 200 + emergency_mode=True 全路径 PASS |
| **P0-4 Judge Model Routing** | 1 (新增) | — | **1.0** | ConflictResolution 新字段前后端对齐；test_conflict_resolver_model_routing PASS |
| **P0-5 Tree-sitter RepoMap** | 1 (新增) | — | **0.9** | V7 候选命中率 2/2 PASS；本地环境 tree-sitter 未装走 fallback，仅通过 mock 间接验证真实 tree-sitter 路径，扣 0.1 |

**总分 v4：18.7 / 19**（v3 基线 15.7/16 的折合标准化分为 15.7/16 × 19/16 ≈ 18.65；v4 能力增长零掉分，仅两个新维度各扣 0.1/0.2 记录可改进项）

---

## 七、未执行项及原因

| 项目 | 原因 | 归属 |
|---|---|---|
| **真实 `git clone` + 真 OpenAI API 120s 端到端** | OPENAI_API_KEY 未设置，且本地环境受限无法保证网络到 github.com 可用；原 prompt 明确允许走 mock 路径 | 阶段5 上线前做一次真实冒烟 |
| **lint-imports 静态层** | `importlinter` 包未安装（v3 同因） | CI 门禁 C 仍应由 GitHub Actions 承担 |
| **真 tree-sitter RepoMap 构建（非 mock）** | `tree_sitter` + `tree_sitter_python` 未装；V7 走 `FakeRepoMap` 注入候选以验证 BehaviorInferer 对候选的消费路径 | 阶段4 CI 补 `tree_sitter` 依赖后可去除 fake，或保留 fallback 测试作 safety net |
| **真 pylint + radon 子进程** | 两包未装；`_run_subprocess` 捕获 FileNotFoundError 后返回空 dict，不抛异常，因此真 StaticAnalyzer 在该环境返回合法但空的 StaticResult；V1-V9 全部使用 `RecordingStaticAnalyzer` 注入可控结果 | CI 安装后用 v3 test_static_analyzer 9/9 作真实覆盖 |
| **sentence_transformers SemanticValidator** | `SEMANTIC_VALIDATOR_BACKEND=stub`（默认），V8 只验证 regex 层；semantic 层 stub 模式下直接返回 `[]` | 生产环境启动时切 `SEMANTIC_VALIDATOR_BACKEND=sentence_transformers` |
| **前端 `tsc -b` + `vitest run`** | 本轮聚焦后端集成；v3 已验证前端编译；阶段4 前端新增字段全部 optional，无破坏性变更 | 阶段5 发布前端时复测 |
| **GitHub issue API 真实拉取** | 无 GITHUB_TOKEN；mock CommunityAssessor 覆盖 | 与真实 github clone 合并在阶段5 真实冒烟做 |

---

## 八、阶段5 准入建议 — **YES**

### 8.1 硬门禁对照

- [x] **pytest 151/151 PASS**（v3 94 → v4 151，新增 57 测试全绿）
- [x] **架构门禁**（运行期 `test_behavior_inferer_does_not_pull_guardrail` 仍 PASS；lint-imports 静态层依赖 CI，本地环境限制同 v3）
- [x] **契约对齐**（GuardrailTelemetry 5 个 P0 新字段 + ConflictResolution 3 个 P0-4 字段前后端双向落地）
- [x] **9 项必做集成验证 PASS**（含 V5 附带 1 个可改进的行为 gap）
- [x] **非功能指标达标**（SLA 61ms << 10s；并发度 0.400 << 0.7；cache delta=0 LLM 调用）
- [x] **P0-2/P0-3/P0-4/P0-5 功能可观测**（V5/V6/契约 3.2/V7 一一对应）

### 8.2 阻塞项

**无**。V5 的 Planner→Telemetry 折叠 gap 归类 Minor，不阻塞上线：
1. 安全核心能力（secrets 脱敏）在 BehaviorInferer 层面已正确生效，进入 LLM prompt 的文本已被 `[REDACTED:...]` 替换。
2. 仅 UI 层面的 observability 面板无法显示"input 已脱敏 N 条"的证据，但审计日志仍能通过 logger 追溯。

### 8.3 建议

**可进入阶段5**，理由：

1. **P0-2/P0-3/P0-4/P0-5 能力齐全**：4 项阶段4 核心增量都有独立测试文件 + 9 项集成验证双重覆盖，零阻塞。
2. **非功能指标清晰可观测**：`/metrics` 三维指标 + 本次集成脚本收集的 wall/sum/ratio/cache 指标可作为阶段5 CI 基线，防漂移。
3. **契约稳定可演化**：新字段均为 optional 或有 default，前端兼容层无破坏性变更。
4. **降级路径全通**：V6 Emergency Reporter + V9 Community 降级 + V9 CancelledError 重抛三路互斥语义正确。
5. **唯一 Minor gap 有明确修复方案**（2 行代码），可放入阶段5 首个 sprint 的 housekeeping 里。

**建议阶段5 首个动作**：
1. 修复 V5 的 Planner→Telemetry 折叠 gap（`telemetry.input_secrets_redacted = self.behavior_inferer.last_input_secrets_redacted`，同 `input_injections_blocked`）。
2. 在 CI 里安装 `tree-sitter` + `tree-sitter-python` + `pylint` + `radon`，把本次通过 Mock 绕过的模块切回真实调用。
3. 执行一次 `OPENAI_API_KEY` 真实 120s 端到端冒烟（目标仓库 `https://github.com/CronusL-1141/AI-company`，STAGE3-PLAN M3 指定），作为阶段5 上线前最后一道闸门。

---

## 九、发现的新问题清单

| ID | 严重程度 | 描述 | 建议归属 |
|---|---|---|---|
| **BUG-V4-001** | Minor | `Planner.run_pipeline` 未将 `BehaviorInferer.last_input_secrets_redacted` / `last_input_injections_blocked` 折叠进 `GuardrailTelemetry.input_secrets_redacted` / `input_injections_blocked`，导致报告顶层 telemetry 面板无法反映 input-side 拦截次数，尽管 BehaviorInferer 本身正确完成了脱敏。复现方式见 V5 证据：构造含 `sk-proj-` 的 README，pipeline 跑完后 `report.guardrail_telemetry.input_secrets_redacted == 0` 但 `behavior_inferer.last_input_secrets_redacted == 1`。 | 阶段5 首个 sprint housekeeping，2 行代码修复 |
| **Carry-over-001** | Trivial | `ReportJsonResponse.community` 前端标记为可选、后端为必需（v3 §6.1 已记录，v4 未修复）。 | 阶段5 前端对齐时顺带改为必需 |
| **Carry-over-002** | Trivial | `LineRisk.metric?` 前端独有可选字段，后端无对应写入点（v3 §6.1 已记录）。 | 阶段5 前端清理或后端补字段（二选一） |
| **Carry-over-003** | Trivial | `pyproject.toml` 缺 `norecursedirs = ["tests/fixtures"]`，`tests/fixtures/tiny_repo/tests/test_simple.py` 在默认收集时会 `ModuleNotFoundError: No module named 'simple'`，需用 `--ignore=tests/fixtures` 绕过（v3 §1.1 已记录，v4 仍需绕过）。 | 5 分钟级修复，合并进阶段5 首个 PR |

---

## 十、执行环境清理

- 本次没有启动任何常驻后端进程（TestClient 内联运行，`asyncio.run` 驱动 Planner 后自动退出事件循环），**无需 taskkill**
- `PathThroughRepoCloner.cleanup` 为 no-op（local source 跳过），**无临时目录残留**
- V5 创建的 `tests/fixtures/_tiny_repo_poisoned` 在测试函数末尾已通过 `shutil.rmtree(tmp_root, ignore_errors=True)` **正确删除**
- V1 的 `_job_results` 通过每次 `build_app()` 开头的 `_job_results.clear()` **隔离**
- **未修改任何后端/前端源代码**（仅新增 `backend/tests/e2e_stage4_integration.py` 一个独立运行脚本，不被 pytest 收集）
- **未执行 git 操作**

---

## 十一、关键发现汇总（给 Leader）

1. **pytest 151/151 全绿**，相比 v3 基线 94 增长 +57 测试，新增文件直接对应 P0-2/P0-3/P0-4/P0-5 四项阶段4 能力。
2. **9/9 集成验证 PASS**，端到端真 Planner pipeline 能按 `POST/WS/GET` 闭环跑完并序列化合法 `ReportJsonResponse`。
3. **阶段4 P0-2 Input Guardrail 核心能力已落地但存在 Minor gap**：BehaviorInferer 层的 InputGuardrail 扫描+脱敏工作正常，但 Planner 没把拦截次数折叠进顶层 telemetry 面板。非阻塞，2 行代码可修复。
4. **并发度指标 0.400 << 0.7**，`asyncio.gather` 真实并行，调度开销仅 4%。
5. **缓存命中率 100%**，同 repo 二次 Planner 跑 LLM 调用数零增长，CacheKey 三维（文件哈希 + prompt 版本 + 模型+温度）工作正确。
6. **Emergency Reporter + CancelledError/TimeoutError 降级互斥** 三路全部验证通过，阶段3 PATCH-PLAN 2.4 语义在阶段4 无回归。
7. **契约零核心漂移**：`GuardrailTelemetry` 5 个 P0 新字段 + `ConflictResolution` 3 个 P0-4 字段前后端双向对齐；仅 v3 两个 trivial 漂移延续未处理。
8. **阶段4 评分 18.7 / 19**，对比 v3 15.7/16 标准化值，能力增长零掉分，仅新维度各扣 0.1/0.2 记录 V5 gap 和 tree-sitter 本地环境限制。
9. **可进入阶段5**：硬门禁全部通过，无阻塞项；建议阶段5 首 sprint 修 V5 gap、装 tree-sitter/pylint/radon、跑一次真实 OpenAI+github clone 冒烟。

---

## 附录 A — 集成脚本清单

- **新增文件**：`backend/tests/e2e_stage4_integration.py`（约 810 行）
- **调用方式**：`cd repo-insight/backend && PYTHONPATH=. python tests/e2e_stage4_integration.py`
- **依赖**：仅 backend 项目内现有依赖（FastAPI / httpx / pytest-asyncio / pydantic v2），无新增三方依赖
- **副作用**：测试期间创建/删除 `backend/tests/fixtures/_tiny_repo_poisoned` 临时目录（V5），退出前自动清理
- **pytest 收集**：文件名不以 `test_` 开头，pytest 默认不会收集，作为独立运行脚本存在；后续可根据 Leader 决定是否纳入 pytest 或迁至专门的集成测试目录

## 附录 B — 集成脚本输出原文

```
================================================================================
Stage 4 Integration Harness — 2026-04-14T12:47:44.169423+00:00
================================================================================
[PASS] V1: POST->202 ws_url=/ws/progress/f4a5d817-d8b1-411 pipeline->report.status=completed ws_contract_events=5 drain_events=9
[PASS] V2: total_pipeline_ms=61 < 10000 (mock path, no real LLM)
[PASS] V3: wall=188ms < sum=450ms; max/sum=0.400 (<0.7)
[PASS] V4: run1 llm=1 hits=0; run2 llm_delta=0 hits_delta=1
[PASS] V5: BI counter=1 scanner.secrets=1 telemetry_field=0 (BI counter OK, but Planner telemetry does not fold BI.last_input_secrets_redacted into GuardrailTelemetry — behaviour gap)
[PASS] V6: HTTP 200 emergency_mode=True reason=behavior_inferer_failed
[PASS] V7: core_modules=2 from_repo_map_True_count=2
[PASS] V8: regex_blocked count=2 rules=['future_tense', 'future_tense']
[PASS] V9: community.is_degraded=True CancelledError re-raised=True

================================================================================
SUMMARY
================================================================================
PASS: 9  FAIL: 0  TOTAL: 9
```
