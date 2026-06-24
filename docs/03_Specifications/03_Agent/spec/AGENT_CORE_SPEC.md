# AGENT CORE 기능 명세서

> **도메인**: AGENT | **모듈**: AGENT-CORE | **최종 업데이트**: 2026-06-23

## 범위

`AGENT-CORE`는 멀티에이전트 실행 전반에서 공통으로 사용하는 이벤트, 상태, 실패 처리, 실행 시간 측정, cleanup 정책을 정의합니다. 특정 LLM prompt나 파일 검색 전략이 아니라 run lifecycle을 안정적으로 관리하는 공통 계약입니다.

| 구분 | 기준 |
| --- | --- |
| 적용 계층 | `chat/`, `agent_graph/`, frontend run UI |
| 주요 상태 | `queued`, `running`, `streaming`, `completed`, `failed`, `cancelled` |
| 주요 이벤트 | `graph_started`, `supervisor_plan`, `route_validated`, `worker_result`, `answer_delta`, `completed`, `failed` |
| 비책임 | Supervisor prompt, Route Node 보안 정책 세부 구현, Worker 검색 알고리즘 |

---

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| AGENT-CORE-B-201 | agent 시작/완료 이벤트 발행 | Backend | Phase 1 |
| AGENT-CORE-B-202 | completed/failed 후 cleanup | Backend | Phase 1 |
| AGENT-CORE-B-203 | agent 실행 시간 측정 | Backend | Phase 1 |
| AGENT-CORE-B-204 | agent 실패 처리 | Backend | Phase 1 |
| AGENT-CORE-F-201 | ReportJsonResponse 필드 확정 | Frontend | Phase 1 |
| AGENT-CORE-B-205 | Error Recovery 시나리오 Decision Tree | Backend | Phase 2 |

---

## Phase 1

### AGENT-CORE-B-201: agent 시작/완료 이벤트 발행

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CORE |

**설명**

Agent run의 주요 전이를 이벤트로 발행합니다. 이벤트는 SSE 스트림, run 상태 API, frontend 타임라인에서 동일하게 해석되어야 합니다.

**이벤트 계약**

| 이벤트 | 발행 주체 | 설명 |
| --- | --- | --- |
| `graph_started` | `chat/service.py` | LangGraph 실행 시작 |
| `supervisor_plan` | `agent_graph/agents/supervisor_agent.py` | worker 선택 및 접근 계획 생성 |
| `route_validated` | `agent_graph/nodes/route_node.py` | 계획 schema와 path allowlist 검증 완료 |
| `worker_started` | 각 worker wrapper | worker 실행 시작 |
| `worker_result` | 각 worker wrapper | 원본 근거가 `worker_results`에 append됨 |
| `evidence_compacted` | `agent_graph/nodes/evidence_node.py` | evidence 압축 완료 |
| `answer_delta` | `chat/final_answer_agent.py` | 최종 답변 토큰 조각 |
| `completed` | `chat/service.py` | 정상 종료 |
| `failed` | `chat/service.py` | 실패 종료 |
| `cancelled` | `chat/service.py` | 취소 종료 |

**완료 조건**

- 모든 이벤트에는 `runId`, `timestamp`, `sequence`가 포함됩니다.
- `failed`, `cancelled`, `completed`는 terminal event입니다.
- terminal event 이후 동일 run에 추가 이벤트를 발행하지 않습니다.

### AGENT-CORE-B-202: completed/failed 후 cleanup

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CORE |

**설명**

Final event 이후 event queue, cancel token, 임시 compact context, worker task handle을 정리합니다. 단, run 상태 요약과 evidence metadata는 조회 가능해야 하므로 즉시 삭제하지 않습니다.

**정리 대상**

| 대상 | 정책 |
| --- | --- |
| SSE event queue | terminal event 발행 후 TTL 기반 정리 |
| worker task handle | 완료/취소 후 해제 |
| cancel token | terminal state 전환 후 해제 |
| raw snippet cache | 정책에 따라 TTL 적용 |
| run summary | 상태 조회와 감사용으로 보존 |

