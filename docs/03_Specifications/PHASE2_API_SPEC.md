# Phase 2 고도화 기능 API 명세서

본 문서는 CodeMap **Phase 2(고도화)** 기능에 해당하는 API에 대한 상세 명세서입니다.
MVP 이후 점진적으로 도입되는 23개 기능을 포함하며, 각 도메인별로 정리합니다.

> **Phase 2 도메인 목록**:
> - **PROJECT-PIPELINE**: 비동기 깊은 분석 파이프라인
> - **RAG-GRAPH**: 코드 의존성 그래프 시각화
> - **RAG-PARSE 고도화**: 위험 신호 태깅, 기술 스택 점수화
> - **LLM 멀티에이전트**: LangGraph State 공유형 채팅 실행, SSE 스트리밍, 근거 조회
> - **LLM 고도화**: 장기 기억, 선택형 reasoning worker 고도화, 허용된 외부 도구 worker
> - **DOCS-UTIL**: HTML-PDF 변환, 이메일/Slack 공유
> - **PROJECT-REPO**: 중복 저장소 검사

---

## 공통 규격

### 응답 공통 형식

```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

---

## PROJECT-PIPELINE API 명세서

> 관련 기능 ID: `PROJECT-PIPELINE-B-201` ~ `PROJECT-PIPELINE-F-301`

---

### PIPELINE-API-001 분석 단계 상태 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/pipeline/{job_id}/stages` |
| Method | GET |
| 관련 기능 ID | `PROJECT-PIPELINE-B-201` |
| 목적 | 비동기 분석 파이프라인의 각 단계별 실행 상태 조회 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Headers

| 헤더명 | 값 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| Authorization | Bearer {access_token} | Y | 인증 토큰 |

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| job_id | UUID | Y | 분석 작업 고유 ID |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.jobId | UUID | 분석 작업 ID |
| data.overallStatus | String | 전체 파이프라인 상태 (queued, running, completed, failed) |
| data.stages | Array<Object> | 각 단계 상태 목록 |
| data.stages[].name | String | 단계명 (clone, parse, embed, agent, docs) |
| data.stages[].status | String | 단계 상태 |
| data.stages[].startedAt | String | 단계 시작 시각 |
| data.stages[].completedAt | String | 단계 완료 시각 (완료된 경우) |
| data.stages[].elapsedSeconds | Float | 단계 소요 시간 |

##### 응답 예시

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "jobId": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "overallStatus": "running",
    "stages": [
      { "name": "clone", "status": "completed", "startedAt": "2026-06-18T10:00:00Z", "completedAt": "2026-06-18T10:00:30Z", "elapsedSeconds": 30.5 },
      { "name": "parse", "status": "completed", "startedAt": "2026-06-18T10:00:31Z", "completedAt": "2026-06-18T10:01:00Z", "elapsedSeconds": 29.0 },
      { "name": "embed", "status": "running", "startedAt": "2026-06-18T10:01:01Z", "completedAt": null, "elapsedSeconds": null },
      { "name": "agent", "status": "queued", "startedAt": null, "completedAt": null, "elapsedSeconds": null },
      { "name": "docs", "status": "queued", "startedAt": null, "completedAt": null, "elapsedSeconds": null }
    ]
  }
}
```

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `JOB_NOT_FOUND` | DB 조회 | 해당 job_id가 존재하지 않음 |

---

### PIPELINE-API-002 비동기 깊은 분석 파이프라인 실행

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/pipeline/{job_id}/deep` |
| Method | POST |
| 관련 기능 ID | `PROJECT-PIPELINE-B-202` |
| 목적 | 기본 분석 완료 후 심층 분석 파이프라인(Advanced Reasoning 포함) 비동기 실행 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| job_id | UUID | Y | 분석 작업 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| includeRiskAnalysis | Boolean | N | true | 위험 신호 태깅 포함 여부 |
| includeStackScore | Boolean | N | true | 기술 스택 점수화 포함 여부 |
| includeDependencyGraph | Boolean | N | true | 의존성 그래프 생성 포함 여부 |

#### 응답(Response)

##### 성공 응답 - 202 Accepted

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 (202) |
| message | String | "accepted" |
| data.jobId | UUID | 분석 작업 ID |
| data.deepPipelineStatus | String | deep_analysis_queued |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `JOB_NOT_FOUND` | DB 조회 | 작업 없음 |
| 409 | `BASIC_ANALYSIS_NOT_COMPLETED` | 사전 검증 | 기본 분석이 완료되지 않은 상태에서 심층 분석 요청 |
| 500 | `PIPELINE_START_FAILED` | 파이프라인 초기화 | 심층 분석 시작 중 오류 |

