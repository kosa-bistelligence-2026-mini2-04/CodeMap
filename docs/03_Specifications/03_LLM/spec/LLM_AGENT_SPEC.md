# LLM AGENT 기능 명세서 (통합본)

> **도메인**: Agent | **모듈**: LLM-AGENT | **최종 업데이트**: 2026-06-24

본 문서는 LangGraph 기반의 `Agent` 도메인 설계 표준 명세서로, 기존의 `LLM_GRAPH_SPEC.md`, `LLM_MEMORY_EXTENSION_SPEC.md`, `LLM_OPS_SPEC.md`를 통합하여 단일 진실 공급원(SSOT)으로 구성한 문서입니다.

---

## 1. 범위 및 아키텍처 개요

`LLM-AGENT`는 코드베이스 탐색 계획 수립(Planner), 흐름 제어(LangGraph 및 State 관리), 결과 검토(Evaluator)를 아우르는 에이전트의 실행 전반을 정의합니다.

| 구분 | 기준 |
| --- | --- |
| 구현 위치 | `backend/app/agent/` |
| 주요 파일 | `state.py`, `graph.py`, `service.py`, `llm_client.py` |
| 하위 구성 | `agents/`, `nodes/`, `workers/` |
| 책임 | 탐색 계획 수립, 상태(State) 정의, LangGraph 워크플로우 구성, 실행 제어 및 14개 Thought Trace 이벤트 발행 |
| 비책임 | 최종 사용자 답변 스트리밍 및 마크다운 렌더링 (Chat 도메인 영역) |

---

## 2. 공유 상태 및 Reducer (`CodeMapState`)

모든 에이전트 노드와 워커가 공유하고 업데이트하는 메모리 구조입니다.

### 1) CodeMapState 스키마
- `run_id`: 에이전트 실행 세션 식별자 (UUID)
- `repo_id`: 대상 프로젝트 저장소 식별자 (UUID)
- `user_query`: 사용자 원본 질문
- `rewritten_query`: 계획 수립 에이전트가 오타 교정 및 보정한 쿼리
- `access_plan`: 탐색용 도구 사용 계획 리스트
- `security_result`: 보안 검증 결과 (approved/rejected)
- `worker_results`: 각 도구가 수집한 코드 근거 데이터 리스트 (Reducer 병합)
- `compact_context`: 최종 답변 생성을 위해 압축/정제된 컨텍스트
- `events`: Thought Trace 스트리밍용 이벤트 버퍼 (Reducer 병합)
- `errors`: 에러 발생 이력 목록
- `durations`: 노드 및 워커별 실행 소요 시간 측정값

### 2) DTO 규격
- **WorkerResult (JSON Job 결과 규격)**:
  - `id`: 근거 고유 식별자 (UUID)
  - `path`: 파일 상대 경로
  - `lineStart`: 시작 줄 번호
  - `lineEnd`: 끝 줄 번호
  - `score`: 검색 정확도 점수
  - `snippet`: 수집된 소스코드 스니펫
  - `metadata`: 실행 도구 및 쿼리 정보

---

## 3. 워크플로우 그래프 구성 (LangGraph)

에이전트는 LangGraph의 `StateGraph`를 통해 비동기 상태 기동 및 병렬 워커 호출을 처리합니다.

### 1) 실행 흐름
```text
START
-> planner_agent (supervisor_node)
-> route_node
-> parallel workers (search, dir, grep, read)
-> evaluator_node (evidence_aggregator)
-> END
```

### 2) 병렬 실행 (fan-out/fan-in)
- **Send API**: `route_node`에서 보안allowlist 검증을 통과한 워커를 LangGraph `Send` API를 통해 동적으로 병렬 가동합니다.
- **Annotated Reducer**: 병렬 실행된 워커들이 반환한 `worker_results`와 `events`는 `operator.add` 리듀서를 통해 순서 유실 없이 하나의 리스트로 자동 취합(fan-in)됩니다.

---

## 4. 상태 영속성 및 대화 세션 관리

동일 세션 내 연속 대화를 구현하기 위해 `AsyncPostgresSaver` 체크포인터를 활용합니다.

- **Checkpointer 바인딩**: `app/agent/graph.py` 컴파일 단계에서 PostgreSQL 데이터베이스 커넥션 풀 기반의 체크포인터 세션을 주입하여 상태를 유지합니다.
- **세션 식별**: 채팅 기동 시 사용자가 제공한 `sessionId`를 LangGraph `thread_id`로 매핑하여 이전 질문 및 탐색 맥락을 지속적으로 유지합니다.

---

## 5. 실행 제어 및 Thought Trace 이벤트

### 1) 14개 Thought Trace 이벤트 규격
에이전트 구동 시작부터 완료까지 프론트엔드 실시간 타임라인 렌더링을 위해 다음 이벤트를 발행합니다.
1. `graph_started`
2. `planner_started`
3. `planner_plan_generated`
4. `route_validated`
5. `worker_dispatch`
6. `worker_started`
7. `worker_result`
8. `worker_completed`
9. `worker_failed`
10. `evaluator_started`
11. `evaluator_completed`
12. `completed` (터미널)
13. `failed` (터미널)
14. `cancelled` (터미널)

### 2) 에러 복구 시나리오 (Decision Tree)
도구 실행이나 분석 중 에외 발생 시 아래 복구 규칙을 적용합니다:
- **일부 워커 실패 시**: 수집된 부분 근거가 존재하면 진행을 계속하는 `PARTIAL_EVIDENCE_CONTINUE` 정책을 적용합니다.
- **보안 차단 발생 시**: `AGENT_ROUTE_BLOCKED` 오류 코드로 우회 시도를 차단하고 로그를 기록한 뒤 무해한 경고만 사용자에게 표출합니다.

---

## 6. Phase 2 확장 사양

- **장기 기억 (Long-term Memory)**: 세션 경계를 넘어서 자주 조회되는 핵심 모듈과 설계 가이드를 재사용할 수 있는 장기 기억 스토어 연동.
- **외부 MCP 도구 확장**: HTTP 수신 라우터(`tool/router.py`)를 통해 외부 Issue, API 문서 저장소 등을 워커로 바인딩.