### AGENT-CORE-B-203: agent 실행 시간 측정

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CORE |

**설명**

각 node와 worker의 시작/종료 시각, latency, timeout 여부를 기록합니다. 단순 총 실행 시간뿐 아니라 병렬 worker별 소요 시간을 확인할 수 있어야 합니다.

**필수 측정값**

| 필드 | 설명 |
| --- | --- |
| `durations.supervisor` | Supervisor plan 생성 시간 |
| `durations.route_node` | Route Node 검증 시간 |
| `durations.search_worker` | Search Worker 실행 시간 |
| `durations.dir_worker` | Dir Worker 실행 시간 |
| `durations.grep_worker` | Grep Worker 실행 시간 |
| `durations.read_worker` | Read Worker 실행 시간 |
| `durations.evidence_node` | Evidence compact 시간 |
| `durations.final_answer` | 최종 답변 생성 시간 |
| `elapsedSeconds` | run 전체 체감 시간 |

### AGENT-CORE-B-204: agent 실패 처리

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CORE |

**설명**

실패 node/worker와 error code를 구조화하여 저장하고, 가능한 경우 이미 수집된 evidence를 기반으로 fallback 답변을 생성할 수 있게 합니다.

**실패 분류**

| Error Code | 설명 |
| --- | --- |
| `INVALID_CHAT_REQUEST` | 질문, 옵션, path 입력 검증 실패 |
| `REPO_NOT_ANALYZED` | agent 실행 전 repo 분석/인덱싱 미완료 |
| `AGENT_RUN_CREATE_FAILED` | run 생성 실패 |
| `AGENT_STREAM_FAILED` | SSE stream 초기화/전송 실패 |
| `AGENT_ROUTE_BLOCKED` | Route Node가 위험 path 또는 worker 계획 차단 |
| `AGENT_WORKER_FAILED` | worker 실행 실패 |
| `AGENT_EVIDENCE_NOT_FOUND` | 답변 가능한 evidence 없음 |
| `AGENT_REASONING_FAILED` | Code Reasoning Worker 실행 실패 |

**완료 조건**

- `failedNode`, `failedWorker`, `errorCode`, `message`, `partialEvidenceCount`를 저장합니다.
- 사용자에게는 안전한 메시지를 반환하고 내부 stack trace는 노출하지 않습니다.
- path traversal, secret file 접근 시도는 `failed`가 아니라 policy block으로 분류할 수 있습니다.

### AGENT-CORE-F-201: ReportJsonResponse 필드 확정

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | CORE |

**설명**

프로젝트 분석 리포트의 공통 JSON 계약입니다. Agent Chat의 run 계약과 혼동하지 않도록 `ReportJsonResponse`는 repo 분석 결과 화면에만 사용합니다.

**필수 필드**

| 필드 | 설명 |
| --- | --- |
| `summary` | 프로젝트 마스터 요약 |
| `stack` | 기술 스택 목록 |
| `file_map` | 파일 단위 코드 맵 |
| `recommendations` | 추천 읽기 순서와 작업 |
| `heatmap` | 위험도/복잡도 히트맵 |
| `durations` | repo 분석 pipeline 소요 시간 |
| `guide` | 온보딩 가이드북 Markdown |

---

## Run Lifecycle

```text
queued
-> running
-> streaming
-> completed

running
-> failed

running
-> cancelled

streaming
-> cancelled
```

| 전이 | 조건 |
| --- | --- |
| `queued -> running` | `chat/service.py`가 LangGraph 실행을 시작 |
| `running -> streaming` | Evidence compact 완료 후 Final Answer Agent 시작 |
| `streaming -> completed` | Final Answer가 종료되고 completed event 발행 |
| `running -> failed` | Supervisor/Route/Worker/Evidence 단계에서 복구 불가 실패 |
| `running -> cancelled` | 사용자 취소 또는 timeout |

