# LLM 공통 API 명세서

> **도메인**: LLM | **범위**: Common Contract | **최종 업데이트**: 2026-06-23

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

| 이벤트 | 데이터 요약 | 설명 |
| --- | --- | --- |
| `graph_started` | `runId`, `stateKeys` | LangGraph 실행 시작 |
| `planner_plan` | `rewrittenQuery`, `selectedWorkers`, `allowedPaths` | Planner Node 계획 완료 |
| `route_validated` | `allowed`, `parallelGroups`, `blockedReason` | Dispatcher Node 검증 완료. 이벤트명은 기존 프론트 호환을 위해 유지 |
| `worker_started` | `worker`, `target` | worker 실행 시작 |
| `worker_result` | `worker`, `resultCount`, `evidenceIds` | worker 결과 기록 |
| `evidence_compacted` | `evidenceCount`, `compactContextReady` | evidence 정리 완료 |
| `answer_delta` | `content` | 최종 답변 토큰 조각 |
| `completed` | `runId`, `finalAnswer`, `durations` | 정상 종료 |
| `failed` | `runId`, `error`, `partialEvidenceCount` | 실패 종료 |
| `cancelled` | `runId`, `cancelledAt` | 취소 종료 |

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
