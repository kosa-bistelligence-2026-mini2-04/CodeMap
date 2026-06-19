# AGENT CHAT 기능 명세서

> **도메인**: AGENT | **모듈**: AGENT-CHAT | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase | 우선순위 |
| --- | --- | --- | --- | --- |
| AGENT-CHAT-B-101 | Repo Chat API | Backend | Phase 1 |  |
| AGENT-CHAT-B-201 | 코드 컨텍스트 생성 | Backend | Phase 2 |  |
| AGENT-CHAT-B-202 | 출처 파일 반환 | Backend | Phase 2 |  |
| AGENT-CHAT-F-201 | AI 응답 UI | Frontend | Phase 2 |  |
| AGENT-CHAT-F-202 | 탐색 루프 횟수/시간 제한 | Frontend | Phase 2 |  |
| AGENT-CHAT-F-203 | 관련 파일 검색 | Frontend | Phase 2 |  |
| AGENT-CHAT-F-204 | 스트리밍 응답 처리 | Frontend | Phase 2 |  |
| AGENT-CHAT-F-205 | 답변 스트리밍 UI | Frontend | Phase 2 |  |
| AGENT-CHAT-F-206 | 질문 의도 분석 | Frontend | Phase 2 |  |
| AGENT-CHAT-B-203 | Service | Backend | Phase 2 | 사용자 세션 기반 지속적인 장기 기억 관리 로직 보류 |

---

## Phase 1

### AGENT-CHAT-B-101: Repo Chat API

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | AGENT |
| 모듈명 | CHAT |

**설명**

`POST /api/chat/{repo_id}`


---

## Phase 2

### AGENT-CHAT-B-201: 코드 컨텍스트 생성

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | AGENT |
| 모듈명 | CHAT |

**설명**

관련 파일을 묶어 LLM Context 구성


### AGENT-CHAT-B-202: 출처 파일 반환

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | AGENT |
| 모듈명 | CHAT |

**설명**

파일명 및 line 정보 제공


### AGENT-CHAT-F-201: AI 응답 UI

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | AGENT |
| 모듈명 | CHAT |

**설명**

답변 및 참조 파일명 표시


### AGENT-CHAT-F-202: 탐색 루프 횟수/시간 제한

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | AGENT |
| 모듈명 | CHAT |

**설명**

에이전트 도구 호출 최대 5회·처리 시간 최대 20초 제한, 초과 시 수집 정보 기반 최선 답변 반환


### AGENT-CHAT-F-203: 관련 파일 검색

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | AGENT |
| 모듈명 | CHAT |

**설명**

벡터 검색 기반 관련 코드 탐색


### AGENT-CHAT-F-204: 스트리밍 응답 처리

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | AGENT |
| 모듈명 | CHAT |

**설명**

FastAPI SSE(Server-Sent Events) 기반 LLM 응답 스트리밍 처리


### AGENT-CHAT-F-205: 답변 스트리밍 UI

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | AGENT |
| 모듈명 | CHAT |

**설명**

LLM 답변을 실시간 스트리밍으로 받아 타이핑 효과로 표시


### AGENT-CHAT-F-206: 질문 의도 분석

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | AGENT |
| 모듈명 | CHAT |

**설명**

자연어 질문 파싱


### AGENT-CHAT-B-203: Service

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | AGENT |
| 소분류 ID | CHAT |
| 우선순위 | 사용자 세션 기반 지속적인 장기 기억 관리 로직 보류 |

**설명**

장기 기억 (Long-term Memory)


