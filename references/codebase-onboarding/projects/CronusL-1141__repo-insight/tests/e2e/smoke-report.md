# RepoInsight 阶段2骨架冒烟测试报告

- **任务 ID**: e2c8f140-c21e-45bb-b9ed-c36565dd2059
- **执行人**: qa-engineer
- **执行日期**: 2026-04-13
- **环境**: Windows 11 Pro / PowerShell 7 (经 git-bash 调用) / Python 3.12 (system) / Node v22.18.0 / npm 11.5.2
- **被测范围**: backend 骨架 + frontend 骨架 + 静态契约一致性
- **结论**: **PASS WITH ISSUES** — 最小闭环（HTTP + WebSocket + TypeScript 编译）可走通；但发现 1 个 CRITICAL 契约错位、3 个 MAJOR 缺陷与若干 MINOR 缺陷

---

## 一、阶段1：静态契约一致性检查

### 1.1 字段对齐矩阵 — `AnalyzeRequest` / `AnalyzeResponse`

| 字段 | backend (Pydantic) | frontend (TS) | 一致性 |
|---|---|---|---|
| AnalyzeRequest.source | `Literal["local","github"]` | `'local'\|'github'` | PASS |
| AnalyzeRequest.path | `str` | `string` | PASS |
| AnalyzeResponse.job_id | `str` | `string` | PASS |
| AnalyzeResponse.status | `Literal["queued"]` | `'queued'` | PASS |
| AnalyzeResponse.created_at | `datetime` (ISO8601 序列化) | `string` | PASS |
| AnalyzeResponse.ws_url | `str` | `string` | PASS |

实测请求/响应（来自 `POST http://127.0.0.1:8765/api/analyze`）：

```json
// request
{"source":"github","path":"https://github.com/test/repo"}
// response 202
{"job_id":"4f060d90-d812-47ac-9bb8-6a89388546f6","status":"queued","created_at":"2026-04-13T05:17:04.800507Z","ws_url":"/ws/progress/4f060d90-d812-47ac-9bb8-6a89388546f6"}
```

### 1.2 字段对齐矩阵 — `ReportResult` (backend) vs `ReportJsonResponse` (frontend)

| frontend 字段 | backend 是否存在 | 一致性 |
|---|---|---|
| job_id | yes | PASS |
| status: 'completed' | **缺失** | **FAIL** — backend ReportResult 没有 status 字段 |
| completed_at: string | **缺失** | **FAIL** — backend 无该字段 |
| total_pipeline_ms | yes | PASS |
| recommendations[] | yes (但 priority 类型不一致) | **FAIL** — 见 1.3 |
| conflicts_resolved[] | yes | PASS（结构一致） |
| community: CommunityMetrics | **缺失** | **FAIL** — backend ReportResult 不嵌套 CommunityResult |
| html_report?: string | yes (required, frontend optional) | MINOR — required/optional 不一致 |
| file_heatmap? | **缺失** | **FAIL** — backend Reporter 输出无 file_heatmap，热力图数据在 StaticResult 但未透传 |

```python
# backend/app/models/agent_schemas.py:182-196
class ReportResult(BaseModel):
    job_id: str
    html_report: str            # required
    recommendations: list[Recommendation]
    conflicts_resolved: list[ConflictResolution]
    duration_ms: int
    total_pipeline_ms: int
    # 没有 status / completed_at / community / file_heatmap
```

```ts
// frontend/src/types/contracts.ts:75-85
export interface ReportJsonResponse {
  job_id: string;
  status: 'completed';            // backend 没有
  completed_at: string;            // backend 没有
  total_pipeline_ms: number;
  recommendations: Recommendation[];
  conflicts_resolved: ConflictResolution[];
  community: CommunityMetrics;     // backend ReportResult 没有，要从 CommunityResult 聚合
  html_report?: string;
  file_heatmap?: FileHeatmap;      // backend ReportResult 没有
}
```