---

### PIPELINE-API-003 파이프라인 외부 연동 Webhook 등록

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/pipeline/{job_id}/webhook` |
| Method | POST |
| 관련 기능 ID | `PROJECT-PIPELINE-B-203` |
| 목적 | 분석 완료 시 외부 시스템에 Webhook 알림을 발송하도록 URL 등록 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Request Body

| 필드명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| webhookUrl | String | Y | Webhook 수신 URL |
| events | Array<String> | Y | 알림 받을 이벤트 목록 (completed, failed) |
| secret | String | N | HMAC 서명 검증용 시크릿 키 |

#### 응답(Response)

##### 성공 응답 - 201 Created

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 (201) |
| message | String | "created" |
| data.webhookId | UUID | 등록된 Webhook 고유 ID |
| data.webhookUrl | String | 등록된 Webhook URL |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_WEBHOOK_URL` | URL 검증 | 유효하지 않은 Webhook URL 형식 |
| 404 | `JOB_NOT_FOUND` | DB 조회 | 작업 없음 |

---

## RAG-GRAPH API 명세서

> 관련 기능 ID: `RAG-GRAPH-B-201`, `RAG-GRAPH-F-201`

---

### GRAPH-API-001 코드 의존성 그래프 생성

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/graph/{repo_id}` |
| Method | POST |
| 관련 기능 ID | `RAG-GRAPH-B-201` |
| 목적 | import 관계를 기반으로 코드 의존성 그래프 데이터 생성 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 그래프 생성 대상 저장소 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| maxDepth | Integer | N | 3 | 의존성 탐색 최대 깊이 |
| excludePaths | Array<String> | N | [] | 그래프에서 제외할 경로 목록 |

#### 응답(Response)

##### 성공 응답 - 202 Accepted

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 (202) |
| message | String | "accepted" |
| data.graphId | UUID | 생성된 그래프 고유 ID |
| data.status | String | graph_queued |

---

### GRAPH-API-002 의존성 그래프 데이터 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/graph/{repo_id}` |
| Method | GET |
| 관련 기능 ID | `RAG-GRAPH-B-201`, `RAG-GRAPH-F-201` |
| 목적 | 프론트엔드 시각화용 코드 의존성 그래프 데이터 반환 |
| 상태 | 시작 전 (Phase 2) |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.nodes | Array<Object> | 그래프 노드 목록 (파일) |
| data.nodes[].id | String | 노드 ID (파일 경로) |
| data.nodes[].label | String | 표시 레이블 (파일명) |
| data.nodes[].type | String | 노드 유형 (entry, service, model 등) |
| data.nodes[].riskScore | Integer | 위험도 점수 (0-100) |
| data.edges | Array<Object> | 그래프 엣지 목록 (의존성) |
| data.edges[].source | String | 참조하는 파일 경로 |
| data.edges[].target | String | 참조되는 파일 경로 |
| data.edges[].type | String | 의존성 유형 (import, export) |

##### 응답 예시

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "nodes": [
      { "id": "backend/app/main.py", "label": "main.py", "type": "entry", "riskScore": 20 },
      { "id": "backend/app/repo/service.py", "label": "service.py", "type": "service", "riskScore": 45 }
    ],
    "edges": [
      { "source": "backend/app/main.py", "target": "backend/app/repo/service.py", "type": "import" }
    ]
  }
}
```

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `GRAPH_NOT_FOUND` | DB 조회 | 의존성 그래프가 아직 생성되지 않음 |
| 500 | `GRAPH_BUILD_FAILED` | 그래프 처리 | 의존성 그래프 생성 중 오류 |

---

## RAG-PARSE 고도화 API 명세서

> 관련 기능 ID: `RAG-PARSE-B-211`, `RAG-PARSE-B-212`, `RAG-PARSE-F-202`

---

### PARSE-ADVANCED-API-001 위험 신호 태깅 결과 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/parse/analysis/{repo_id}/risks` |
| Method | GET |
| 관련 기능 ID | `RAG-PARSE-B-211` |
| 목적 | 코드 복잡도, 민감정보 패턴, 병목 파일 등 위험 신호 태깅 결과 반환 |
| 상태 | 시작 전 (Phase 2) |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.repoId | UUID | 저장소 고유 ID |
| data.risks | Array<Object> | 위험 신호 목록 |
| data.risks[].path | String | 위험 파일 경로 |
| data.risks[].type | String | 위험 유형 (high_complexity, sensitive_data, bottleneck 등) |
| data.risks[].severity | String | 심각도 (critical, high, medium, low) |
| data.risks[].description | String | 위험 사유 설명 |
| data.risks[].riskScore | Integer | 위험도 점수 (0-100) |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `RISK_ANALYSIS_NOT_FOUND` | DB 조회 | 위험 분석 결과가 없음 |
| 500 | `RISK_ANALYSIS_FAILED` | 분석 처리 | 위험 신호 분석 중 오류 |

