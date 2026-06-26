# LLM 공통 API 명세서

> **도메인**: LLM | **범위**: Common Contract | **최종 업데이트**: 2026-06-26

## 공통 응답 형식

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

## 공통 에러 형식

```json
{
  "code": 400,
  "message": "error",
  "error": {
    "code": "INVALID_CHAT_REQUEST",
    "message": "요청을 처리할 수 없습니다.",
    "detail": "question is required"
  }
}
```

에러 응답의 `detail`에는 secret, token, credential, private file content를 포함하지 않습니다.

## 공통 Headers

| 헤더명 | 값 | 필수 | 설명 |
| --- | --- | --- | --- |
| `Content-Type` | `application/json` | POST 계열 Y | JSON 요청 |
| `Authorization` | `Bearer {access_token}` | Y | 인증 토큰 |
| `Accept` | `text/event-stream` | Stream API Y | SSE 수신 |

## 공통 Path Parameters

| 파라미터명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `repo_id` | UUID | Y | 대상 저장소 ID |
| `run_id` | UUID | run API Y | Agent 실행 ID |

## Run 상태값

| 상태 | 설명 |
| --- | --- |
| `queued` | run 생성 후 실행 대기 |
| `running` | LangGraph 데이터 수집 중 |
| `streaming` | Final Answer 응답 스트리밍 중 |
| `completed` | 정상 완료 |
| `failed` | 실패 |
| `cancelled` | 취소됨 |

## SSE 이벤트 타입

### 현재 구현 이벤트

| 이벤트 | 데이터 요약 | 설명 |
| --- | --- | --- |
| `graph_started` | `runId`, `stateKeys` | LangGraph 실행 시작 |
| `planner_plan` | `rewrittenQuery`, `selectedWorkers`, `allowedPaths` | Planner Node 계획 완료 |
| `route_validated` | `allowed`, `parallelGroups` | Dispatcher Node 검증 완료. 이벤트명은 기존 프론트 호환을 위해 유지 |
| `worker_started` | `worker`, `target` | worker 실행 시작 |
| `worker_result` | `worker`, `resultCount`, `evidenceIds` | worker 결과 기록 |
| `evidence_compacted` | `evidenceCount`, `compactContextReady` | evidence 정리 완료 |
| `evaluator_decision` | `sufficient`, `missingInfo`, `nextPlanHint`, `reason`, `confidence` | 근거 충분성 판단 |
| `replan_started` | `missingInfo`, `nextPlanHint`, `iteration`, `maxIterations` | 추가 탐색 계획 시작 |
| `answer_delta` | `content` | 최종 답변 토큰 조각 |
| `references` | `references[]` | 참조 파일 목록 |
| `completed` | `runId`, `status` | 정상 종료 |
| `cancelled` | `runId`, `cancelledAt` | 취소 종료 |
| `failed` | `runId`, `error` | 실패 종료 |

### 구현 예정 이벤트

| 이벤트 | 데이터 요약 | 설명 |
| --- | --- | --- |
| `worker_completed` | `worker`, `durationMs` | worker 실행 완료 |

## 공통 Error Code

| Error Code | HTTP Status | 설명 |
| --- | --- | --- |
| `UNAUTHORIZED` | 401 | 인증 토큰 누락 또는 만료 |
| `REPO_NOT_FOUND` | 404 | 저장소 없음 |
| `INVALID_CHAT_REQUEST` | 400 | 질문 또는 옵션 검증 실패 |
| `REPO_NOT_ANALYZED` | 409 | 저장소 분석/인덱싱 미완료 |
| `LLM_RUN_CREATE_FAILED` | 500 | agent run 생성 실패 |
| `LLM_RUN_NOT_FOUND` | 404 | agent run 없음 |
| `LLM_RUN_ALREADY_FINISHED` | 409 | 이미 종료된 run에 대한 불가능한 요청 |
| `AGENT_STREAM_FAILED` | 500 | SSE stream 처리 실패 |
| `AGENT_ROUTE_BLOCKED` | 403 | Dispatcher Node 보안 정책 차단 |
| `LLM_WORKER_FAILED` | 500 | worker 실행 실패 |
| `AGENT_EVIDENCE_NOT_FOUND` | 404 | evidence 없음 |
| `AGENT_EVIDENCE_NOT_READY` | 409 | reasoning에 필요한 evidence 미준비 |
| `AGENT_TOOL_POLICY_FAILED` | 500 | 외부 도구 정책 조회 실패 |
| `AGENT_REASONING_FAILED` | 500 | 선택형 reasoning worker 실패 |

## 모델 카탈로그 계약

Issue #181에 따라 프론트 모델 선택 UI와 백엔드 모델 검증은 같은 카탈로그를 기준으로 동작해야 합니다. 구현 방식은 `GET /api/llm/models` 또는 빌드 시 공유되는 정적 계약 중 하나를 선택할 수 있으나, 사용자에게 보이는 선택지와 backend allowlist가 어긋나서는 안 됩니다.

### LLM-COMMON-API-001: 모델 카탈로그 조회

| 항목 | 값 |
| --- | --- |
| Method | `GET` |
| Endpoint | `/api/llm/models` |
| 관련 기능 ID | `LLM-COMMON-B-201`, `LLM-COMMON-F-201` |
| 상태 | 제안 |

**성공 응답 — 200 OK**

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "defaultModel": "gpt-4o",
    "models": [
      {
        "id": "gpt-4o",
        "label": "GPT-4o",
        "provider": "openai",
        "capabilities": ["planner", "answer", "tool-calling"],
        "enabled": true,
        "disabledReason": null
      }
    ]
  }
}
```

**필드 규칙**

| 필드 | 설명 |
| --- | --- |
| `id` | API 요청에 사용할 model id. backend allowlist와 동일해야 함 |
| `label` | UI 표시명 |
| `provider` | 모델 제공자 |
| `capabilities` | `planner`, `answer`, `embedding`, `summarization` 등 역할 |
| `enabled` | 현재 환경에서 선택 가능 여부 |
| `disabledReason` | 비활성 모델의 사용자 안내 문구 |

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 400 | `UNSUPPORTED_MODEL` | 요청한 model id가 backend allowlist에 없음 |
| 422 | `MODEL_DISABLED` | 카탈로그에는 있으나 현재 환경에서 비활성화된 모델 |
| 500 | `MODEL_CATALOG_UNAVAILABLE` | 모델 카탈로그 조회 실패 |

**클라이언트 기준**

- enabled model만 primary selectable로 보여줍니다.
- disabled model은 선택 불가 상태와 `disabledReason`을 함께 표시합니다.
- unsupported model 요청 실패는 분석/채팅 실패 뒤늦은 에러가 아니라 입력 검증 오류로 처리합니다.
