# API Contract — RepoInsight

**版本**: v1  
**日期**: 2026-04-12  
**后端**: FastAPI + asyncio + WebSocket (Pydantic v2)  
**前端对齐**: `frontend/src/types/api.ts`

---

## 1. 通用约定

| 项 | 值 |
|---|---|
| Base URL | `http://localhost:8000` |
| 内容类型 | `application/json` |
| 字符编码 | UTF-8 |
| 时间戳格式 | ISO 8601，UTC（`2026-04-12T10:00:00Z`） |
| 错误格式 | `{"error": {"code": str, "message": str, "detail": any}}` |
| 版本前缀 | `/api`（当前 v1，无路径版本号；破坏性变更时升级为 `/api/v2`） |

### 标准错误码

| HTTP 状态 | code 字段 | 含义 |
|---|---|---|
| 400 | `INVALID_INPUT` | 请求体校验失败 |
| 404 | `JOB_NOT_FOUND` | job_id 不存在 |
| 409 | `JOB_ALREADY_RUNNING` | 同一 repo 已有进行中任务 |
| 422 | `VALIDATION_ERROR` | Pydantic 校验错误（自动） |
| 500 | `INTERNAL_ERROR` | 未预期服务端错误 |
| 504 | `PIPELINE_TIMEOUT` | 120s 总预算耗尽 |

---

## 2. REST 端点

### 2.1 POST /api/analyze

提交分析任务，立即返回 job_id，分析异步执行。

**Request**

```
POST /api/analyze
Content-Type: application/json
```

```json
{
  "source": "github",
  "path": "https://github.com/CronusL-1141/AI-company"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source` | `"local" \| "github"` | 是 | `local` 时 path 为绝对路径；`github` 时为 HTTPS URL |
| `path` | `string` | 是 | 本地路径或 GitHub 仓库 URL |

**约束**:
- `source=local` 时，后端只读访问该路径，禁止执行目录内任何文件
- `source=github` 时，后端克隆到临时目录，分析完成后清理

**Response 202 Accepted**

```json
{
  "job_id": "a3f8c1d2-4e5b-4f6a-8c9d-0e1f2a3b4c5d",
  "status": "queued",
  "created_at": "2026-04-12T10:00:00Z",
  "ws_url": "/ws/progress/a3f8c1d2-4e5b-4f6a-8c9d-0e1f2a3b4c5d"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `job_id` | `string (UUID4)` | 任务唯一标识 |
| `status` | `"queued"` | 初始状态 |
| `created_at` | `string (ISO 8601)` | 任务创建时间 |
| `ws_url` | `string` | WebSocket 进度推送地址 |

**Response 409 Conflict**

```json
{
  "error": {
    "code": "JOB_ALREADY_RUNNING",
    "message": "A job for this repository is already running",
    "detail": {"existing_job_id": "..."}
  }
}
```

---

### 2.2 GET /api/report/{job_id}

获取已完成任务的 HTML 报告。

**Request**

```
GET /api/report/{job_id}
```

| 参数 | 类型 | 位置 | 说明 |
|---|---|---|---|
| `job_id` | `string (UUID4)` | path | 任务 ID |
| `format` | `"html" \| "json"` | query（可选，默认 `html`） | `json` 返回结构化 ReportResult |

**Response 200 OK — format=html**

```
Content-Type: text/html; charset=utf-8