---

### PARSE-ADVANCED-API-002 기술 스택 점수화 결과 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/parse/analysis/{repo_id}/stack-score` |
| Method | GET |
| 관련 기능 ID | `RAG-PARSE-B-212`, `RAG-PARSE-F-202` |
| 목적 | 기술 스택 성숙도, 보안 취약점 버전 여부, 최신성 점수 반환 |
| 상태 | 시작 전 (Phase 2) |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.repoId | UUID | 저장소 고유 ID |
| data.overallScore | Integer | 전체 기술 스택 점수 (0-100) |
| data.stacks | Array<Object> | 개별 기술별 점수 |
| data.stacks[].name | String | 기술명 |
| data.stacks[].version | String | 사용 버전 |
| data.stacks[].latestVersion | String | 최신 버전 |
| data.stacks[].score | Integer | 기술별 점수 |
| data.stacks[].hasVulnerability | Boolean | 알려진 보안 취약점 여부 |
| data.stacks[].isOutdated | Boolean | 구버전 여부 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `STACK_SCORE_NOT_FOUND` | DB 조회 | 점수화 결과 없음 |
| 500 | `STACK_SCORE_FAILED` | 점수 계산 | 기술 스택 점수화 처리 중 오류 |

---

## LLM 멀티에이전트 API 명세서

> [!IMPORTANT]
> 아래 LLM API는 최신 합의된 LangGraph State 공유형 멀티에이전트 구조를 기준으로 합니다. `Dispatcher Node`는 LLM agent가 아니라 deterministic code node이며, 보안 검증과 병렬 worker routing을 담당합니다.
> 구현 위치 기준으로 `Final Answer Agent`는 `chat/final_answer_agent.py`에 두고, Planner/Dispatcher/Workers/Evaluator node는 `agent/` 아래에 둡니다.

> 관련 기능 ID: `LLM-CHAT-B-101`, `LLM-CHAT-B-201` ~ `LLM-CHAT-B-204`, `LLM-GRAPH-B-201` ~ `LLM-GRAPH-B-202`, `LLM-PLANNER-B-201`, `LLM-DISPATCHER-B-201` ~ `LLM-DISPATCHER-B-203`, `LLM-WORKER-B-201` ~ `LLM-WORKER-B-205`, `LLM-EVALUATOR-B-201`

### LLM 공통 State 및 역할 계약

| 구분 | 명세 |
| :--- | :--- |
| 구현 기준 구조 | `backend/app/chat/` + `backend/app/agent/` |
| `Final Answer Agent` 위치 | `chat/final_answer_agent.py` |
| LangGraph 데이터 수집 계층 | `agent/state.py`, `graph.py`, `service.py`, `llm_client.py`, `nodes/`, `workers/` |
| LLM agent | `Planner Node`, `Final Answer Agent` |
| 일반 코드 node/wrapper | `Dispatcher Node`, `Evaluator Node`, `Search Worker`, `Dir Worker`, `Grep Worker`, `Read Worker` |
| `CodeMapState` 핵심 필드 | `user_query`, `rewritten_query`, `access_plan`, `security_result`, `worker_results`, `compact_context`, `final_answer` |
| 원본 근거 보존 기준 | Worker 결과는 중간 LLM 요약 없이 `CodeMapState.worker_results`에 append-only 방식으로 기록 |

---