---

## 운영 원칙

| 원칙 | 내용 |
| --- | --- |
| Terminal event 단일성 | 하나의 run에는 하나의 terminal event만 존재합니다. |
| Evidence 보존 | 실패해도 이미 수집된 `worker_results` metadata는 조회 가능해야 합니다. |
| 비밀 보호 | 에러 detail에 secret 값, 토큰, private path를 노출하지 않습니다. |
| 사용자 표시 메시지 분리 | 내부 debug detail과 사용자 메시지를 분리합니다. |

---

## Phase 2

### AGENT-CORE-B-205: Error Recovery 시나리오 Decision Tree

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CORE |

**설명**

실패 유형별 복구 경로를 Decision Tree 형태로 정의합니다. Phase 1의 단순 에러 코드 목록을 넘어서, 다양한 실패 시나리오에서 업무가 어떻게 처리되는지 코드로 담습니다.
_(레퍼런스: Cicada, ChatRepos AI 프로젝트)_

**Recovery Decision Tree**

```text
실패 발생
└── Supervisor 실패?
│   ├── YES → [AGENT_RUN_FAILED] 터미널 이벤트, partial evidence 0건
│   └── NO  → 다음 단계
└── Route Node 보안 로직 차단?
    ├── YES → [AGENT_ROUTE_BLOCKED] 로그 남기고 무해한 메시지만 사용자에게
    └── NO  → Worker 실패
        ├── 일부 Worker 실패?
        │   ├── partial evidence 있음?
        │   │   ├── YES → [PARTIAL_EVIDENCE_CONTINUE] Evidence Aggregator 진입
        │   │   └── NO  → [AGENT_EVIDENCE_NOT_FOUND] 다음
        │   └── 모든 Worker 실패 → [AGENT_WORKER_FAILED] 다음
        └── Evidence Aggregator 실패?
            ├── YES → [AGENT_EVIDENCE_NOT_FOUND] raw evidence metadata는 보존
            └── NO  → Final Answer Agent 실패?
                ├── YES → [AGENT_STREAM_FAILED] partial answer 있으면 기존 부분 반환
                └── NO  → [COMPLETED] 정상 종료
```

**시나리오별 처리 정의**

| 시나리오 | 정책 코드 | 사용자 메시지 | partial evidence 반환 |
| --- | --- | --- | --- |
| Supervisor 실패 | `AGENT_RUN_FAILED` | "요청 처리 중 오류가 발생했습니다" | ✕ |
| Route Node 보안 차단 | `AGENT_ROUTE_BLOCKED` | "사용 정책에 의해 접근이 제한되었습니다" | ✕ |
| 일부 Worker 실패 + partial evidence 있음 | `PARTIAL_EVIDENCE_CONTINUE` | "일부 검색을 완료하지 못했으나 찾은 근거로 답변합니다" | ● |
| 모든 Worker 실패 | `AGENT_WORKER_FAILED` | "코드를 검색하는 중 문제가 발생했습니다" | ✕ |
| Evidence 없음 | `AGENT_EVIDENCE_NOT_FOUND` | "관련 코드를 찾지 못했습니다" | raw metadata ○ |
| Final Answer 실패 | `AGENT_STREAM_FAILED` | "답변 생성 중 오류가 발생했습니다" | partial ○ |

**구현 요구사항**

- `PARTIAL_EVIDENCE_CONTINUE` 정책은 `chat/service.py`가 Evidence Aggregator 완료 시 충분한 evidence가 있는지 판단하여 관리
- `AGENT_ROUTE_BLOCKED`는 `failed` 상태가 아니라 `policy_blocked`로 별도 분류하는 것을 Phase 2에서 검토
- terminal event payload에 `recoveryScenario` 필드 추가하여 프론트가 적절한 UI를 표시할 수 있게 함