**影响**：`frontend/src/components/ReportViewer.tsx:73` 直接读 `report.completed_at`，`:78-82` 直接读 `report.file_heatmap`，`:121` 读 `c.module/static_view/behavior_view/final_recommendation`。当 backend 真正接入 `/api/report/{job_id}?format=json` 时返回的 ReportResult 形状会让 ReportViewer 渲染出 `undefined` 或在 file_heatmap 上崩溃。

### 1.3 字段对齐矩阵 — `Recommendation` / `LineRisk` / 命名空间

| 字段路径 | backend | frontend | 一致性 |
|---|---|---|---|
| Recommendation.title | `str` | `string` | PASS |
| Recommendation.detail | `str` | `string` | PASS |
| Recommendation.affected_files | `list[str]` | `string[]` | PASS |
| Recommendation.priority | `RiskLevel` (`low/medium/high/critical`) | `Priority` (`high/medium/low`) | **FAIL** — backend 多 'critical' |
| LineRisk.line | `int (ge=1)` | `number` | PASS |
| LineRisk severity 字段 | `risk_level: RiskLevel` | `severity: Severity` | **FAIL** — 字段名 + 类型联合一致但键名不同 |
| LineRisk.reason | `str` | `string` | PASS |
| LineRisk.metric | (无) | `'complexity'\|'coverage'\|'maintainability'?` | MINOR — frontend 多一个可选字段 |
| FunctionRisk.risk_level | `RiskLevel` | (无对应 TS 类型) | INFO — frontend 未消费 |

```python
# backend/app/models/agent_schemas.py:35-46
class LineRisk(BaseModel):
    line: int = Field(ge=1)
    risk_level: RiskLevel       # 字段名是 risk_level
    reason: str

class Recommendation(BaseModel):
    title: str
    detail: str
    affected_files: list[str] = Field(default_factory=list)
    priority: RiskLevel = RiskLevel.MEDIUM   # 'low/medium/high/critical'
```

```ts
// frontend/src/types/contracts.ts:33-47
export interface LineRisk {
  line: number;
  severity: Severity;          // 字段名是 severity
  reason: string;
  metric?: 'complexity' | 'coverage' | 'maintainability';
}

export interface Recommendation {
  title: string;
  detail: string;
  affected_files: string[];
  priority: Priority;          // 'high/medium/low' — 缺 'critical'
}
```

### 1.4 WebSocket 事件契约

| 事件类型 | backend 发送 | frontend 处理 | 一致性 |
|---|---|---|---|
| agent_status (8 个) | `{type, job_id, timestamp, agent, status, progress}` 平铺 | `WsAgentStatusEvent` 平铺同形 | PASS |
| completed (1 个) | `{type, job_id, timestamp, report_url, total_duration_ms}` | `WsCompletedEvent` 同形 | PASS |
| agent_completed | 未发送 | 已实现处理 case | INFO — fake 阶段未触发 |
| conflict_detected | 未发送 | 已实现处理 case | INFO |
| degraded | 未发送 | 已实现处理 case | INFO |
| failed | 未发送 | 已实现处理 case | INFO |
| error | 未发送 | 已实现处理 case | INFO |

**重要副发现**：`backend/app/models/api_schemas.py:23-27` 定义的 `WSMessage` 结构是 `{type, job_id, timestamp, data: dict}`（嵌套 data），但 `backend/app/api/websocket.py:31-37` 实际推送时把字段平铺写在顶层（`**event`），并不使用 WSMessage 序列化。也即**后端实际推送格式与后端自身的 Pydantic Schema 不一致**——好在前端类型是参考实际推送格式写的，恰好对齐。建议要么删除未使用的 WSMessage，要么改用 WSMessage 序列化（需同步前端类型）。

### 1.5 阶段1结论
- **PASS** ：API 请求/响应签名、所有 WebSocket 事件 type/structure
- **FAIL（CRITICAL）**：ReportResult vs ReportJsonResponse 形状错位（5 个字段不一致）
- **FAIL（MAJOR）**：LineRisk 字段名 risk_level vs severity；Recommendation.priority 取值集不一致
- **FAIL（MINOR）**：WSMessage Pydantic schema 与实际推送格式自相矛盾（虽然不影响当前闭环）