### LLM-CHAT-API-001 멀티에이전트 채팅 실행 요청

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/chat/{repo_id}/runs` |
| Method | POST |
| 관련 기능 ID | `LLM-CHAT-B-101`, `LLM-CHAT-B-201`, `LLM-GRAPH-B-201`, `LLM-PLANNER-B-201` |
| 목적 | 사용자 질문을 받아 LangGraph 멀티에이전트 실행 run을 생성하고 SSE stream URL을 반환 |
| 상태 | 구현 완료 |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 질문 대상 저장소 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| question | String | Y | - | 사용자 원본 질문 |
| sessionId | UUID | N | 자동 생성 | 이어지는 대화 세션 ID |
| mode | String | N | `standard` | 실행 모드 (`lite`, `standard`, `deep`) |
| includeEvidence | Boolean | N | true | 최종 응답에 파일 경로/라인 근거 포함 여부 |
| maxToolCalls | Integer | N | 8 | 전체 worker tool call 최대 횟수 |
| timeoutSeconds | Integer | N | 30 | run 전체 제한 시간 |

##### 요청 예시

```json
{
  "question": "로그인 어딧음?",
  "mode": "standard",
  "includeEvidence": true,
  "maxToolCalls": 8,
  "timeoutSeconds": 30
}
```

#### 응답(Response)

##### 성공 응답 - 202 Accepted

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 (202) |
| message | String | "accepted" |
| data.runId | UUID | 생성된 agent 실행 ID |
| data.sessionId | UUID | 대화 세션 ID |
| data.status | String | `queued` |
| data.streamUrl | String | SSE 수신 URL |
| data.statusUrl | String | run 상태 조회 URL |
| data.evidenceUrl | String | evidence 조회 URL |

##### 응답 예시

```json
{
  "code": 202,
  "message": "accepted",
  "data": {
    "runId": "2f86a7b7-4d9b-45f1-bc5b-1c2b938c1d10",
    "sessionId": "a0de8d29-92a4-4fd6-a657-2d22f4c0cc75",
    "status": "queued",
    "streamUrl": "/api/chat/8cfd0f7b-3ec3-42e3-97c4-8f4b4cc9390f/runs/2f86a7b7-4d9b-45f1-bc5b-1c2b938c1d10/stream",
    "statusUrl": "/api/chat/8cfd0f7b-3ec3-42e3-97c4-8f4b4cc9390f/runs/2f86a7b7-4d9b-45f1-bc5b-1c2b938c1d10",
    "evidenceUrl": "/api/chat/8cfd0f7b-3ec3-42e3-97c4-8f4b4cc9390f/runs/2f86a7b7-4d9b-45f1-bc5b-1c2b938c1d10/evidence"
  }
}
```

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_CHAT_REQUEST` | 요청 검증 | 질문 누락, mode 값 오류, 제한값 초과 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 409 | `REPO_NOT_ANALYZED` | 사전 검증 | 분석/인덱싱이 완료되지 않은 저장소 |
| 500 | `LLM_RUN_CREATE_FAILED` | run 생성 | agent run 생성 실패 |

---

### LLM-CHAT-API-002 멀티에이전트 SSE 스트림

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/chat/{repo_id}/runs/{run_id}/stream` |
| Method | GET |
| 관련 기능 ID | `LLM-CHAT-B-203`, `LLM-OPS-B-201`, `LLM-OPS-B-202`, `LLM-OPS-B-204` |
| 목적 | LangGraph 실행 과정과 Final Answer 토큰을 SSE로 실시간 전달 |
| 상태 | 구현 완료 |

#### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 저장소 고유 ID |
| run_id | UUID | Y | agent 실행 ID |

#### SSE 이벤트 규격

| Event | data payload | 설명 |
| :--- | :--- | :--- |
| `graph_started` | `{ "runId": "...", "stateKeys": ["user_query"] }` | LangGraph 실행 시작 |
| `planner_plan` | `{ "rewrittenQuery": "...", "selectedWorkers": [...], "allowedPaths": [...] }` | Planner LLM 계획 생성 완료 |
| `route_validated` | `{ "allowed": true, "parallelGroups": [...] }` | deterministic Dispatcher Node 검증 완료 |
| `worker_started` | `{ "worker": "grep", "target": "backend/app" }` | worker 실행 시작 |
| `worker_result` | `{ "worker": "grep", "resultCount": 3, "evidenceIds": [...] }` | worker 원본 근거 State 기록 완료 |
| `evidence_compacted` | `{ "evidenceCount": 8, "tokenBudget": 12000 }` | Evaluator 정리 완료 |
| `answer_delta` | `{ "content": "로그인 로직은..." }` | Final Answer 토큰 조각 |
| `references` | `{ "references": [...] }` | 참조 파일 목록 |
| `completed` | `{ "runId": "...", "status": "completed" }` | run 정상 완료 |
| `cancelled` | `{ "runId": "...", "cancelledAt": "..." }` | run 취소 |
| `failed` | `{ "runId": "...", "error": "AGENT_TIMEOUT" }` | run 실패 |

#### 스트림 예시

```text
event: graph_started
data: {"runId":"2f86a7b7-4d9b-45f1-bc5b-1c2b938c1d10","stateKeys":["user_query"]}

