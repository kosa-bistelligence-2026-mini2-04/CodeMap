# LLM EVALUATOR 기능 명세서

> **도메인**: Agent | **모듈**: LLM-EVALUATOR | **최종 업데이트**: 2026-06-24

## 범위

`LLM-EVALUATOR`는 도구(`tool/service.py`)가 수행한 JSON 결과 데이터(`worker_results`)를 수집 및 분석하여 정보의 충분성을 평가하고 탐색의 종결(`commit`/`complete`) 혹은 추가 탐색(`re-plan`) 여부를 판단하는 검토 및 종결 에이전트입니다.

| 구분 | 기준 |
| --- | --- |
| 구현 위치 | `backend/app/agent/nodes/evidence_aggregator.py` |
| 성격 | LLM/Deterministic Agent |
| 책임 | 수집 데이터 충분성 평가, 종결 판단 및 commit 신호 발행 |
| 비책임 | 최초 계획 수립, 직접적인 도구 실행, 최종 사용자 답변 렌더링 |

---

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| LLM-EVALUATOR-B-201 | 수집 근거 충분성 평가 및 제어 결정 | Backend | Phase 1 |

---

## LLM-EVALUATOR-B-201: 수집 근거 충분성 평가 및 제어 결정

### 1. 설명
현재까지 탐색 완료되어 누적된 `worker_results`를 분석하여 사용자의 질문에 답변을 충분히 구성할 수 있는지 평가합니다.

### 2. 입/출력 규격
- **Input**:
  - `user_query`: 사용자 원본 질문
  - `worker_results`: 각 도구 워커가 수집하여 누적된 데이터 리스트
- **Output**: JSON 포맷의 제어 결정문
  - 예 (충분한 경우):
    ```json
    {
      "decision": "commit",
      "reason": "데이터베이스 풀 설정 정보가 auth.py와 database.py에서 충분히 확인되었습니다."
    }
    ```
  - 예 (부족하여 추가 탐색이 필요한 경우 - Phase 2 피드백 연동):
    ```json
    {
      "decision": "re-plan",
      "feedback": "auth 설정 파일은 찾았으나, config 모듈의 refresh 토큰 키를 아직 확인하지 못했습니다."
    }
    ```

### 3. 완료 조건
- 수집 근거의 유무 및 질을 정량적/정성적으로 판단하여 명확한 종결(commit) 판단 결과를 발행해야 합니다.
