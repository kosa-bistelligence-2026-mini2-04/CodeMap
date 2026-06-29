# LLM AGENT 기능 명세서 (통합본)

> **도메인**: Agent | **모듈**: LLM-AGENT | **최종 업데이트**: 2026-06-25

본 문서는 LangGraph 기반 `Agent` 도메인의 **단일 진실 공급원(SSOT)** 설계 명세서로, 기존 `AGENT_GRAPH` · `AGENT_MEMORY_EXTENSION` · `AGENT_CORE`(→ **LLM-OPS** 운영 관심사) 명세와 `AGENT_SUPERVISOR_ROUTE`의 **라우팅/보안** 부분을 통합한다.

> 세부 책임은 다음 문서로 분리한다:
> - 계획 수립(Planner) → [`LLM_PLANNER_SPEC.md`](./LLM_PLANNER_SPEC.md)
> - 근거 충분성 평가(Evaluator) → [`LLM_EVALUATOR_SPEC.md`](./LLM_EVALUATOR_SPEC.md)
> - 도구 실행(Tool/Worker) → [`LLM_TOOL_SPEC.md`](./LLM_TOOL_SPEC.md)

---

## 1. 범위

`LLM-AGENT`는 코드베이스 탐색의 **흐름 제어**를 담당한다: 공유 상태(State) 정의, LangGraph 워크플로우 구성, 보안 검증 및 병렬 워커 fan-out, 실행 추적 이벤트 발행.

| 구분 | 기준 |
| --- | --- |
| 구현 위치 | `backend/app/agent/` (`state.py`, `graph.py`, `service.py`, `llm_client.py`, `nodes/`, `workers/`) |
| 성격 | LangGraph 오케스트레이션 (LLM Planner + 결정론적 Dispatcher/Worker/Evaluator 혼합) |
| 책임 | `CodeMapState` 정의, `StateGraph` 구성, `dispatcher_node` 보안 검증·Send 병렬 fan-out, 실행 제어, Thought Trace 이벤트 발행 |
| 비책임 | 계획 수립 상세(→ PLANNER), 충분성 평가 상세(→ EVALUATOR), 도구 실행 상세(→ TOOL), 최종 답변 스트리밍/마크다운 렌더링(→ Chat 도메인) |

---

## 2. 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| LLM-AGENT-B-201 | `CodeMapState` 공유 상태 및 Reducer 정의 | Backend | Phase 1 |
| LLM-AGENT-B-202 | LangGraph `StateGraph` 구성 및 실행 흐름 | Backend | Phase 1 |
| LLM-AGENT-B-203 | `dispatcher_node` 보안 검증 및 Send 병렬 fan-out | Backend | Phase 1 |
| LLM-AGENT-B-204 | Thought Trace 이벤트 발행 (실시간 타임라인) | Backend | Phase 1 |
| LLM-AGENT-B-301 | LangGraph thread_id 기반 멀티턴 상태 영속 | Backend | Phase 2 |
| LLM-AGENT-B-302 | 장기 기억(Long-term Memory) 및 외부 MCP 도구 확장 | Backend | Phase 2 |

---

## LLM-AGENT-B-201: `CodeMapState` 공유 상태 및 Reducer 정의

### 1. 설명
모든 노드·워커가 읽고 쓰는 LangGraph 공유 상태(`backend/app/agent/state.py`). **중간 요약 없이 원본 근거를 `worker_results`에 그대로 누적**하여 정보 유실을 방지하고, Final Answer Agent가 원본 근거를 직접 참조한다.

### 2. 입/출력 규격
- **`CodeMapState` (TypedDict)**
  - 입력: `user_query`, `repo_id`, `clone_path`, `run_id`
  - Planner 출력: `rewritten_query`, `access_plan: list[AccessPlanItem]`
  - Dispatcher 출력: `security_result: SecurityResult` (`{approved, rejected}`), `attempted_signatures: NotRequired[Annotated[set[tuple[str, str]], operator.or_]]`
  - Worker 출력(fan-in): `worker_results: Annotated[list[WorkerResult], operator.add]`, `events: Annotated[list[dict], operator.add]`, `errors: list[str]`, `durations: dict`
  - Evaluator 출력: `compact_context: dict`
  - 최종: `final_answer: str | None`
  - 내부: `_plan_item: AccessPlanItem | None` (Send fan-out 시 워커에 전달되는 개별 계획)
