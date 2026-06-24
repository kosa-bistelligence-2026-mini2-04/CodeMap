# LLM PLANNER 기능 명세서

> **도메인**: Agent | **모듈**: LLM-PLANNER | **최종 업데이트**: 2026-06-24

## 범위

`LLM-PLANNER`는 사용자 질문과 대화 맥락을 기반으로 탐색해야 할 도구 및 대상 디렉토리를 식별하여 최초의 실행 계획 목록을 도출하는 계획 수립 에이전트입니다.

| 구분 | 기준 |
| --- | --- |
| 구현 위치 | `backend/app/agent/agents/supervisor_agent.py` |
| 성격 | LLM Agent |
| 책임 | 사용자 의도 분석, 쿼리 재작성, 초기 도구 실행 계획 수립 |
| 비책임 | 직접적인 파일 I/O 도구 실행, 보안 검증, 결과 충분성 평가 |

---

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| LLM-PLANNER-B-201 | Planner Agent 계획 수립 | Backend | Phase 1 |

---

## LLM-PLANNER-B-201: Planner Agent 계획 수립

### 1. 설명
사용자 질문을 분석하여 어떤 도구를 어떤 경로에 대해 실행할지 구조화된 계획(`access_plan`)을 수립합니다.

### 2. 입/출력 규격
- **Input**:
  - `user_query`: 사용자 원본 질문
  - `repo_summary`: 저장소 요약 및 주요 기술 스택
- **Output**: JSON 포맷의 초기 실행 플랜 `access_plan: list[dict]`
  - 예:
    ```json
    {
      "rewritten_query": "database connection pool",
      "access_plan": [
        {
          "tool": "search",
          "path": null,
          "query": "database pool config",
          "scope": "chunk"
        },
        {
          "tool": "grep",
          "path": "backend/app/infra",
          "query": "connection",
          "scope": "file"
        }
      ]
    }
    ```

### 3. 완료 조건
- 수립된 플랜은 JSON 스키마 규격을 충족해야 합니다.
- 경로 설정 시 상대 경로 형식을 엄격히 준수합니다.
