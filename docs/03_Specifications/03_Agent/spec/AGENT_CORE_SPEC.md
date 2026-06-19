# AGENT CORE 기능 명세서

> **도메인**: AGENT | **모듈**: AGENT-CORE | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| AGENT-CORE-B-201 | agent 시작/완료 이벤트 발행 | Backend | Phase 1 |
| AGENT-CORE-B-202 | completed/failed 후 cleanup | Backend | Phase 1 |
| AGENT-CORE-B-203 | agent 실행 시간 측정 | Backend | Phase 1 |
| AGENT-CORE-B-204 | agent 실패 처리 | Backend | Phase 1 |
| AGENT-CORE-F-201 | ReportJsonResponse 필드 확정 | Frontend | Phase 1 |

---

## Phase 1

### AGENT-CORE-B-201: agent 시작/완료 이벤트 발행

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CORE |

**설명**

`agent_status`, `agent_completed`, `completed`, `failed` 이벤트를 publish. 각 LangGraph 노드 실행 전후에 이벤트를 발행하여 진행 상태를 실시간으로 전달.

**구현 노트**

- Redis pub/sub 또는 인메모리 큐 사용
- job_id 기반 채널 분리


### AGENT-CORE-B-202: completed/failed 후 cleanup

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CORE |

**설명**

final event (completed 또는 failed) 이후 이벤트 큐 정리. 리소스 누수 방지.

**구현 노트**

- 이벤트 큐 비우기
- 타임아웃 설정으로 미소비 이벤트 자동 삭제


### AGENT-CORE-B-203: agent 실행 시간 측정

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CORE |

**설명**

각 agent start/end timestamp 기록. 성능 모니터링 및 디버깅에 활용.

**구현 노트**

- 각 노드 실행 시작/종료 시간 기록
- 분석 리포트의 `durations` 필드에 포함


### AGENT-CORE-B-204: agent 실패 처리

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CORE |

**설명**

실패 agent 이름과 error message를 저장 및 failed event 발행. 클라이언트가 실패 원인을 파악할 수 있도록 구조화된 에러 정보 제공.

**구현 노트**

- `failed_agent`, `error_message`, `timestamp` 저장
- Frontend에서 실패 원인 표시 가능하도록 포맷 통일


### AGENT-CORE-F-201: ReportJsonResponse 필드 확정

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | CORE |

**설명**

`summary`, `stack`, `file_map`, `recommendations`, `heatmap`, `durations`, `guide` 포함. Frontend와 backend 간 report 응답 계약 고정.

**구현 노트**

- TypeScript 타입 정의로 계약 명시
- 모든 필드 nullable 처리하여 부분 완성 리포트 지원