event: planner_plan
data: {"rewrittenQuery":"login signin auth authentication","selectedWorkers":["search","grep","read"],"allowedPaths":["backend/app","frontend/src"]}

event: route_validated
data: {"allowed":true,"parallelGroups":[["search","grep"],["read"]]}

event: worker_started
data: {"worker":"grep","target":"backend/app"}

event: worker_result
data: {"worker":"grep","resultCount":3,"evidenceIds":["ev_001","ev_002","ev_003"]}

event: answer_delta
data: {"content":"로그인 로직은 "}

event: answer_delta
data: {"content":"backend/app/auth/router.py에서 시작됩니다."}

event: completed
data: {"runId":"2f86a7b7-4d9b-45f1-bc5b-1c2b938c1d10","status":"completed"}
```

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `LLM_RUN_NOT_FOUND` | run 조회 | run_id가 존재하지 않음 |
| 409 | `LLM_RUN_ALREADY_FINISHED` | stream 연결 | 이미 완료된 run에 stream 재연결 |
| 500 | `AGENT_STREAM_FAILED` | SSE 처리 | 스트림 초기화 또는 전송 실패 |

---

### LLM-CHAT-API-003 Agent Run 상태 및 State 요약 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/chat/{repo_id}/runs/{run_id}` |
| Method | GET |
| 관련 기능 ID | `LLM-CHAT-B-204`, `LLM-GRAPH-B-201`, `LLM-OPS-B-203` |
| 목적 | 실행 상태, node별 소요 시간, State 요약, 최종 답변 상태 조회 |
| 상태 | 구현 완료 |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.runId | UUID | agent 실행 ID |
| data.sessionId | UUID | 대화 세션 ID |
| data.status | String | `queued`, `running`, `streaming`, `completed`, `failed`, `cancelled` |
| data.currentNode | String | 현재 실행 중인 node/worker |
| data.state.userQuery | String | 사용자 원본 질문 |
| data.state.rewrittenQuery | String | Planner가 교정한 검색 질의 |
| data.state.accessPlan | Object | selectedWorkers, allowedPaths, riskLevel |
| data.state.securityResult | Object | Dispatcher Node의 allowlist/path traversal 검증 결과 |
| data.state.workerResultCount | Integer | State에 기록된 raw evidence 개수 |
| data.state.compactContextReady | Boolean | Final Answer용 compact context 준비 여부 |
| data.state.stateKeys | Array<String> | 현재 `CodeMapState`에 기록된 key 목록 |
| data.durations | Object | node/worker별 소요 시간 |
| data.finalAnswer | Object | 완료된 경우 최종 답변 메타데이터 |

##### 응답 예시

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

### LLM-CHAT-API-004 Agent Run 취소

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/chat/{repo_id}/runs/{run_id}/cancel` |
| Method | POST |
| 관련 기능 ID | `LLM-CHAT-B-204`, `LLM-OPS-B-202`, `LLM-OPS-B-204` |
| 목적 | 실행 중인 LangGraph/worker run을 취소하고 SSE에 cancelled 이벤트 발행 |
| 상태 | 구현 완료 |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "cancelled" |
| data.runId | UUID | 취소된 run ID |
| data.status | String | `cancelled` |
| data.cancelledAt | String | 취소 시각 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `LLM_RUN_NOT_FOUND` | run 조회 | run_id가 존재하지 않음 |
| 409 | `LLM_RUN_ALREADY_FINISHED` | 상태 검증 | 이미 completed/failed/cancelled 상태 |

---

### LLM-CHAT-API-005 Agent 근거 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/chat/{repo_id}/runs/{run_id}/evidence` |
| Method | GET |
| 관련 기능 ID | `LLM-WORKER-B-201` ~ `LLM-WORKER-B-204`, `LLM-EVALUATOR-B-201` |
| 목적 | Worker가 `CodeMapState.worker_results`에 직접 기록한 raw evidence와 compact context 조회 |
| 상태 | 구현 완료 |

#### Query Parameters