- **`WorkerResult` (DTO)**: `id`, `path`, `lineStart`, `lineEnd`, `score`, `snippet`, `metadata`
- **`AccessPlanItem` (DTO)**: `tool`("search"|"dir"|"grep"|"read"), `path`, `query`, `scope`("chunk"|"file"|"directory")

### 3. 완료 조건
- `worker_results`·`events`는 `Annotated[..., operator.add]` 리듀서로 선언되어 병렬 워커 결과가 순서 유실 없이 자동 병합(fan-in)된다.
- 각 노드는 부분 dict만 반환해 해당 채널만 갱신한다.

---

## LLM-AGENT-B-202: LangGraph `StateGraph` 구성 및 실행 흐름

### 1. 설명
`backend/app/agent/graph.py`의 `build_graph()`가 `StateGraph(CodeMapState)`를 구성하고, 모듈 로드 시 `compiled_graph = build_graph().compile()` 싱글톤으로 컴파일한다.

### 2. 입/출력 규격
- **실행 흐름**
  ```text
  START → planner_node → dispatcher_node ──(conditional: fanout_to_workers)──► search_worker
                                                                               ► dir_worker     ┐
                                                                               ► grep_worker    ├─► evaluator_node → END
                                                                               ► read_worker    ┘
  ```
- **엣지 구성**: `set_entry_point("planner_node")` → `add_edge("planner_node","dispatcher_node")` → `add_conditional_edges("dispatcher_node", fanout_to_workers, [4개 워커 + "evaluator_node"])` → 각 워커 `add_edge(worker,"evaluator_node")` → `add_edge("evaluator_node", END)`.
- **반환**: 그래프 실행 후 State의 `compact_context`·`worker_results`를 Chat 도메인(`chat/service.py`)이 읽어 Final Answer Agent에 전달.

### 3. 완료 조건
- `dispatcher_node`는 상태(`security_result`)만 갱신하고, 실제 라우팅은 conditional edge 함수 `fanout_to_workers`가 `Send` 리스트를 반환해 수행한다(노드가 상태 갱신과 Send를 동시 반환하면 `InvalidUpdateError` 발생 — 분리 필수).
- 승인 plan이 0건이면 `fanout_to_workers`는 `evaluator_node`로 직행하는 단일 `Send`를 반환한다.

---

## LLM-AGENT-B-203: `dispatcher_node` 보안 검증 및 Send 병렬 fan-out

### 1. 설명
`backend/app/agent/nodes/dispatcher_node.py` — **100% 결정론적**(LLM 아님). Planner의 `access_plan` 각 항목 경로를 보안 검증해 `security_result`로 분류하고, `fanout_to_workers`가 승인 항목을 `Send(f"{tool}_worker", {**state, "_plan_item": item})`로 병렬 fan-out 한다.

### 2. 입/출력 규격
- **Input**: `access_plan: list[AccessPlanItem]`
- **Output**: `{"security_result": {"approved": [...], "rejected": [...]}, "events": [{"type":"route_validated", ...}]}`
- **보안 규칙 (`_is_safe_path`) — 현재 구현**:
  - `path` 없음(search 도구) → 안전 통과
  - 절대 경로(`/` 시작) 또는 `..` 상위 탐색 → **차단**
  - 민감 파일 패턴 정규식(`.env`, `id_rsa`, `id_ed25519`, `.pem`, `.key`, `.p12`, `.pfx`, `secret`, `password`, `credential`, 대소문자 무관) → **차단**
  - 허용 확장자 집합(`_ALLOWED_EXTENSIONS`) 밖의 확장자 → **차단**

### 3. 완료 조건
- 거부 항목은 `logger.warning`으로 기록하고 `rejected`에 분류하며, 사용자에게는 무해하게 제외 처리한다.
- `_is_safe_path`는 절대경로·`..`·민감 파일 패턴·허용 확장자를 모두 검증한다.

---

## LLM-AGENT-B-204: Thought Trace 이벤트 발행

### 1. 설명
프론트엔드 실시간 타임라인(Exploration Timeline) 렌더링을 위해 그래프 진행 단계마다 이벤트를 `events` 채널에 누적·발행한다.

