# AGENT Advanced API 명세서

> **도메인**: AGENT | **범위**: Memory / Allowed Tools / Reasoning Extension | **최종 업데이트**: 2026-06-23

## AGENT-ADVANCED-API-001 에이전트 장기 기억 조회

### 기본 정보

| 항목 | 값 |
| --- | --- |
| Endpoint | `GET /api/chat/{repo_id}/memory` |
| Method | GET |
| 관련 기능 ID | `AGENT-MEMORY-B-201` |
| 목적 | 이전 대화 세션에서 에이전트가 학습한 장기 기억 컨텍스트 조회 |
| 상태 | Phase 2 / 보류 |

### 응답

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| `code` | Integer | HTTP 상태 코드 |
| `message` | String | `success` |
| `data.repoId` | UUID | 저장소 ID |
| `data.memories` | Array<Object> | 장기 기억 목록 |
| `data.memories[].id` | String | memory ID |
| `data.memories[].summary` | String | 기억 요약 |
| `data.memories[].sourceRunId` | UUID | 생성 근거 run |
| `data.memories[].createdAt` | String | 생성 시각 |

---

## AGENT-ADVANCED-API-002 허용 외부 도구 Worker 목록 조회

### 기본 정보

| 항목 | 값 |
| --- | --- |
| Endpoint | `GET /api/chat/{repo_id}/tools/allowed` |
| Method | GET |
| 관련 기능 ID | `AGENT-WORKER-B-206` |
| 목적 | Phase 2에서 확장 가능한 외부 도구 worker allowlist와 권한 범위 조회 |
| 상태 | Phase 2 / 보류 |

### 응답

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| `code` | Integer | HTTP 상태 코드 |
| `message` | String | `success` |
| `data.repoId` | UUID | 저장소 ID |
| `data.tools` | Array<Object> | 허용된 외부 도구 worker 목록 |
| `data.tools[].name` | String | 도구 worker 이름 |
| `data.tools[].type` | String | `github`, `docs`, `issue`, `webhook` 등 |
| `data.tools[].enabled` | Boolean | 활성화 여부 |
| `data.tools[].allowedActions` | Array<String> | 허용 action 목록 |
| `data.tools[].requiresConfirmation` | Boolean | 사용자 확인 필요 여부 |

### 응답 예시

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

---

## AGENT-ADVANCED-API-003 Code Reasoning Worker 고도화 실행 요청

### 기본 정보

| 항목 | 값 |
| --- | --- |
| Endpoint | `POST /api/chat/{repo_id}/runs/{run_id}/reasoning` |
| Method | POST |
| 관련 기능 ID | `AGENT-WORKER-B-205`, `AGENT-WORKER-B-207` |
| 목적 | 기존 run의 State evidence를 기반으로 추가 Code Reasoning Worker 실행 |
| 상태 | Phase 2 / 보류 |

### Request Body

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| `focus` | String | N | - | `security`, `architecture`, `data_flow`, `bug_risk` 등 |
| `maxEvidence` | Integer | N | 12 | reasoning worker가 읽을 최대 evidence 수 |
| `includeNewSearch` | Boolean | N | false | 추가 worker 검색 허용 여부 |

### 응답

#### 성공 응답 - 202 Accepted

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| `code` | Integer | HTTP 상태 코드 |
| `message` | String | `accepted` |
| `data.runId` | UUID | 대상 run ID |
| `data.reasoningRunId` | UUID | 추가 reasoning 실행 ID |
| `data.status` | String | `reasoning_queued` |

### 에러 응답

| HTTP Status | Error Code | 발생 시점 | 설명 |
| --- | --- | --- | --- |
| 404 | `AGENT_RUN_NOT_FOUND` | run 조회 | run_id가 존재하지 않음 |
| 409 | `AGENT_EVIDENCE_NOT_READY` | 사전 검증 | reasoning에 필요한 evidence 미준비 |
| 500 | `AGENT_REASONING_FAILED` | worker 실행 | Code Reasoning Worker 실행 실패 |
