# AGENT GRAPH 기능 명세서

> **도메인**: AGENT | **모듈**: AGENT-GRAPH | **최종 업데이트**: 2026-06-23

## 범위

`AGENT-GRAPH`는 LangGraph 기반 데이터 수집 계층입니다. 사용자-facing HTTP/SSE 처리는 `chat/`에서 담당하고, 이 계층은 StateGraph 실행과 `CodeMapState` 갱신에 집중합니다.

| 구분 | 기준 |
| --- | --- |
| 구현 위치 | `backend/app/agent_graph/` |
| 주요 파일 | `state.py`, `graph.py` |
| 하위 구성 | `agents/`, `nodes/`, `tools/`, `workers/` |
| 책임 | State 정의, graph edge 구성, node 실행 순서, worker fan-out/fan-in |
| 비책임 | 최종 답변 스트리밍, HTTP request/response, frontend 표시 |

---

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| AGENT-GRAPH-B-201 | CodeMapState 스키마 정의 | Backend | Phase 1 |
| AGENT-GRAPH-B-202 | LangGraph workflow 정의 | Backend | Phase 1 |

---

## AGENT-GRAPH-B-201: CodeMapState 스키마 정의

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | GRAPH |
| 구현 위치 | `backend/app/agent_graph/state.py` |

**설명**

Supervisor, Route Node, Workers, Evidence Aggregator, Final Answer Agent가 공유하는 상태 구조입니다. Worker 결과는 중간 LLM 요약 없이 `worker_results`에 append-only로 기록합니다.

**핵심 필드**

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `run_id` | UUID/String | agent run 식별자 |
| `repo_id` | UUID/String | 대상 저장소 |
| `user_query` | String | 사용자 원본 질문 |
| `rewritten_query` | String | Supervisor가 정리한 검색 질의 |
| `access_plan` | Object | selectedWorkers, allowedPaths, riskLevel, searchHints |
| `security_result` | Object | Route Node 검증 결과 |
| `worker_results` | Array<Object> | Worker가 수집한 raw evidence |
| `compact_context` | Object | Evidence Aggregator가 압축한 답변용 근거 |
| `final_answer` | String/Null | Final Answer Agent가 생성한 최종 답변 |
| `events` | Array<Object> | graph 내부 실행 이벤트 |
| `durations` | Object | node/worker별 실행 시간 |
| `errors` | Array<Object> | 실패 또는 block 기록 |

**worker_results 항목**

| 필드 | 설명 |
| --- | --- |
| `id` | evidence ID |
| `worker` | `search`, `dir`, `grep`, `read`, `reasoning` |
| `path` | repo 내부 상대 경로 |
| `lineStart` | 시작 라인 |
| `lineEnd` | 종료 라인 |
| `score` | 검색/선정 점수 |
| `snippet` | 원본 코드 또는 텍스트 조각 |
| `metadata` | language, symbol, match type 등 |

**compact_context 스키마**

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `status` | String | `sufficient`, `insufficient`, `partial` |
| `totalEvidenceCount` | Integer | worker_results 전체 evidence 수 |
| `selectedEvidenceCount` | Integer | compact에 선택된 evidence 수 |
| `tokenBudget` | Integer | Final Answer Agent에 전달할 최대 토큰 수 |
| `usedTokens` | Integer | 실제 사용된 토큰 수 |
| `evidences` | Array\<Object\> | 정렬/중복제거/축약된 evidence 목록 |
| `evidences[].id` | String | 원본 evidence ID 참조 |
| `evidences[].worker` | String | 생성 worker |
| `evidences[].path` | String | 파일 경로 |
| `evidences[].lineStart` | Integer | 시작 라인 |
| `evidences[].lineEnd` | Integer | 종료 라인 |
| `evidences[].score` | Float | 정렬 점수 |
| `evidences[].snippet` | String | token budget 내 축약된 snippet |
| `evidences[].metadata` | Object | language, symbol 등 |
| `groupedByFile` | Object | 파일 경로별 evidence ID 그룹핑 |

> `compact_context.evidences`는 `worker_results`의 subset이며, 원본 `worker_results`는 별도 보존됩니다.

**완료 조건**