---

## 二、阶段2：实际启动验证

### 2.1 后端启动

**预期路径**：`uv sync` → `uv run uvicorn app.main:app`
**实际执行**：

```bash
$ cd repo-insight/backend && uv sync
× Failed to download `rich==15.0.0`
├─▶ Failed to extract archive: rich-15.0.0-py3-none-any.whl
├─▶ I/O operation failed during extraction
╰─▶ Failed to download distribution due to network timeout
help: rich (v15.0.0) was included because repo-insight-backend depends on
      sentence-transformers (v5.4.0) → transformers (v5.5.3) → typer
      (v0.24.1) → rich
```

`UV_HTTP_TIMEOUT=180 uv sync` 仍因 sentence-transformers 链路（约 2GB 模型/wheel）在受限网络下超时，**未执行：网络延迟+依赖体积**。

**Workaround**：使用系统 Python 3.12 直接启动（已具备 fastapi 0.135.1 / pydantic 2.12.3 / uvicorn 0.41.0）：

```bash
$ python -m uvicorn app.main:app --host 127.0.0.1 --port 8765 --log-level warning
# 启动成功
```

### 2.2 后端 HTTP 端点验证

| 用例 | 命令 | 期望 | 实际 | 状态 |
|---|---|---|---|---|
| TC-B01 健康检查 | `GET /api/health` | 200 + status:ok | `200 {"status":"ok","version":"0.1.0","timestamp":"2026-04-13T05:16:51...","dependencies":{"sqlite":"ok","llm_provider":"ok"}}` | PASS |
| TC-B02 提交分析(github) | `POST /api/analyze {"source":"github","path":"https://..."}` | 202 + job_id | `202 {"job_id":"4f060d90-...","status":"queued","created_at":"...","ws_url":"/ws/progress/..."}` | PASS |
| TC-B03 非法 source | `POST /api/analyze {"source":"invalid","path":""}` | 422 | `422 literal_error: Input should be 'local' or 'github'` | PASS |
| TC-B04 缺字段 | `POST /api/analyze {"source":"github"}` | 422 | `422` | PASS |
| TC-B05 非 JSON 体 | `POST /api/analyze 'not-json'` | 422 | `422` | PASS |
| TC-B06 **空 path** | `POST /api/analyze {"source":"local","path":""}` | **400/422 拒绝** | **`202 + job_id`（接受）** | **FAIL → BUG-001** |
| TC-B07 报告 html | `GET /api/report/abc-123` | 200 html | `200` 占位 HTML | PASS（占位） |
| TC-B08 报告 json | `GET /api/report/abc-123?format=json` | 200 json 或 404 | `404 {"error":{"code":"JOB_NOT_FOUND",...}}` | PASS（占位） |
| TC-B09 OpenAPI 文档 | `GET /docs` | 200 | `200` | PASS |

### 2.3 WebSocket 假事件验证

```python
# 测试脚本
async with websockets.connect('ws://127.0.0.1:8765/ws/progress/test-job-001') as ws:
    while True: msgs.append(json.loads(await asyncio.wait_for(ws.recv(), timeout=2.0)))
# 输出：received 9 events
```

收到 9 条事件，全部为合法 JSON，时间戳单调递增，每条间隔 ~500ms，最后一条为 `type:"completed"`。前 8 条为 `type:"agent_status"` 覆盖 4 个 agent 的 running→completed 完整生命周期。**通路 PASS**。

证据片段：