### 2. 입/출력 규격
- **Agent 그래프 내부 이벤트** (각 노드/워커가 `events` 채널에 누적):
  - `planner_plan` — Planner Node가 `access_plan` 수립 완료
  - `route_validated` — `dispatcher_node` 보안 검증 결과. 이벤트명은 기존 프론트 호환을 위해 유지
  - `worker_started` — 개별 워커 실행 시작
  - `worker_result` — 개별 워커 근거 수집
  - `evidence_compacted` — Evaluator 압축/충분성 평가 완료
  - `evaluator_decision` — Evaluator의 `sufficient/missingInfo/nextPlanHint` 판단 결과
  - `replan_started` — 반복 한도 내 근거 부족 시 Planner가 참고할 추가 탐색 힌트 발행
- **Chat Application Layer 터미널 이벤트** (`chat/router.py`가 SSE stream에서 직접 발행):
  - `graph_started` — 그래프 실행 시작 (stream 핸들러 진입 시 발행)
  - `answer_delta` — Final Answer Agent 답변 토큰
  - `references` — 참조 파일 목록
  - `completed` — run 정상 완료
  - `failed` — run 실패
- 이전 legacy bridge 이벤트(`content`, `done`, `exploration` 등)는 제거되었으며, 프론트엔드는 Run stream 이벤트를 직접 수신한다.

### 3. 완료 조건
- 각 이벤트는 `{"type": ..., ...payload}` 형태로 `events`(operator.add) 채널에 누적되어 SSE로 스트리밍된다.
- 프론트 타임라인 연동은 위 발행 목록을 기준으로 한다. (`worker_completed` 등 세부 duration 이벤트는 후속 확장으로 둔다.)

---

## LLM-AGENT-B-301: LangGraph thread_id 기반 멀티턴 상태 영속 (Phase 2)

### 1. 설명
동일 세션 내 연속 대화에서 이전 탐색 맥락을 LangGraph 실행 입력과 `thread_id`에 연결한다.

### 2. 현황 및 입/출력 규격
- **현재 구현**: Chat 도메인 DB(`Conversation`/`ChatMessage`, `sessionId` 기준 — `chat/repository.py`)에서 최근 메시지를 복원해 `CodeMapState.memory_context`에 주입한다.
- **LangGraph 실행 config**: 사용자 `sessionId`를 `configurable.thread_id`로 전달한다. `sessionId`가 없으면 `run_id`를 thread_id로 사용한다.
- **Planner 입력**: `planner_node`는 `memory_context`를 LLM 입력 payload의 `sessionMemory`로 받아 후속 질문의 생략된 맥락을 보정한다.

### 3. 완료 조건
- 동일 `sessionId`로 새 run을 만들면 DB에 저장된 이전 user/assistant 메시지 요약이 agent state에 복원되어야 한다.
- LangGraph 실행 config의 `thread_id`가 동일 `sessionId`로 고정되어야 한다.

---

## LLM-AGENT-B-302: 장기 기억 및 외부 MCP 도구 확장 (Phase 2)

### 1. 설명
세션 경계를 넘는 재사용 지식과 외부 도구 바인딩.

### 2. 입/출력 규격 (Phase 2 목표)
- **장기 기억**: 최근 대화 메시지와 assistant reference 수를 `memory_context`로 요약해 Planner 입력으로 재사용한다.
- **외부 도구 Job**: `tool/router.py` HTTP 수신 엔드포인트를 통해 외부 Issue/문서 저장소 등을 워커로 바인딩(MCP-style I/O 인터페이스).

### 3. 완료 조건
- 후속 질문은 같은 `sessionId`의 이전 대화 요약을 Planner 입력에서 참조할 수 있어야 한다.
- 신규 외부 도구 확장은 `LLM_TOOL_SPEC.md`의 MCP-style Job 인터페이스를 통해 연결한다.

---

## 부록: 에러/복구 정책

- **일부 워커 실패**: 수집된 부분 근거가 존재하면 진행을 계속한다(`PARTIAL_EVIDENCE_CONTINUE`). 워커 예외는 `errors`에 누적하고 `failed`/`error` 이벤트로 표면화한다.
- **보안 차단**: `dispatcher_node`가 위반 경로를 `rejected`로 분류·로깅하고 조용히 제외한다(우회 시도에 대한 사용자 노출 에러코드는 현재 미정의 — 표준 에러코드 신설은 `ERROR_CODES.md` 후속 과제).
