# AGENT CHAT 기능 명세서

> **도메인**: AGENT | **모듈**: AGENT-CHAT | **최종 업데이트**: 2026-06-23

## 범위

`AGENT-CHAT`은 사용자 질문을 받아 agent run을 만들고, `agent_graph/` 실행을 호출하며, Final Answer Agent와 SSE 스트리밍을 관리하는 Application Layer입니다.

이 문서의 구조는 최신 멀티에이전트 합의안을 기준으로 합니다.

| 구분 | 기준 |
| --- | --- |
| 구현 위치 | `backend/app/chat/` |
| 주요 파일 | `router.py`, `service.py`, `final_answer_agent.py` |
| 호출 대상 | `backend/app/agent_graph/graph.py` |
| 책임 | 요청 검증, run/session 관리, SSE 연결, 최종 답변 생성, frontend 이벤트 계약 |
| 비책임 | repo 파일 직접 읽기, path allowlist 검증, worker tool 실행 |

`Final Answer Agent`는 LangGraph 데이터 수집 그래프 내부가 아니라 `chat/final_answer_agent.py`에 위치합니다. 이 agent는 `CodeMapState.worker_results`와 `compact_context`를 입력으로 받아 사용자에게 보여줄 최종 답변만 생성합니다.

---

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| AGENT-CHAT-B-101 | 멀티에이전트 채팅 실행 API | Backend | Phase 1 |
| AGENT-CHAT-B-201 | chat/service 실행 관리자 | Backend | Phase 1 |
| AGENT-CHAT-B-202 | Final Answer Agent | Backend | Phase 1 |
| AGENT-CHAT-B-203 | SSE 스트리밍 이벤트 제어 | Backend | Phase 1 |
| AGENT-CHAT-B-204 | run 상태 및 취소 제어 | Backend | Phase 1 |
| AGENT-CHAT-F-201 | AI 응답 UI | Frontend | Phase 1 |
| AGENT-CHAT-F-202 | agent run 상태 표시 | Frontend | Phase 1 |
| AGENT-CHAT-F-203 | 관련 근거 파일 표시 | Frontend | Phase 1 |
| AGENT-CHAT-F-204 | SSE 스트리밍 응답 처리 | Frontend | Phase 1 |
| AGENT-CHAT-F-205 | 답변 스트리밍 UI | Frontend | Phase 1 |
| AGENT-CHAT-F-206 | 질문 입력 및 run 생성 | Frontend | Phase 1 |

---

## 실행 흐름

```text
User
-> frontend chat UI
-> POST /api/chat/{repo_id}/runs
-> chat/router.py
-> chat/service.py
-> agent_graph/graph.py
-> CodeMapState 반환
-> chat/final_answer_agent.py
-> GET /api/chat/{repo_id}/runs/{run_id}/stream
-> User
```

### 계층별 책임

| 계층 | 책임 | 산출물 |
| --- | --- | --- |
| `chat/router.py` | HTTP 요청/응답, path/body 검증, SSE endpoint 노출 | run 생성 응답, stream 응답 |
| `chat/service.py` | run/session 상태 저장, LangGraph 호출, 이벤트 큐 관리 | run state, stream URL |
| `agent_graph/graph.py` | Supervisor/Route/Worker/Evidence 실행 | `CodeMapState` |
| `chat/final_answer_agent.py` | 원본 근거 기반 최종 답변 생성 | answer delta, final answer |
| frontend chat UI | run 생성, 단계 상태 표시, evidence 패널, 답변 렌더링 | 사용자 화면 |

---

## Phase 1 Backend

### AGENT-CHAT-B-101: 멀티에이전트 채팅 실행 API

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CHAT |
| Endpoint | `POST /api/chat/{repo_id}/runs` |

**설명**

사용자 질문을 받아 agent run을 생성합니다. API는 답변 본문을 직접 반환하지 않고 `runId`, `sessionId`, `status`, `streamUrl`을 반환합니다. 실제 단계 진행과 답변 토큰은 SSE endpoint에서 전달합니다.

**구현 노트**

- 저장소 분석/임베딩 완료 여부를 먼저 확인합니다.
- 요청 body의 `question`, `mode`, `includeEvidence`, `maxToolCalls`, `timeoutSeconds`를 검증합니다.
- 생성 직후 상태는 `queued` 또는 `running`으로 저장합니다.
- `chat/service.py`가 LangGraph 실행을 비동기로 예약합니다.
- 동일 세션 내 연속 질문을 지원하기 위해 `sessionId`를 선택 입력으로 받을 수 있습니다.

**세션 연속성 구현 가이드 (Phase 1)** _(수업 실습: sec06 `agent_history_postgresql.py`)_

동일 세션 내에서 이전 질문/답변 맥락을 이어가는 연속 대화는 LangGraph의 `AsyncPostgresSaver` checkpointer를 활용합니다:

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# chat/service.py 또는 graph.py에서 graph compile 시 적용
checkpointer = AsyncPostgresSaver(psycopg_pool)
await checkpointer.setup()
compiled_graph = graph.compile(checkpointer=checkpointer)