```
{"type": "agent_status", "agent": "static_analyzer",    "status": "running",   "progress": 0,   "job_id": "test-job-001", "timestamp": "2026-04-13T05:17:18.219+00:00"}
{"type": "agent_status", "agent": "behavior_inferer",   "status": "running",   "progress": 0,   "job_id": "test-job-001", "timestamp": "2026-04-13T05:17:18.730+00:00"}
{"type": "agent_status", "agent": "community_assessor", "status": "running",   "progress": 0,   "job_id": "test-job-001", "timestamp": "2026-04-13T05:17:19.243+00:00"}
{"type": "agent_status", "agent": "static_analyzer",    "status": "completed", "progress": 100, ...}
{"type": "agent_status", "agent": "behavior_inferer",   "status": "completed", "progress": 100, ...}
{"type": "agent_status", "agent": "community_assessor", "status": "completed", "progress": 100, ...}
{"type": "agent_status", "agent": "reporter",           "status": "running",   "progress": 0,   ...}
{"type": "agent_status", "agent": "reporter",           "status": "completed", "progress": 100, ...}
{"type": "completed",    "report_url": "/api/report/test-job-001", "total_duration_ms": 4000, ...}
```

### 2.4 前端依赖与编译

```bash
$ cd repo-insight/frontend && npm install --no-audit --no-fund --loglevel=error
added 425 packages in 3m
```

Vite + React + TS 全部依赖安装成功（425 个包，耗时约 3 分钟）。

**TypeScript 类型检查**：

```bash
# 用 src tsconfig 单独检查（不含 vite.config.ts）
$ npx tsc --noEmit -p tsconfig.json
src/test/setup.ts(5,3): error TS2578: Unused '@ts-expect-error' directive.
src/test/setup.ts(8,7): error TS2322: Type 'string' is not assignable to type
                       '`${string}-${string}-${string}-${string}-${string}`'.
```

**结果**：`src/` 下 17 个业务源文件 0 错误，仅 `src/test/setup.ts` 报 2 个错。

```bash
# 完整 build 模式（含 vite.config.ts → tsconfig.node.json）
$ npx tsc -b --noEmit
vite.config.ts(3,18): error TS2307: Cannot find module 'node:path' ...
vite.config.ts(9,25): error TS2304: Cannot find name '__dirname'.
vite.config.ts(39,3): error TS2769: Object literal may only specify known
                     properties, and 'test' does not exist in type
                     'UserConfigExport'.
tsconfig.json(25,18): error TS6310: Referenced project '...tsconfig.node.json'
                     may not disable emit.
```

阶段2前端编译产生 6 个错误（4 类）：见 BUG-002 / BUG-003 / BUG-004。

### 2.5 阶段2结论
- **PASS**：health / analyze（含正/负用例 5 条）/ report html+json / WebSocket 9 事件 / OpenAPI 文档 / src 17 个业务文件类型检查
- **FAIL**：uv sync 受网络阻塞（环境性，非代码 BUG）、空路径未校验（BUG-001）、vite.config.ts 缺类型（BUG-002）、tsconfig.node.json 配置错（BUG-003）、test/setup.ts 报错（BUG-004）

---

## 三、骨架完整性评分

| 维度 | 满分 | 评分 | 说明 |
|---|---|---|---|
| HTTP API 接口可用 | 2 | 2.0 | health/analyze/report 全部启动并可访问 |
| WebSocket 推送闭环 | 2 | 2.0 | 9 事件全部正确推送，时序与结构符合预期 |
| Pydantic Schema 完整度 | 1 | 0.8 | 4 个 Agent 输入输出齐全，但 ReportResult 未对齐前端 |
| 前后端契约一致性 | 2 | 0.5 | 字段名错位、形状错位、取值集错位（CRITICAL） |
| 前端 TS 编译 | 1 | 0.6 | 业务源码通过；vite.config / setup.ts 报错 |
| Docker/启动脚本 | 1 | 0.7 | 已存在 docker-compose / bootstrap / smoke 但未实测 |
| 输入校验稳健度 | 1 | 0.5 | 类型校验有，业务校验缺（空字符串 / source-path 一致性） |

**总分：7.1 / 10** — 骨架最小闭环可走通，但**契约对齐与边界校验存在显著瑕疵**，进入业务实现阶段前应修复。

---

## 四、缺陷清单

