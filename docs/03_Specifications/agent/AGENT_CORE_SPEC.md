# AGENT CORE 기능 명세서

> **도메인**: AGENT | **모듈**: AGENT-CORE | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| AGENT-CORE-B-201 | agent 시작/완료 이벤트 발행 | Backend | Phase 2 |
| AGENT-CORE-B-202 | completed/failed 후 cleanup | Backend | Phase 2 |
| AGENT-CORE-B-203 | agent 실행 시간 측정 | Backend | Phase 2 |
| AGENT-CORE-B-204 | agent 실패 처리 | Backend | Phase 2 |
| AGENT-CORE-F-201 | ReportJsonResponse 필드 확정 | Frontend | Phase 2 |

---

## Phase 2

### AGENT-CORE-B-201: agent 시작/완료 이벤트 발행

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | AGENT |
| 모듈명 | CORE |

**설명**

agent_status, agent_completed, completed, failed 이벤트 publish


### AGENT-CORE-B-202: completed/failed 후 cleanup

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | AGENT |
| 모듈명 | CORE |

**설명**

final event 이후 queue 정리


### AGENT-CORE-B-203: agent 실행 시간 측정

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | AGENT |
| 모듈명 | CORE |

**설명**

각 agent start/end timestamp 기록


### AGENT-CORE-B-204: agent 실패 처리

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | AGENT |
| 모듈명 | CORE |

**설명**

실패 agent, error message 저장 및 failed event 발행


### AGENT-CORE-F-201: ReportJsonResponse 필드 확정

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | AGENT |
| 모듈명 | CORE |

**설명**

summary, stack, file_map, recommendations, heatmap, durations, guide 포함, frontend와 report 계약 고정