| 파라미터명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| includeRawSnippet | Boolean | N | false | 원본 코드 snippet 포함 여부 |
| worker | String | N | - | 특정 worker 결과만 필터링 (`search`, `dir`, `grep`, `read`, `reasoning`) |
| limit | Integer | N | 20 | 반환할 최대 evidence 수 |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.runId | UUID | agent 실행 ID |
| data.evidence | Array<Object> | 근거 목록 |
| data.evidence[].id | String | evidence ID |
| data.evidence[].worker | String | 생성 worker |
| data.evidence[].path | String | 파일 경로 |
| data.evidence[].lineStart | Integer | 시작 라인 |
| data.evidence[].lineEnd | Integer | 종료 라인 |
| data.evidence[].score | Float | 검색/선정 점수 |
| data.evidence[].snippet | String | 선택 시 반환되는 원본 코드 snippet |
| data.compactContext | String | Final Answer Agent에 전달된 압축 근거 |
| data.stateField | String | 원본 근거가 저장된 State 필드명 (`worker_results`) |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `LLM_RUN_NOT_FOUND` | run 조회 | run_id가 존재하지 않음 |
| 404 | `AGENT_EVIDENCE_NOT_FOUND` | evidence 조회 | State에 evidence가 없음 |

---

## LLM 고도화 확장 API 명세서

> 관련 기능 ID: `LLM-MEMORY-B-201`, `LLM-WORKER-B-206`, `LLM-WORKER-B-207`

---

### LLM-ADVANCED-API-001 에이전트 장기 기억 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/chat/{repo_id}/memory` |
| Method | GET |
| 관련 기능 ID | `LLM-MEMORY-B-201` |
| 목적 | 이전 대화 세션에서 에이전트가 학습한 장기 기억 컨텍스트 조회 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 저장소 고유 ID |

##### Query Parameters

| 파라미터명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| userId | String | N | - | 사용자 ID (없으면 전체 조회) |
| limit | Integer | N | 20 | 반환할 최대 기억 항목 수 |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.memories | Array<Object> | 장기 기억 목록 |
| data.memories[].key | String | 기억 키 (파일명, 개념명 등) |
| data.memories[].value | String | 기억 내용 |
| data.memories[].createdAt | String | 기억 생성 시각 |
| data.memories[].accessCount | Integer | 참조 횟수 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 500 | `MEMORY_RETRIEVAL_FAILED` | 기억 조회 | 장기 기억 조회 중 오류 |

---

### LLM-ADVANCED-API-002 허용 외부 도구 Worker 목록 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/chat/{repo_id}/tools/allowed` |
| Method | GET |
| 관련 기능 ID | `LLM-WORKER-B-206` |
| 목적 | Phase 2에서 확장 가능한 외부 도구 worker allowlist와 권한 범위 조회 |
| 상태 | 시작 전 (Phase 2) |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.repoId | UUID | 저장소 고유 ID |
| data.tools | Array<Object> | 허용된 외부 도구 worker 목록 |
| data.tools[].name | String | 도구 worker 이름 |
| data.tools[].type | String | 도구 유형 (`github`, `docs`, `issue`, `webhook` 등) |
| data.tools[].enabled | Boolean | 활성화 여부 |
| data.tools[].allowedActions | Array<String> | 허용된 action 목록 |
| data.tools[].requiresConfirmation | Boolean | 사용자 확인 필요 여부 |

##### 응답 예시

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "repoId": "8cfd0f7b-3ec3-42e3-97c4-8f4b4cc9390f",
    "tools": [
      {
        "name": "github_issue_search",
        "type": "github",
        "enabled": false,
        "allowedActions": ["search"],
        "requiresConfirmation": false
      }
    ]
  }
}
```

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 500 | `AGENT_TOOL_POLICY_FAILED` | 정책 조회 | 외부 도구 worker 정책 조회 실패 |

---

### LLM-ADVANCED-API-003 선택형 Reasoning Worker 고도화 실행 요청

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/chat/{repo_id}/runs/{run_id}/reasoning` |
| Method | POST |
| 관련 기능 ID | `LLM-WORKER-B-205`, `LLM-WORKER-B-207` |
| 목적 | 기존 run의 State evidence를 기반으로 Phase 2 선택형 reasoning worker를 실행 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| focus | String | N | - | 추가 추론 초점 (`security`, `architecture`, `data_flow`, `bug_risk` 등) |
| maxEvidence | Integer | N | 12 | reasoning worker가 읽을 최대 evidence 수 |
| includeNewSearch | Boolean | N | false | 추가 worker 검색 허용 여부 |

#### 응답(Response)

##### 성공 응답 - 202 Accepted

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 (202) |
| message | String | "accepted" |
| data.runId | UUID | 대상 run ID |
| data.reasoningRunId | UUID | 추가 reasoning worker 실행 ID |
| data.status | String | `reasoning_queued` |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `LLM_RUN_NOT_FOUND` | run 조회 | run_id가 존재하지 않음 |
| 409 | `AGENT_EVIDENCE_NOT_READY` | 사전 검증 | reasoning에 필요한 evidence가 아직 준비되지 않음 |
| 500 | `AGENT_REASONING_FAILED` | worker 실행 | 선택형 reasoning worker 실행 실패 |