### BUG-001 [MAJOR] AnalyzeRequest 未拒绝空 path

- **严重程度**：Major
- **影响范围**：所有调用 `/api/analyze` 的入口
- **复现步骤**：
  ```bash
  curl -X POST http://127.0.0.1:8765/api/analyze \
    -H "Content-Type: application/json" \
    -d '{"source":"local","path":""}'
  ```
- **期望行为**：返回 400/422，提示 path 不能为空
- **实际行为**：返回 202 并生成 job_id `d3c3a089-90b6-45a8-a0ac-7360a0b6525f`
- **代码位置**：`backend/app/models/api_schemas.py:9-13`
- **可能原因**：`path: str` 缺 `Field(min_length=1)`，且未对 `source='github'` 时 path 必须以 `https://github.com/` 开头做语义校验
- **修复定位线索**：
  ```python
  path: str = Field(min_length=1, description="...")
  @field_validator("path")
  @classmethod
  def _check(cls, v, info): ...
  ```

### BUG-002 [MAJOR] vite.config.ts 缺 @types/node，无法通过 tsc -b

- **严重程度**：Major
- **影响范围**：`pnpm/npm run build` 和任何 `tsc -b` 调用，CI 会失败
- **复现步骤**：
  ```bash
  cd repo-insight/frontend && npx tsc -b --noEmit
  ```
- **期望行为**：编译通过
- **实际行为**：3 个错误
  ```
  vite.config.ts(3,18): error TS2307: Cannot find module 'node:path'
  vite.config.ts(9,25): error TS2304: Cannot find name '__dirname'.
  vite.config.ts(39,3): error TS2769: 'test' does not exist in 'UserConfigExport'
  ```
- **代码位置**：`frontend/vite.config.ts:1-44` + `frontend/tsconfig.node.json` + `frontend/package.json:29-46`
- **可能原因**：
  1. devDependencies 缺 `@types/node`
  2. vite.config.ts 在顶层使用 `test` 字段（vitest config），但未通过 `defineConfig` 的 vitest 重载或三斜线引用
- **修复定位线索**：
  ```jsonc
  // package.json devDependencies
  "@types/node": "^22.0.0"
  ```
  ```ts
  // vite.config.ts 顶部加
  /// <reference types="vitest" />
  ```

### BUG-003 [MAJOR] tsconfig.node.json 缺 noEmit，与 tsconfig.json 引用矛盾

- **严重程度**：Major
- **影响范围**：`tsc -b` 项目引用模式
- **复现步骤**：同 BUG-002
- **实际错误**：
  ```
  tsconfig.json(25,18): error TS6310: Referenced project 'tsconfig.node.json'
  may not disable emit.
  ```
- **代码位置**：`frontend/tsconfig.node.json:1-12`
- **可能原因**：`tsconfig.node.json` 设置了 `composite: true` 但既没设 `noEmit: false` 也没设 outDir，TS 6310 要求 referenced project 不能 disableEmit，但 tsconfig.json 又有 `noEmit: true`。需在 tsconfig.node.json 中显式 `"noEmit": false` + `"outDir": "./node_modules/.tmp"`
- **修复定位线索**：阅读 [Vite 官方模板 tsconfig.node.json](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) 的标准写法

### BUG-004 [MAJOR] @testing-library/jest-dom 被 setup.ts 引用但未在 package.json 声明

- **严重程度**：Major（vitest 测试套件无法运行）
- **影响范围**：`pnpm/npm run test`
- **复现步骤**：
  ```bash
  cd repo-insight/frontend && npm test
  ```
- **代码位置**：`frontend/src/test/setup.ts:1` `import '@testing-library/jest-dom/vitest';`
- **package.json devDependencies 实际**：只有 `@testing-library/react` 和 `jsdom`，无 `@testing-library/jest-dom`
- **附带问题**：setup.ts 第 5 行 `@ts-expect-error` 无效；第 8 行返回的 string 不匹配 `randomUUID()` 的模板字面量类型
- **修复定位线索**：
  ```jsonc
  "@testing-library/jest-dom": "^6.5.0"
  ```
  并把 setup.ts 中 `randomUUID` 返回值断言为 `as `${string}-${string}-${string}-${string}-${string}``

