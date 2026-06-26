# LLM PLANNER 기능 명세서

> **도메인**: Agent | **모듈**: LLM-PLANNER | **최종 업데이트**: 2026-06-25

## 범위

`LLM-PLANNER`(Planner)는 사용자 질문을 분석해 오타 교정·의도 보정한 쿼리(`rewritten_query`)와 탐색 도구 실행 계획(`access_plan`)을 도출하는 **LLM 계획 수립 노드**입니다. 로컬 I/O 도구는 직접 보유하지 않습니다(보안 원칙).

| 구분 | 기준 |
| --- | --- |
| 구현 위치 | `backend/app/agent/nodes/planner_node.py` (`planner_node`) |
| LLM factory | `backend/app/agent/llm_client.py` (`create_planner_llm`) |
| 성격 | LLM-powered LangGraph node (`settings.OPENAI_MODEL`, `temperature=0`) |
| 책임 | 사용자 의도 분석, 쿼리 재작성, 초기 도구 실행 계획(`access_plan`) 수립 |
| 비책임 | 직접적인 파일 I/O 도구 실행, 경로 보안 검증(→ `dispatcher_node`/LLM-AGENT), 결과 충분성 평가(→ LLM-EVALUATOR) |

---

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| LLM-PLANNER-B-201 | Planner Node 계획 수립 (`access_plan` 생성) | Backend | Phase 1 |
| LLM-PLANNER-B-202 | LLM 응답 파싱 실패 시 휴리스틱 폴백 | Backend | Phase 1 |
| LLM-PLANNER-B-301 | 재계획(re-plan) 피드백 반영 | Backend | Phase 2 |

---

## LLM-PLANNER-B-201: Planner Node 계획 수립

### 1. 설명
사용자 질문을 LLM으로 분석하여 `rewritten_query`(오타 교정·의도 보정)와 어떤 도구를 어떤 경로에 실행할지 구조화한 `access_plan`을 수립합니다. 시스템 프롬프트는 **최대 4개** plan 항목, **상대 경로만 허용**(절대 경로·`../` 금지), **JSON만 출력**을 강제합니다.

### 2. 입/출력 규격
- **Input**: `user_query`(사용자 원본 질문)
  - `build_planner_messages(state)`가 최초 계획과 재계획 입력을 동일한 JSON payload로 구성한다.
- **Output**: State 갱신 `{ rewritten_query, access_plan, events }`
  - `access_plan: list[AccessPlanItem]`, 각 항목 `{tool: "search"|"dir"|"grep"|"read", path: str|null, query: str, scope: "chunk"|"file"|"directory"}`
  - LLM 원문에 ` ```json ` 코드블록이 있으면 제거 후 파싱
  - 예:
    ```json
    {
      "rewritten_query": "database connection pool",
      "access_plan": [
        { "tool": "search", "path": null, "query": "database pool config", "scope": "chunk" },
        { "tool": "grep", "path": "backend/app/infra", "query": "connection", "scope": "file" }
      ]
    }
    ```
- **발행 이벤트**: `{"type": "planner_plan", "rewrittenQuery", "selectedWorkers", "allowedPaths"}`

### 3. 완료 조건
- 수립된 plan은 위 JSON 스키마(`AccessPlanItem`)를 충족하고, 경로는 저장소 내 상대 경로만 사용한다.
- `selectedWorkers`/`allowedPaths`는 plan에서 도출하여 이벤트로 노출한다.

---

## LLM-PLANNER-B-202: LLM 응답 파싱 실패 시 휴리스틱 폴백

### 1. 설명
LLM 호출·JSON 파싱이 실패해도 그래프가 중단되지 않도록, 안전한 기본 계획으로 폴백합니다.

### 2. 입/출력 규격
- **트리거**: `llm.ainvoke` 예외 또는 `json.loads` 실패
- **폴백 plan**: `rewritten_query = user_query`, `access_plan = [{tool:"search", path:null, query:user_query, scope:"chunk"}]`

### 3. 완료 조건
- 폴백 시에도 `dispatcher_node` → 워커 fan-out이 정상 동작하도록 유효한 `access_plan`을 반환한다.
- 파싱 실패는 `logger.warning`으로 기록한다.

---

## LLM-PLANNER-B-301: 재계획(re-plan) 피드백 반영 (Phase 2)

### 1. 설명
LLM-EVALUATOR가 근거 부족으로 `re-plan`을 결정한 경우, 그 피드백을 입력으로 받아 추가 탐색 계획을 재수립합니다.

### 2. 입/출력 규격 (Phase 2 목표)
- **Input**: `user_query`, `replan_hint`, `replan_count`, 직전 `access_plan`, 직전 `worker_results` 요약, Evaluator의 `missingInfo`/`nextPlanHint`/`reason`
- **Output**: 보강된 `access_plan`(중복 탐색 회피)
- **현황**: `planner_node`는 `build_planner_messages(state)`를 통해 최초 계획과 재계획을 같은 LLM 호출 경로로 처리한다. 재계획 입력이 있으면 system prompt가 이전 plan/evidence와 중복되는 탐색을 피하고 부족 정보에 직접 대응하도록 지시한다.

### 3. 완료 조건
- Evaluator `re-plan` → Planner 재진입 루프가 최대 반복 한도 내에서 수렴해야 한다.
- Planner prompt에는 직전 raw snippet 전체가 아니라 path/worker/tool/query 요약만 포함되어 토큰 낭비와 민감정보 노출 위험을 줄인다.