---

## DOCS-UTIL API 명세서

> 관련 기능 ID: `DOCS-UTIL-B-201`, `DOCS-UTIL-B-202`

---

### UTIL-API-001 HTML-PDF 파일 렌더링 및 변환

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/gen/docs/{repo_id}/export/pdf` |
| Method | POST |
| 관련 기능 ID | `DOCS-UTIL-B-201` |
| 목적 | 온보딩 가이드북 Markdown을 서버 사이드에서 PDF로 변환하여 다운로드 제공 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | PDF 변환 대상 저장소 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| theme | String | N | default | PDF 스타일 테마 (default, dark, minimal) |
| includeCodeHighlight | Boolean | N | true | 코드 블록 구문 강조 포함 여부 |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 헤더명 | 값 | 설명 |
| :--- | :--- | :--- |
| Content-Type | application/pdf | PDF 파일 |
| Content-Disposition | attachment; filename="{repoName}_onboarding.pdf" | 다운로드 파일명 |

> 응답 body는 PDF 바이너리 데이터입니다.

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `DOCS_NOT_FOUND` | DB 조회 | 가이드북 없음 |
| 500 | `PDF_RENDER_FAILED` | PDF 변환 | HTML→PDF 렌더링 중 오류 |

---

### UTIL-API-002 이메일 및 Slack 외부 공유

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/gen/docs/{repo_id}/share` |
| Method | POST |
| 관련 기능 ID | `DOCS-UTIL-B-202` |
| 목적 | 분석 완료된 온보딩 가이드북을 이메일 또는 Slack 채널로 공유 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repo_id | UUID | Y | 공유 대상 저장소 고유 ID |

##### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| :--- | :--- | :--- | :--- | :--- |
| channels | Array<Object> | Y | - | 공유 채널 목록 |
| channels[].type | String | Y | - | 채널 유형 (email / slack) |
| channels[].target | String | Y | - | 이메일 주소 또는 Slack Webhook URL |
| includeFullGuide | Boolean | N | false | 가이드북 전문 포함 여부 (false면 요약만) |

##### 요청 예시

```json
{
  "channels": [
    { "type": "email", "target": "newdev@company.com" },
    { "type": "slack", "target": "https://hooks.slack.com/services/T00/B00/xxx" }
  ],
  "includeFullGuide": false
}
```

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.sentChannels | Array<Object> | 발송 성공 채널 목록 |
| data.failedChannels | Array<Object> | 발송 실패 채널 목록 |
| data.sentAt | String | 발송 시각 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_CHANNEL` | 채널 검증 | 유효하지 않은 이메일 또는 Slack URL |
| 404 | `DOCS_NOT_FOUND` | DB 조회 | 가이드북 없음 |
| 500 | `SHARE_FAILED` | 발송 처리 | 이메일 또는 Slack 발송 중 오류 |

---

## PROJECT-REPO 고도화 API 명세서

> 관련 기능 ID: `PROJECT-REPO-B-303`

---

### REPO-FILE-API-001 저장소 파일 컨텐츠 조회

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `GET /api/repo/analysis/{job_id}/files/content` |
| Method | GET |
| 관련 기능 ID | `PROJECT-REPO-F-001` |
| 목적 | 분석 job의 clone workspace 내 특정 파일 텍스트 내용을 반환하여 코드 미리보기 지원 |
| 상태 | 완료 (fix/issue-160) |

#### 요청(Request)

##### Path Parameters

| 파라미터 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| job_id | UUID | Y | 분석 작업 고유 ID |

##### Query Parameters

| 파라미터 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| path | String | Y | 저장소 내 상대 경로 (예: `src/main.py`) |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | 200 |
| message | String | "success" |
| data.path | String | 저장소 내 상대 경로 |
| data.content | String | 파일 텍스트 내용 (최대 50,000자) |
| data.language | String \| null | 감지된 언어 (예: "python", "typescript") |
| data.lines | Integer | 총 줄 수 |
| data.truncated | Boolean | 파일 크기 초과로 내용이 잘렸는지 여부 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 403 | `FILE_PATH_FORBIDDEN` | 경로 검증 | path traversal 또는 workspace 외부 경로 |
| 404 | `JOB_NOT_FOUND` | job 확인 | 존재하지 않는 job_id |
| 404 | `WORKSPACE_NOT_READY` | workspace 확인 | clone workspace 미준비 또는 파일 없음 |
| 422 | `BINARY_FILE` | 파일 유형 확인 | 바이너리 파일 (미리보기 불가) |

---

### REPO-ADVANCED-API-001 중복 저장소 검사

#### 기본 정보

| 항목 | 값 |
| :--- | :--- |
| Endpoint | `POST /api/repo/check-duplicate` |
| Method | POST |
| 관련 기능 ID | `PROJECT-REPO-B-303` |
| 목적 | 동일한 GitHub URL의 분석 이력 존재 여부 사전 확인 |
| 상태 | 시작 전 (Phase 2) |

#### 요청(Request)

##### Request Body

| 필드명 | 타입 | 필수 | 설명 |
| :--- | :--- | :--- | :--- |
| repoUrl | String | Y | 중복 검사할 GitHub 저장소 URL |
| branch | String | N | 검사 대상 브랜치 |

#### 응답(Response)

##### 성공 응답 - 200 OK

| 필드명 | 타입 | 설명 |
| :--- | :--- | :--- |
| code | Integer | HTTP 상태 코드 |
| message | String | "success" |
| data.isDuplicate | Boolean | 중복 여부 |
| data.existingJob | Object | 기존 분석 작업 정보 (중복인 경우) |
| data.existingJob.jobId | UUID | 기존 작업 ID |
| data.existingJob.status | String | 기존 작업 상태 |
| data.existingJob.createdAt | String | 기존 작업 생성 시각 |

##### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_REPO_URL` | URL 검증 | 잘못된 GitHub URL 형식 |
| 500 | `DATABASE_ERROR` | DB 조회 | 데이터베이스 조회 중 오류 |