### BUG-005 [CRITICAL] ReportJsonResponse 与后端 ReportResult 形状错位

- **严重程度**：Critical
- **影响范围**：阶段3 真实接入 `/api/report/{job_id}?format=json` 时，前端 `useAnalysisJob.ts` → `setReport` → `ReportViewer.tsx` 全链路渲染异常或运行时 undefined
- **触发场景**：当 backend 把 ReportResult 真实序列化返回时
- **缺失字段**：`status`、`completed_at`、`community`（CommunityMetrics）、`file_heatmap`
- **代码位置**：
  - `backend/app/models/agent_schemas.py:182-196` (ReportResult)
  - `frontend/src/types/contracts.ts:75-85` (ReportJsonResponse)
  - `frontend/src/components/ReportViewer.tsx:73,77-82` (直接读取这些字段)
- **预期影响**：
  ```tsx
  // ReportViewer.tsx:73 — 报告时间渲染会显示 "生成时间: undefined"
  生成时间: {report.completed_at}
  // ReportViewer.tsx:77-82 — 热力图永远不会显示
  {report.file_heatmap && <HeatmapChart fileHeatmap={report.file_heatmap} />}
  ```
- **修复方向**：定义独立的 `ReportJsonResponse` Pydantic schema 在 `api_schemas.py`，由 `/api/report/{job_id}?format=json` 端点返回；不直接复用 `ReportResult`

### BUG-006 [MAJOR] LineRisk 字段名 risk_level vs severity 不一致

- **严重程度**：Major（影响 HeatmapChart 渲染热力图）
- **影响范围**：`StaticResult.file_heatmap` → 前端 `FileHeatmap` → `HeatmapChart`
- **代码位置**：
  - backend `agent_schemas.py:35-39`：`LineRisk.risk_level: RiskLevel`
  - frontend `contracts.ts:33-38`：`LineRisk.severity: Severity`
- **触发场景**：阶段3 后端把 StaticResult 中的 file_heatmap 序列化返回时，前端读 `severity` 拿不到值
- **修复方向**：二选一统一字段名（建议前端改为 `risk_level` 与后端对齐）

### BUG-007 [MINOR] Recommendation.priority 取值集不一致

- **严重程度**：Minor
- **影响范围**：当 backend Reporter 输出 priority='critical' 时，frontend `Priority` 类型不接受
- **代码位置**：
  - backend `agent_schemas.py:41-45`：`priority: RiskLevel = RiskLevel.MEDIUM`，可取 `low/medium/high/critical`
  - frontend `contracts.ts:21`：`Priority = 'high' | 'medium' | 'low'`，缺 `critical`
- **修复方向**：frontend 加 `'critical'`，统一为 `Severity` / `RiskLevel`

### BUG-008 [MINOR] 后端定义的 WSMessage Pydantic 模型与实际推送格式不一致

- **严重程度**：Minor（当前未导致问题，仅未来扩展风险）
- **代码位置**：
  - `backend/app/models/api_schemas.py:23-27`：`WSMessage` 定义为 `{type, job_id, timestamp, data: dict}`
  - `backend/app/api/websocket.py:31-37`：实际推送时把 `agent/status/progress/...` 平铺到顶层而非放入 `data`
- **后果**：WSMessage 被定义但从不使用；如果未来某模块按 WSMessage 序列化推送，前端类型会爆
- **修复方向**：删除 WSMessage 或改用它序列化（同步前端类型重构）

### BUG-009 [TRIVIAL] /api/health dependencies 字段为硬编码 "ok"

- **严重程度**：Trivial（骨架阶段可接受）
- **代码位置**：`backend/app/api/health.py:13-19`
- **当前行为**：永远返回 `{"sqlite":"ok","llm_provider":"ok"}`，未实际探测
- **修复方向**：阶段3 应做真实的 `pragma quick_check` + LLM Provider ping

