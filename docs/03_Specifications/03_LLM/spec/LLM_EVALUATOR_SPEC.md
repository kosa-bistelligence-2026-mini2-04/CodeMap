# LLM EVALUATOR 기능 명세서

> **도메인**: Agent | **모듈**: LLM-EVALUATOR | **최종 업데이트**: 2026-06-25

## 범위

`LLM-EVALUATOR`는 병렬 워커가 수집한 `worker_results`를 정제하여 Final Answer Agent가 소비할 **압축 근거 묶음(`compact_context`)**을 생성하는 노드입니다.

> **Phase 2 구현 현황**: 현재 구현은 중복 제거 + token budget 압축 후 `sufficient`, `missingInfo`, `nextPlanHint` 구조의 Evaluator 판단 DTO와 SSE 이벤트를 생성하고, 설정 가능한 반복 한도(`AGENT_MAX_REPLANS`, 기본 2회) 내에서 LangGraph re-plan 조건부 edge를 수행합니다.

| 구분 | 기준 |
| --- | --- |
| 구현 위치 | `backend/app/agent/nodes/evaluator_node.py` (`evaluator_node`) |
| 성격 | 결정론적 압축 노드 + Phase 2 Evaluator Judge 계약 |
| 책임 | `worker_results` 중복 제거, 파일 경로 그룹핑, token budget 내 `compact_context` 생성, 근거 충분성 판단 DTO 생성 |
| 비책임 | 최초 계획 수립(→ PLANNER), 직접적인 도구 실행(→ TOOL), 최종 사용자 답변 렌더링(→ Chat) |

---

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| LLM-EVALUATOR-B-201 | `worker_results` 중복 제거 및 파일 그룹핑 | Backend | Phase 1 |
| LLM-EVALUATOR-B-202 | token budget 내 `compact_context` 압축 생성 | Backend | Phase 1 |
| LLM-EVALUATOR-B-301 | 근거 충분성 판단 prompt/출력 스키마 및 re-plan 제어 결정 | Backend | Phase 2 |

---

## LLM-EVALUATOR-B-201: `worker_results` 중복 제거 및 파일 그룹핑

### 1. 설명
병렬 워커가 `operator.add`로 누적한 `worker_results`에서 중복을 제거하고 파일 경로 기준으로 그룹핑합니다.

### 2. 입/출력 규격
- **Input**: `worker_results: list[WorkerResult]`
- **중복 제거 키**: `(path, snippet[:200])` — 동일 파일 + 동일 스니펫 앞부분이면 중복으로 간주해 제거
- **그룹핑**: `path`가 있는 결과는 파일 경로별로 묶고, 경로 없는 결과(예: 시맨틱 검색)는 `no_path` 그룹으로 분리

### 3. 완료 조건
- 중복 제거 후 파일 경로 오름차순으로 정렬된 그룹이 구성된다.

---

## LLM-EVALUATOR-B-202: token budget 내 `compact_context` 압축 생성

### 1. 설명
Final Answer Agent의 컨텍스트 한도를 넘지 않도록 근거를 token budget 내로 압축한 `compact_context`를 생성합니다.

### 2. 입/출력 규격
- **Budget**: `_TOKEN_BUDGET = 12_000` (글자 수 기준, 1 token ≈ 4 chars)
- **압축 규칙**: 파일 그룹 순회하며 스니펫을 누적하다 예산 초과 시, 잔여 예산이 100자 초과면 잘라서 포함(`... (budget 초과로 잘림)`) 후 종료, 아니면 중단
- **Output**: State 갱신 `{ compact_context, events }`
  - `compact_context = { selectedEvidenceCount, tokenBudget, usedTokens(≈total_chars/4), groupedByFile }`
  - `groupedByFile[path] = [{id, lineStart, lineEnd, score, snippet, metadata}, ...]`
- **발행 이벤트**: `{"type": "evidence_compacted", "evidenceCount", "compactContextReady": true}`

### 3. 완료 조건
- `usedTokens`가 `tokenBudget`를 초과하지 않으며, 선택된 근거 수(`selectedEvidenceCount`)와 함께 `compact_context`가 반환된다.

---

## LLM-EVALUATOR-B-301: 근거 충분성 판단 prompt/출력 스키마 및 re-plan 제어 결정 (Phase 2)

### 1. 설명
누적된 근거가 사용자 질문에 답하기 충분한지 평가하기 위해 Evaluator Judge prompt와 구조화 출력 스키마를 정의합니다. 현재 노드는 API key가 없는 로컬/CI에서도 동작하도록 deterministic fallback 판단을 사용하며, 같은 DTO를 `evaluator_decision` 이벤트로 발행합니다. `sufficient=false`이고 `replan_count < max_replans`이면 `replan_started`를 발행하고 Planner로 되돌아갑니다. `max_replans`는 `AGENT_MAX_REPLANS` 설정값으로 결정하며, 잘못된 환경값으로 인한 과도한 반복을 막기 위해 0~3 범위로 제한합니다.

### 2. 입/출력 규격
- **Input**: `user_query`, `compact_context`
- **Prompt builder**: `build_evaluator_messages(user_query, compact_context)`
- **LLM factory**: `create_evaluator_llm()`
- **Output DTO**:

```json
{
  "sufficient": true,
  "missingInfo": [],
  "nextPlanHint": null,
  "reason": "파일 경로와 snippet 근거가 질문에 직접 대응합니다.",
  "confidence": 0.72
}
```

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `sufficient` | Boolean | 현재 근거만으로 답변 가능한지 여부 |
| `missingInfo` | String[] | 부족한 파일, 함수, 정책, 실행 흐름 등 추가 정보 |
| `nextPlanHint` | String \| null | Planner가 다음 탐색 계획에 사용할 힌트 |
| `reason` | String | 판단 근거 |
| `confidence` | Number | 0~1 범위의 판단 신뢰도 |

### 3. 발행 이벤트
- `evidence_compacted`: 기존 Phase 1 압축 완료 이벤트
- `evaluator_decision`: 위 DTO를 그대로 포함
- `replan_started`: `sufficient=false`이고 반복 한도 전일 때 `missingInfo`, `nextPlanHint`, `iteration`, `maxIterations`를 포함하여 발행

### 4. 완료 조건
- Evaluator 판단 DTO가 `compact_context.evaluatorDecision`과 State `evaluator_decision`에 기록된다.
- 프론트 타임라인에서 `evaluator_decision`, `replan_started`를 표시할 수 있다.
- LangGraph 조건부 edge가 반복 한도 내에서 Planner로 되돌아가고, 한도 도달 또는 `sufficient=true`일 때 종료한다.
- 반복 한도는 서비스 초기 state의 `max_replans`에 주입되며 기본값은 2회, 안전 상한은 3회다.