<!DOCTYPE html>
<html>...完整自包含 HTML，内嵌 ECharts 热力图...</html>
```

**Response 200 OK — format=json**

```json
{
  "job_id": "a3f8c1d2-...",
  "status": "completed",
  "completed_at": "2026-04-12T10:01:45Z",
  "total_pipeline_ms": 87432,
  "recommendations": [
    {
      "title": "Refactor high-complexity function parse_config",
      "detail": "CC=18 exceeds threshold 10. Extract sub-functions.",
      "affected_files": ["config/parser.py"],
      "priority": "high"
    }
  ],
  "conflicts_resolved": [
    {
      "module": "utils",
      "static_view": "CC=15, coverage=42%, pylint=5.2",
      "behavior_view": "Referenced in 3 of 4 usage patterns as entry point",
      "final_recommendation": "Prioritize test coverage increase before refactor; current usage frequency justifies investment."
    }
  ],
  "community": {
    "commits_per_week": 4.2,
    "avg_issue_response_hours": 36.5,
    "unique_contributors": 8,
    "is_degraded": false
  }
}
```

**Response 202 Accepted**（任务仍在进行中）

```json
{
  "job_id": "a3f8c1d2-...",
  "status": "running",
  "progress": {
    "static_analyzer": "completed",
    "behavior_inferer": "running",
    "community_assessor": "completed",
    "reporter": "pending"
  }
}
```

**Response 404 Not Found**

```json
{
  "error": {
    "code": "JOB_NOT_FOUND",
    "message": "Job not found",
    "detail": null
  }
}
```

---

### 2.3 GET /api/health

服务健康检查，供 Docker healthcheck 和负载均衡器使用。

**Request**

```
GET /api/health
```

**Response 200 OK**

```json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": "2026-04-12T10:00:00Z",
  "dependencies": {
    "sqlite": "ok",
    "llm_provider": "ok"
  }
}
```

**Response 503 Service Unavailable**（关键依赖不可用）

```json
{
  "status": "degraded",
  "version": "0.1.0",
  "timestamp": "2026-04-12T10:00:00Z",
  "dependencies": {
    "sqlite": "ok",
    "llm_provider": "error"
  }
}
```

---

## 3. WebSocket 协议

### 连接

```
WS /ws/progress/{job_id}
```

- 服务端在任务各阶段主动推送事件（Server → Client only）
- 客户端无需发送消息；连接建立后保持监听直至收到 `completed` 或 `failed`
- 若 job_id 不存在，服务端立即发送 `{"type": "error", "code": "JOB_NOT_FOUND"}` 并关闭连接

### 消息格式（所有消息共有字段）

```json
{
  "type": "<event_type>",
  "job_id": "<uuid>",
  "timestamp": "<ISO 8601>",
  ...event_specific_fields
}
```

---

### 3.1 事件类型详情

#### agent_status — Agent 运行进度更新

```json
{
  "type": "agent_status",
  "job_id": "a3f8c1d2-...",
  "timestamp": "2026-04-12T10:00:05Z",
  "agent": "static_analyzer",
  "status": "running",
  "progress": 62
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `agent` | `"static_analyzer" \| "behavior_inferer" \| "community_assessor" \| "reporter"` | Agent 标识 |
| `status` | `"pending" \| "running" \| "completed" \| "failed"` | 当前状态 |
| `progress` | `integer [0, 100]` | 百分比进度（Agent 自报） |

推送频率：每个 Agent 至少推送 `status=running`（启动时）和 `status=completed/failed`（结束时），运行中可选推送进度更新。

---

#### agent_completed — Agent 完成

```json
{
  "type": "agent_completed",
  "job_id": "a3f8c1d2-...",
  "timestamp": "2026-04-12T10:00:58Z",
  "agent": "static_analyzer",
  "duration_ms": 52340,
  "summary": "Scanned 47 files, found 3 high-complexity functions"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `agent` | `string` | 完成的 Agent |
| `duration_ms` | `integer` | 该 Agent 实际耗时 |
| `summary` | `string` | 人类可读的简要结果摘要 |

---

#### conflict_detected — 检测到 Static/Behavior 冲突

```json
{
  "type": "conflict_detected",
  "job_id": "a3f8c1d2-...",
  "timestamp": "2026-04-12T10:01:00Z",
  "modules": ["utils", "config/parser"],
  "count": 2
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `modules` | `string[]` | 触发冲突的模块路径列表 |
| `count` | `integer` | 冲突模块数量 |

该事件由 Planner 在 Phase 2（三个分析 Agent 完成后、Reporter 启动前）推送。

---

#### degraded — Agent 降级通知

```json
{
  "type": "degraded",
  "job_id": "a3f8c1d2-...",
  "timestamp": "2026-04-12T10:00:46Z",
  "agent": "community_assessor",
  "reason": "exceeded 45s budget",
  "fallback": "historical_average"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `agent` | `string` | 发生降级的 Agent |
| `reason` | `string` | 降级原因（超时 / 无缓存等） |
| `fallback` | `"cache" \| "historical_average"` | 实际使用的降级数据来源 |

---

#### completed — 分析完成

```json
{
  "type": "completed",
  "job_id": "a3f8c1d2-...",
  "timestamp": "2026-04-12T10:01:47Z",
  "report_url": "/api/report/a3f8c1d2-4e5b-4f6a-8c9d-0e1f2a3b4c5d",
  "total_duration_ms": 107432
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `report_url` | `string` | 可直接 GET 的报告地址 |
| `total_duration_ms` | `integer` | 从任务创建到报告生成的总耗时 |

---

#### failed — 分析失败

```json
{
  "type": "failed",
  "job_id": "a3f8c1d2-...",
  "timestamp": "2026-04-12T10:02:01Z",
  "error_code": "PIPELINE_TIMEOUT",
  "message": "Pipeline exceeded 120s budget"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `error_code` | `string` | 对应 §1 标准错误码 |
| `message` | `string` | 人类可读的错误描述 |

---

### 3.2 典型事件序列

```
Client connects to /ws/progress/{job_id}
    ↓
← {"type": "agent_status", "agent": "static_analyzer",    "status": "running",    "progress": 0}
← {"type": "agent_status", "agent": "behavior_inferer",   "status": "running",    "progress": 0}
← {"type": "agent_status", "agent": "community_assessor", "status": "running",    "progress": 0}
    ↓ (t ≈ 45s, community timeout)
← {"type": "degraded",        "agent": "community_assessor", "reason": "exceeded 45s budget", "fallback": "historical_average"}
← {"type": "agent_completed", "agent": "community_assessor", "duration_ms": 45001}
    ↓ (t ≈ 52s)
← {"type": "agent_completed", "agent": "static_analyzer",    "duration_ms": 52340}
    ↓ (t ≈ 55s)
← {"type": "agent_completed", "agent": "behavior_inferer",   "duration_ms": 55120}
← {"type": "conflict_detected", "modules": ["utils"], "count": 1}
← {"type": "agent_status",   "agent": "reporter", "status": "running", "progress": 0}
← {"type": "agent_status",   "agent": "reporter", "status": "running", "progress": 70}
← {"type": "agent_completed","agent": "reporter",            "duration_ms": 31200}
← {"type": "completed", "report_url": "/api/report/...", "total_duration_ms": 87432}
```

---

## 4. 前端 TypeScript 类型对齐

```typescript
// frontend/src/types/api.ts

export type AgentName =
  | "static_analyzer"
  | "behavior_inferer"
  | "community_assessor"
  | "reporter";

export type AgentStatus = "pending" | "running" | "completed" | "failed";

export type WsEventType =
  | "agent_status"
  | "agent_completed"
  | "conflict_detected"
  | "degraded"
  | "completed"
  | "failed"
  | "error";

export interface WsBaseEvent {
  type: WsEventType;
  job_id: string;
  timestamp: string;
}

export interface WsAgentStatusEvent extends WsBaseEvent {
  type: "agent_status";
  agent: AgentName;
  status: AgentStatus;
  progress: number;
}

export interface WsAgentCompletedEvent extends WsBaseEvent {
  type: "agent_completed";
  agent: AgentName;
  duration_ms: number;
  summary: string;
}

export interface WsConflictDetectedEvent extends WsBaseEvent {
  type: "conflict_detected";
  modules: string[];
  count: number;
}

export interface WsDegradedEvent extends WsBaseEvent {
  type: "degraded";
  agent: AgentName;
  reason: string;
  fallback: "cache" | "historical_average";
}

export interface WsCompletedEvent extends WsBaseEvent {
  type: "completed";
  report_url: string;
  total_duration_ms: number;
}

export interface WsFailedEvent extends WsBaseEvent {
  type: "failed";
  error_code: string;
  message: string;
}

export type WsEvent =
  | WsAgentStatusEvent
  | WsAgentCompletedEvent
  | WsConflictDetectedEvent
  | WsDegradedEvent
  | WsCompletedEvent
  | WsFailedEvent;

export interface AnalyzeRequest {
  source: "local" | "github";
  path: string;
}

export interface AnalyzeResponse {
  job_id: string;
  status: "queued";
  created_at: string;
  ws_url: string;
}
```