---

## 五、修复优先级建议

| 优先级 | BUG | 理由 |
|---|---|---|
| **P0（进入阶段3前必修）** | BUG-005 | ReportResult/ReportJsonResponse 形状错位，会让真实接入瞬间崩溃；契约错位是后续所有联调的卡口 |
| **P0** | BUG-006 | LineRisk 字段名错位会让热力图永远空，是产品核心交付物之一 |
| **P0** | BUG-002 + BUG-003 + BUG-004 | 三者合在一起会让 `npm run build` 和 `npm run test` 全部失败，CI/CD 必然挂 |
| **P1（业务实装阶段修）** | BUG-001 | 输入校验缺失，会让无效任务进入队列污染审计日志 |
| **P1** | BUG-007 | priority 取值集不一致，Reporter 一旦输出 critical 即前端类型 ban |
| **P2** | BUG-008 | 自相矛盾的 WSMessage 定义，技术债 |
| **P2** | BUG-009 | health 假数据，正式上线前替换 |

**3 条实操修复建议（按依赖顺序）**：

1. **先统一前后端类型源** —— 在 `docs/API-CONTRACT.md` 落定一份"金本位"，然后让 Pydantic 与 TS 类型从该文档双向校验。建议引入 `datamodel-code-generator` 把 OpenAPI 直接生成 TS（消除 BUG-005/006/007 全部起因）。

2. **把 frontend 编译/测试加入 CI 必经门** —— 当前 `tsc -b` 与 `vitest` 都因 BUG-002/003/004 不通；建议立刻补全 `@types/node`、`@testing-library/jest-dom`、修 tsconfig.node.json，让 CI 第一关就能拦截这类问题。

3. **AnalyzeRequest 加业务校验层** —— 用 Pydantic v2 的 `field_validator` 校验：path 非空、`source='github'` 时为合法 GitHub URL、`source='local'` 时为绝对路径且存在。这是 BUG-001 的根治办法。

---

## 六、未执行项与原因

| 项目 | 是否执行 | 原因 |
|---|---|---|
| `uv sync` | 未完整执行 | sentence-transformers/transformers/typer/rich 链路在受限网络下 wheel 下载超时；改用系统 Python 3.12 直接启动 |
| `docker compose up` | 未执行 | 不在本次任务范围（专注前后端最小闭环），且 sentence-transformers 镜像构建会复现同样的网络问题 |
| `scripts/bootstrap.ps1` / `dev.ps1` / `smoke.ps1` | 未执行 | 同上；脚本本身已存在，未实测脚本逻辑 |
| `npm run dev`（前端 vite 启动） | 未执行 | 任务约束第 5 行只要求"只类型检查，不启动"前端 |
| `npm run test`（vitest） | 未执行 | 由 BUG-004 阻塞（缺 jest-dom）；已记录为缺陷而非补救 |
| `pnpm` 执行 | 未执行 | 环境未安装 pnpm，已用 npm 替代；package.json 中无 lockfile，两者等价 |

---

## 七、执行环境清理

- 后端 uvicorn 进程（端口 8765）已通过 `Get-NetTCPConnection -LocalPort 8765 | Stop-Process -Force` 终止，端口剩余 0 个连接
- 未启动任何前端 dev server
- 未修改 backend/frontend/scripts 任何源代码
- 未执行 git 操作

---

## 八、结论

**骨架冒烟测试结论：PASS WITH 9 ISSUES**

最小闭环（FastAPI 启动 → REST + WebSocket → 前端 17 文件 TS 编译）走通；阶段2骨架达到了"可启动可联调"的最低门槛。但**前后端契约对齐存在 1 个 CRITICAL（BUG-005）和 3 个 MAJOR（BUG-002/003/004/006）**，强烈建议在进入阶段3"真实 Agent 业务实装"之前先合一个"契约对齐 + 编译修复"PR，否则联调阶段会被这些问题反复阻塞。