- 모든 worker 결과는 공통 evidence shape를 따릅니다.
- `worker_results` 원본은 Final Answer 전까지 손실 없이 보존됩니다.
- path 값은 repo 내부 상대 경로만 허용합니다.

---

## AGENT-GRAPH-B-202: LangGraph workflow 정의

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | GRAPH |
| 구현 위치 | `backend/app/agent_graph/graph.py` |

**설명**

Supervisor Agent, Route Node, Worker fan-out, Evidence Aggregator를 연결하는 StateGraph를 정의합니다.

**권장 흐름**

```text
START
-> supervisor_agent
-> route_node
-> parallel workers
   -> search_worker
   -> dir_worker
   -> grep_worker
   -> read_worker
   -> reasoning_worker(optional)
-> evidence_node
-> END
```

**Edge 규칙**

| Edge | 조건 |
| --- | --- |
| `START -> supervisor_agent` | run 입력 검증 완료 |
| `supervisor_agent -> route_node` | access_plan 생성 성공 |
| `route_node -> workers` | `security_result.allowed = true` |
| `route_node -> END` | policy block 또는 복구 불가 검증 실패 |
| `workers -> evidence_node` | 하나 이상의 worker 종료 |
| `evidence_node -> END` | compact_context 생성 완료 |

**병렬 실행 원칙**

- `Route Node`가 허용한 worker만 실행합니다.
- `dir`, `grep`, `search`는 병렬 실행할 수 있습니다.
- `read`는 후보 path가 있어야 하므로 `search`/`grep` 이후 또는 parallel branch 내부 conditional step으로 실행합니다.
- `reasoning_worker`는 Phase 1에서는 선택형이며 evidence가 충분할 때만 실행합니다.

**fan-out/fan-in 구현 패턴**

1. **권장 패턴: LangGraph `Send` API**
   - Route Node에서 허용된 worker 목록을 순회하며 `Send(worker_name, worker_input)` 반환
   - 각 worker는 독립 branch로 실행되어 결과를 State에 병합

2. **State 병합 전략: Annotated Reducer**
   ```python
   from typing import Annotated
   from operator import add

   class CodeMapState(TypedDict):
       worker_results: Annotated[list, add]  # 각 worker가 append
       events: Annotated[list, add]          # 각 node가 append
       # ... 기타 필드
   ```
   - `worker_results`와 `events`는 `Annotated[list, add]` reducer를 사용하여 병렬 worker 결과를 자동 병합
   - 단일 값 필드(`rewritten_query`, `access_plan` 등)는 마지막 write 우선(last-writer-wins)

3. **fan-in 조건**
   - 모든 허용된 worker가 완료되거나 timeout이 발생하면 Evidence Aggregator Node로 진입
   - 일부 worker 실패 시에도 partial evidence가 있으면 진행 (정책: `PARTIAL_EVIDENCE_CONTINUE`)

**완료 조건**

- graph 실행 결과는 `CodeMapState` 전체 또는 상태 요약을 반환합니다.
- graph 내부에서 최종 사용자 답변을 스트리밍하지 않습니다.
- `Final Answer Agent` 호출은 `chat/service.py`에서 수행합니다.

---

## 디렉토리 기준

```text
backend/app/agent_graph/
├── state.py
├── graph.py
├── agents/
│   └── supervisor_agent.py
├── nodes/
│   ├── route_node.py
│   └── evidence_node.py
├── tools/
│   ├── dir.py
│   ├── grep.py
│   ├── read.py
│   └── search.py
└── workers/
    ├── search_worker.py
    ├── dir_worker.py
    ├── grep_worker.py
    ├── read_worker.py
    └── reasoning_worker.py
```

---

## 비기능 요구사항

| 항목 | 기준 |
| --- | --- |
| 결정론적 보안 | path 검증과 worker allowlist는 LLM이 아니라 코드 node에서 수행합니다. |
| 정보 보존 | worker 간 자연어 relay를 금지하고 State에 raw evidence를 기록합니다. |
| 관측성 | 모든 node/worker는 duration과 event를 남깁니다. |
| 재실행성 | 같은 run 입력과 같은 repo index에서는 유사한 access plan과 evidence를 재현할 수 있어야 합니다. |
