# AGENT SEARCH 기능 명세서

> **도메인**: AGENT | **모듈**: AGENT-SEARCH | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase | 우선순위 |
| --- | --- | --- | --- | --- |
| AGENT-SEARCH-B-201 | 자가 교정 탐색 | Backend | Phase 2 |  |
| AGENT-SEARCH-B-202 | Repo Chat UI | Backend | Phase 2 |  |
| AGENT-SEARCH-B-203 | LLM 답변 생성 | Backend | Phase 2 |  |
| AGENT-SEARCH-B-204 | 에이전트 탐색 과정 표시 UI | Backend | Phase 2 |  |
| AGENT-SEARCH-B-205 | 에이전트 탐색 도구 정의 | Backend | Phase 2 |  |
| AGENT-SEARCH-B-206 | Service | Backend | Phase 2 | 에이전트가 인터넷 검색 등 외부 도구를 자율적으로 사용하는 로직 보류 |
| AGENT-SEARCH-B-207 | Service | Backend | Phase 2 | 단순 질의응답을 넘어서는 심층 추론 로직 보류 |

---

## Phase 2

### AGENT-SEARCH-B-201: 자가 교정 탐색

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | AGENT |
| 모듈명 | SEARCH |

**설명**

탐색 실패 시 최대 5회 재탐색


### AGENT-SEARCH-B-202: Repo Chat UI

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | AGENT |
| 모듈명 | SEARCH |

**설명**

사용자 질문 입력창 제공


### AGENT-SEARCH-B-203: LLM 답변 생성

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | AGENT |
| 모듈명 | SEARCH |

**설명**

프로젝트 맥락 기반 응답 생성


### AGENT-SEARCH-B-204: 에이전트 탐색 과정 표시 UI

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | AGENT |
| 모듈명 | SEARCH |

**설명**

에이전트가 현재 탐색 중인 파일·단계를 실시간으로 화면에 표시


### AGENT-SEARCH-B-205: 에이전트 탐색 도구 정의

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | AGENT |
| 모듈명 | SEARCH |

**설명**

에이전트가 호출할 코드 탐색 도구(grep 검색·파일 읽기·디렉토리 탐색) 정의 및 등록


### AGENT-SEARCH-B-206: Service

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | AGENT |
| 소분류 ID | SEARCH |
| 우선순위 | 에이전트가 인터넷 검색 등 외부 도구를 자율적으로 사용하는 로직 보류 |

**설명**

자율 외부 도구 사용


### AGENT-SEARCH-B-207: Service

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | AGENT |
| 소분류 ID | SEARCH |
| 우선순위 | 단순 질의응답을 넘어서는 심층 추론 로직 보류 |

**설명**

Advanced Reasoning


