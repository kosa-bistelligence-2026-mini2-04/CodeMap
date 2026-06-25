# LLM EVALUATOR 기능 명세서

> **도메인**: Agent | **모듈**: LLM-EVALUATOR | **최종 업데이트**: 2026-06-24

## 범위

`LLM-EVALUATOR`는 병렬 워커가 수집한 `worker_results`를 정제하여 Final Answer Agent가 소비할 **압축 근거 묶음(`compact_context`)**을 생성하는 노드입니다.

> **Phase 1 현황**: 현재 구현은 **결정론적 코드 노드**(LLM 아님)로, 중복 제거 + token budget 압축만 수행합니다. 명칭상의 "충분성 평가 및 commit/re-plan 제어 결정"은 **Phase 2 구현 예정**입니다.

| 구분 | 기준 |
| --- | --- |
| 구현 위치 | `backend/app/agent/workers/evidence_aggregator.py` (`evidence_aggregator`) |
| 성격 | 결정론적 코드 노드 (Phase 1) → LLM 평가 에이전트 (Phase 2) |
| 책임 | `worker_results` 중복 제거, 파일 경로 그룹핑, token budget 내 `compact_context` 생성 |
| 비책임 | 최초 계획 수립(→ PLANNER), 직접적인 도구 실행(→ TOOL), 최종 사용자 답변 렌더링(→ Chat) |

---

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| LLM-EVALUATOR-B-201 | `worker_results` 중복 제거 및 파일 그룹핑 | Backend | Phase 1 |
| LLM-EVALUATOR-B-202 | token budget 내 `compact_context` 압축 생성 | Backend | Phase 1 |
| LLM-EVALUATOR-B-301 | LLM 근거 충분성 평가 및 commit/re-plan 제어 결정 | Backend | Phase 2 |

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

## LLM-EVALUATOR-B-301: LLM 근거 충분성 평가 및 commit/re-plan 제어 결정 (Phase 2)

### 1. 설명
누적된 근거가 사용자 질문에 답하기 충분한지 LLM으로 평가하여 탐색을 종결(`commit`)하거나 추가 탐색(`re-plan`)을 지시합니다. (자가 교정 루프)

### 2. 입/출력 규격 (Phase 2 목표)
- **Input**: `user_query`, `worker_results`(또는 `compact_context`)
- **Output**: 제어 결정 JSON
  - 충분: `{ "decision": "commit", "reason": "..." }`
  - 부족: `{ "decision": "re-plan", "feedback": "..." }` → LLM-PLANNER-B-301로 전달
- **현황**: 현재 노드는 결정론적 압축까지만 수행하며 commit/re-plan 판단은 미구현.

### 3. 완료 조건
- (Phase 2) `re-plan` 루프가 최대 반복 한도 내에서 수렴하고, `commit` 시 `compact_context`가 Final Answer로 전달되어야 한다.