# run 호출 시 sessionId를 thread_id로 전달
await compiled_graph.ainvoke(
    initial_state,
    config={"configurable": {"thread_id": session_id}}
)
```

- `sessionId`가 없으면 새 thread(신규 세션), 있으면 기존 checkpoint에서 이어서 실행
- Phase 1에서는 세션 내 연속성만 지원하며, 세션 간 장기 기억은 Phase 2에서 구현
- checkpointer는 `agent_graph/graph.py` compile 단계에서 주입하여 Application Layer와 분리 유지



**완료 조건**

- run 생성 응답에 `streamUrl`이 포함됩니다.
- repo가 분석되지 않은 경우 `REPO_NOT_ANALYZED`를 반환합니다.
- 질문이 비어 있거나 너무 긴 경우 `INVALID_CHAT_REQUEST`를 반환합니다.

### AGENT-CHAT-B-201: chat/service 실행 관리자

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CHAT |
| 구현 위치 | `backend/app/chat/service.py` |

**설명**

LangGraph 실행과 사용자-facing stream 사이의 조정자입니다. `chat/service.py`는 LangGraph 내부 node가 아니며, Application Layer에서 run 상태와 이벤트 큐를 관리합니다.

**구현 노트**

- run/session 저장소를 통해 상태를 `queued -> running -> streaming -> completed`로 전환합니다.
- LangGraph 실행 시작 전 `graph_started` 이벤트를 발행합니다.
- LangGraph 실행 결과인 `CodeMapState`를 Final Answer Agent에 전달합니다.
- timeout, cancel, failure 이벤트가 발생해도 가능한 근거를 보존합니다.

**완료 조건**

- run 단위로 상태 조회가 가능합니다.
- SSE 소비자가 늦게 연결되어도 최소한 현재 상태와 완료 이벤트를 회복할 수 있습니다.
- 실패 시 `failedNode`, `errorCode`, `partialEvidenceCount`가 기록됩니다.

### AGENT-CHAT-B-202: Final Answer Agent

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CHAT |
| 구현 위치 | `backend/app/chat/final_answer_agent.py` |

**설명**

`CodeMapState.worker_results`와 `compact_context`를 바탕으로 최종 답변을 생성하는 LLM agent입니다. 이 agent는 파일 시스템 도구를 직접 호출하지 않습니다.

**입력**

| 필드 | 설명 |
| --- | --- |
| `user_query` | 사용자 원본 질문 |
| `rewritten_query` | Supervisor가 보정한 검색 질의 |
| `worker_results` | Worker가 수집한 원본 근거 |
| `compact_context` | Evidence Aggregator가 압축한 근거 묶음 |
| `security_result` | Route Node 검증 결과 |

**출력**

| 필드 | 설명 |
| --- | --- |
| `answer_delta` | SSE로 흘려보낼 답변 토큰 조각 |
| `final_answer` | 완료된 최종 답변 |
| `citations` | 파일 경로, line range, evidence ID 목록 |

**완료 조건**

- 근거가 없는 경우 추측하지 않고 "근거 부족" 상태를 명시합니다.
- 답변에는 사용한 파일 경로와 line range가 포함됩니다.
- `worker_results` 원본 내용을 LLM 중간 요약만으로 대체하지 않습니다.

**System Prompt 설계 원칙**

Final Answer Agent의 system prompt는 다음 원칙을 반영하여 구성합니다.

| 원칙 | 설명 |
| --- | --- |
| Evidence-First | `compact_context.evidences`에 포함된 코드 스니펫과 파일 경로를 근거로 답변합니다. 근거 없는 추측, 학습 데이터 기반 답변을 금지합니다. |
| Citation 필수 | 답변에서 코드나 로직을 언급할 때 반드시 파일 경로와 line range를 명시합니다. 형식: `파일경로:L시작-L종료` |
| Raw Data 직접 참조 | Route Node나 중간 agent의 자연어 요약이 아니라, `worker_results`/`compact_context`의 원본 snippet을 직접 읽고 답변합니다. |
| 근거 부족 투명성 | `compact_context.status`가 `insufficient`이면 "찾을 수 있는 근거가 부족합니다"를 명시하고, 있는 근거만으로 부분 답변합니다. |
| 한국어 우선 | 사용자 질문이 한국어이면 한국어로 답변합니다. 코드 용어와 파일 경로는 원문 그대로 표기합니다. |
| 도구 미보유 | Final Answer Agent는 파일 시스템, 검색, grep 등 도구를 직접 호출하지 않습니다. 추가 검색이 필요하면 사용자에게 후속 질문을 제안합니다. |

**답변 포맷 가이드**

| 요소 | 규칙 |
| --- | --- |
| 코드 블록 | 관련 코드 snippet을 Markdown fenced code block으로 포함하고, 언어 태그와 파일 경로를 명시합니다. |
| 파일 경로 | repo 내부 상대 경로로 표기합니다. 예: `backend/app/chat/router.py:L42-L58` |
| 구조 설명 | 함수 호출 흐름이나 import 관계를 설명할 때 순서 목록을 사용합니다. |
| 복수 파일 | 여러 파일이 관련되면 파일별로 섹션을 나누어 설명합니다. |
| citation 목록 | 답변 말미에 `📎 참조 파일` 섹션으로 사용된 evidence의 파일 경로, line range, evidence ID를 목록으로 정리합니다. |

**근거 부족 시 응답 전략**

| 상황 | 응답 |
| --- | --- |
| evidence 0건 | "요청하신 내용과 관련된 코드를 찾지 못했습니다. 다른 키워드로 다시 질문해 주세요." |
| evidence 1~2건, 낮은 score | 있는 근거로 부분 답변 후 "추가 검색이 필요할 수 있습니다"를 안내합니다. |
| `security_result`에 blocked path 존재 | "일부 경로는 보안 정책에 의해 접근이 제한되었습니다"를 답변에 포함합니다. |

### AGENT-CHAT-B-203: SSE 스트리밍 이벤트 제어

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CHAT |
| Endpoint | `GET /api/chat/{repo_id}/runs/{run_id}/stream` |

**설명**

LangGraph 실행 단계와 Final Answer 토큰을 SSE로 전달합니다. 이벤트 이름은 `AGENT_CORE` 이벤트 명세와 공유합니다.

**필수 이벤트**

| 이벤트 | 설명 |
| --- | --- |
| `graph_started` | LangGraph 실행 시작 |
| `supervisor_plan` | Supervisor 계획 생성 완료 |
| `route_validated` | Route Node 보안 검증 완료 |
| `worker_started` | Worker 실행 시작 |
| `worker_result` | Worker 결과가 State에 기록됨 |
| `evidence_compacted` | Evidence Aggregator 처리 완료 |
| `answer_delta` | 최종 답변 토큰 조각 |
| `completed` | run 정상 완료 |
| `failed` | run 실패 |
| `cancelled` | 사용자 또는 timeout에 의해 취소 |

### AGENT-CHAT-B-204: run 상태 및 취소 제어

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CHAT |
| Endpoints | `GET /api/chat/{repo_id}/runs/{run_id}`, `POST /api/chat/{repo_id}/runs/{run_id}/cancel` |

**설명**

실행 중이거나 완료된 run의 현재 상태와 취소 요청을 처리합니다.

**상태값**

| 상태 | 설명 |
| --- | --- |
| `queued` | run 생성 후 실행 대기 |
| `running` | LangGraph 실행 중 |
| `streaming` | Final Answer 토큰 스트리밍 중 |
| `completed` | 정상 완료 |
| `failed` | 실패 |
| `cancelled` | 취소됨 |

---

## Phase 1 Frontend

### AGENT-CHAT-F-201: AI 응답 UI

답변 본문, 출처 파일, 근거 카드, 실패 상태를 한 화면에서 확인할 수 있는 UI입니다. Markdown 렌더링, 코드 블록, 파일 경로 표시를 지원합니다.

### AGENT-CHAT-F-202: agent run 상태 표시

Supervisor 계획, Route Node 검증, Worker 실행, Evidence 정리, Final Answer 단계를 각각 구분해서 표시합니다. 사용자는 "AI가 생각 중"이라는 추상 상태가 아니라 현재 실행 단계를 볼 수 있어야 합니다.

### AGENT-CHAT-F-203: 관련 근거 파일 표시

`worker_results` 기반 evidence 목록을 표시합니다. 각 항목은 worker 종류, 파일 경로, line range, score, snippet 표시 여부를 가집니다.

### AGENT-CHAT-F-204: SSE 스트리밍 응답 처리

SSE 이벤트를 수신하고 이벤트 타입별로 UI state를 갱신합니다. `answer_delta`는 답변 버퍼에 누적하고, worker/event류 메시지는 실행 타임라인에 누적합니다.

### AGENT-CHAT-F-205: 답변 스트리밍 UI

답변 토큰을 실시간으로 표시하고 완료 후 복사, 근거 열기, 다시 질문 액션을 활성화합니다.

### AGENT-CHAT-F-206: 질문 입력 및 run 생성

사용자 질문, mode, includeEvidence 옵션을 API 요청으로 전달합니다. 전송 중 중복 제출을 방지하고, 취소 버튼을 제공합니다.

---

## 비기능 요구사항

| 항목 | 기준 |
| --- | --- |
| 보안 | 사용자가 입력한 경로는 `Route Node` 검증 전까지 파일 접근에 사용하지 않습니다. |
| 지연 시간 | Worker는 가능한 병렬 실행하며 Final Answer는 compact context 준비 후 시작합니다. |
| 회복성 | SSE 연결이 끊겨도 run 상태 API로 현재 상태를 조회할 수 있습니다. |
| 근거성 | 최종 답변은 evidence ID와 파일 line range를 추적 가능해야 합니다. |
| 구현 경계 | `chat/`은 orchestration layer이며 repo I/O worker 구현을 포함하지 않습니다. |
