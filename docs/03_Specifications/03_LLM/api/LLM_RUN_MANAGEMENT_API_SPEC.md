# LLM Run Management API 명세서

> **도메인**: LLM | **범위**: Status / Cancel / Evidence | **최종 업데이트**: 2026-06-23

## LLM-CHAT-API-003 Agent Run 상태 및 State 요약 조회

### 기본 정보

| 항목 | 값 |
| --- | --- |
| Endpoint | `GET /api/chat/{repo_id}/runs/{run_id}` |
| Method | GET |
| 관련 기능 ID | `LLM-CHAT-B-204`, `LLM-GRAPH-B-201`, `LLM-OPS-B-203` |
| 목적 | 실행 상태, node별 소요 시간, State 요약, 최종 답변 상태 조회 |
| 상태 | 설계 확정 / 구현 예정 |

### 응답

#### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| `code` | Integer | HTTP 상태 코드 |
| `message` | String | `success` |
| `data.runId` | UUID | agent run ID |
| `data.sessionId` | UUID | 대화 세션 ID |
| `data.status` | String | `queued`, `running`, `streaming`, `completed`, `failed`, `cancelled` |
| `data.currentNode` | String | 현재 실행 중인 node/worker |
| `data.state.userQuery` | String | 사용자 원본 질문 |
| `data.state.rewrittenQuery` | String | Planner가 교정한 검색 질의 |
| `data.state.accessPlan` | Object | selectedWorkers, allowedPaths, riskLevel |
| `data.state.securityResult` | Object | Dispatcher Node 검증 결과 |
| `data.state.workerResultCount` | Integer | raw evidence 개수 |
| `data.state.compactContextReady` | Boolean | compact context 준비 여부 |
| `data.state.stateKeys` | Array<String> | 현재 기록된 State key 목록 |
| `data.durations` | Object | node/worker별 소요 시간 |
| `data.finalAnswer` | Object/Null | 완료된 경우 최종 답변 메타데이터 |

#### 응답 예시

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "runId": "2f86a7b7-4d9b-45f1-bc5b-1c2b938c1d10",
    "sessionId": "a0de8d29-92a4-4fd6-a657-2d22f4c0cc75",
    "status": "running",
    "currentNode": "read_worker",
    "state": {
      "userQuery": "로그인 어딧음?",
      "rewrittenQuery": "login signin auth authentication",
      "accessPlan": {
        "selectedWorkers": ["search", "grep", "read"],
        "allowedPaths": ["backend/app", "frontend/src"],
        "riskLevel": "normal"
      },
      "securityResult": {
        "allowed": true,
        "blockedPaths": [],
        "policy": "repo_allowlist"
      },
      "workerResultCount": 5,
      "compactContextReady": false,
      "stateKeys": ["user_query", "rewritten_query", "access_plan", "security_result", "worker_results"]
    },
    "durations": {
      "planner_node": 1.4,
      "dispatcher_node": 0.03,
      "search_worker": 0.8,
      "grep_worker": 0.2
    },
    "finalAnswer": null
  }
}
```

---

## LLM-CHAT-API-004 Agent Run 취소

### 기본 정보

| 항목 | 값 |
| --- | --- |
| Endpoint | `POST /api/chat/{repo_id}/runs/{run_id}/cancel` |
| Method | POST |
| 관련 기능 ID | `LLM-CHAT-B-204`, `LLM-OPS-B-202`, `LLM-OPS-B-204` |
| 목적 | 실행 중인 LangGraph/worker run을 취소하고 SSE에 `cancelled` 이벤트 발행 |
| 상태 | 설계 확정 / 구현 예정 |

### 응답

#### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| `code` | Integer | HTTP 상태 코드 |
| `message` | String | `cancelled` |
| `data.runId` | UUID | 취소된 run ID |
| `data.status` | String | `cancelled` |
| `data.cancelledAt` | String | 취소 시각 |

### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| --- | --- | --- | --- |
| 404 | `LLM_RUN_NOT_FOUND` | run 조회 | run_id가 존재하지 않음 |
| 409 | `LLM_RUN_ALREADY_FINISHED` | 상태 검증 | 이미 completed/failed/cancelled 상태 |

---

## LLM-CHAT-API-005 Agent 근거 조회

### 기본 정보

| 항목 | 값 |
| --- | --- |
| Endpoint | `GET /api/chat/{repo_id}/runs/{run_id}/evidence` |
| Method | GET |
| 관련 기능 ID | `LLM-WORKER-B-201` ~ `LLM-WORKER-B-204`, `LLM-EVALUATOR-B-201` |
| 목적 | Worker가 `CodeMapState.worker_results`에 기록한 raw evidence와 compact context 조회 |
| 상태 | 설계 확정 / 구현 예정 |

### Query Parameters

| 파라미터명 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `includeRawSnippet` | Boolean | N | false | 원본 코드 snippet 포함 여부 |
| `worker` | String | N | - | `search`, `dir`, `grep`, `read`, `reasoning` |
| `limit` | Integer | N | 20 | 최대 evidence 수 |

### 응답

#### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| `code` | Integer | HTTP 상태 코드 |
| `message` | String | `success` |
| `data.runId` | UUID | agent run ID |
| `data.evidence` | Array<Object> | 근거 목록 |
| `data.evidence[].id` | String | evidence ID |
| `data.evidence[].worker` | String | 생성 worker |
| `data.evidence[].path` | String | 파일 경로 |
| `data.evidence[].lineStart` | Integer | 시작 라인 |
| `data.evidence[].lineEnd` | Integer | 종료 라인 |
| `data.evidence[].score` | Float | 검색/선정 점수 |
| `data.evidence[].snippet` | String/Null | 선택 시 반환되는 원본 코드 snippet |
| `data.compactContext` | Object | Final Answer Agent에 전달된 압축 근거 |
| `data.stateField` | String | `worker_results` |

### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| --- | --- | --- | --- |
| 404 | `LLM_RUN_NOT_FOUND` | run 조회 | run_id가 존재하지 않음 |
| 404 | `AGENT_EVIDENCE_NOT_FOUND` | evidence 조회 | State에 evidence가 없음 |