---

## 에러 코드 정의

| Error Code | HTTP Status | 설명 |
| :--- | :--- | :--- |
| `FILE_PATH_FORBIDDEN` | 403 | path traversal 또는 허용되지 않는 파일 경로 |
| `WORKSPACE_NOT_READY` | 404 | clone workspace 미준비 또는 파일 없음 |
| `BINARY_FILE` | 422 | 바이너리 파일로 미리보기 불가 |
| `BASIC_ANALYSIS_NOT_COMPLETED` | 409 | 기본 분석이 완료되지 않은 상태 |
| `INVALID_WEBHOOK_URL` | 400 | 유효하지 않은 Webhook URL |
| `GRAPH_NOT_FOUND` | 404 | 의존성 그래프가 생성되지 않음 |
| `GRAPH_BUILD_FAILED` | 500 | 의존성 그래프 생성 실패 |
| `RISK_ANALYSIS_NOT_FOUND` | 404 | 위험 신호 분석 결과 없음 |
| `RISK_ANALYSIS_FAILED` | 500 | 위험 신호 분석 처리 실패 |
| `STACK_SCORE_NOT_FOUND` | 404 | 기술 스택 점수화 결과 없음 |
| `STACK_SCORE_FAILED` | 500 | 기술 스택 점수화 실패 |
| `INVALID_CHAT_REQUEST` | 400 | agent 채팅 실행 요청 검증 실패 |
| `REPO_NOT_ANALYZED` | 409 | agent 실행 전 저장소 분석/인덱싱 미완료 |
| `LLM_RUN_CREATE_FAILED` | 500 | agent run 생성 실패 |
| `LLM_RUN_NOT_FOUND` | 404 | agent run이 존재하지 않음 |
| `LLM_RUN_ALREADY_FINISHED` | 409 | 이미 종료된 agent run에 대한 불가능한 요청 |
| `AGENT_STREAM_FAILED` | 500 | SSE 스트림 처리 실패 |
| `AGENT_EVIDENCE_NOT_FOUND` | 404 | agent State evidence가 존재하지 않음 |
| `AGENT_EVIDENCE_NOT_READY` | 409 | 추가 reasoning에 필요한 evidence가 준비되지 않음 |
| `AGENT_TOOL_POLICY_FAILED` | 500 | 외부 도구 worker 정책 조회 실패 |
| `AGENT_REASONING_FAILED` | 500 | 선택형 reasoning worker 실행 실패 |
| `MEMORY_RETRIEVAL_FAILED` | 500 | 에이전트 장기 기억 조회 실패 |
| `PDF_RENDER_FAILED` | 500 | HTML→PDF 렌더링 실패 |
| `SHARE_FAILED` | 500 | 이메일 또는 Slack 발송 실패 |
| `INVALID_CHANNEL` | 400 | 유효하지 않은 이메일 또는 Slack URL |
