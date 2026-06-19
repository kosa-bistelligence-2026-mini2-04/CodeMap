# AGENT SEARCH 기능 명세서

> **도메인**: AGENT | **모듈**: AGENT-SEARCH | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| AGENT-SEARCH-B-201 | 자가 교정 탐색 | Backend | Phase 1 |
| AGENT-SEARCH-B-202 | Repo Chat UI | Backend | Phase 1 |
| AGENT-SEARCH-B-203 | LLM 답변 생성 | Backend | Phase 1 |
| AGENT-SEARCH-B-204 | 에이전트 탐색 과정 표시 UI | Backend | Phase 1 |
| AGENT-SEARCH-B-205 | 에이전트 탐색 도구 정의 | Backend | Phase 1 |
| AGENT-SEARCH-B-206 | 자율 외부 도구 사용 | Backend | Phase 2 |
| AGENT-SEARCH-B-207 | Advanced Reasoning | Backend | Phase 2 |

---

## Phase 1

### AGENT-SEARCH-B-201: 자가 교정 탐색

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | SEARCH |

**설명**

탐색 실패 시 최대 5회 재탐색. 검색 결과가 불충분할 경우 쿼리를 변형하거나 다른 검색 전략으로 전환.

**구현 노트**

- LangGraph 반복 루프 구현
- 재탐색 시 쿼리 확장 또는 키워드 추출 전략 변경


### AGENT-SEARCH-B-202: Repo Chat UI

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | SEARCH |

**설명**

사용자 질문 입력창 제공. 질문 입력 후 전송 시 LangGraph 에이전트를 통해 RAG 기반 답변 생성.

**구현 노트**

- 엔터키 전송 지원
- 전송 중 입력창 비활성화


### AGENT-SEARCH-B-203: LLM 답변 생성

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | SEARCH |

**설명**

프로젝트 맥락 기반 응답 생성. 검색된 코드 청크를 컨텍스트로 활용하여 GPT-4o로 답변 생성.

**구현 노트**

- GPT-4o 사용
- 시스템 프롬프트: 코드베이스 전문가 역할
- 출처 파일 정보를 함께 반환


### AGENT-SEARCH-B-204: 에이전트 탐색 과정 표시 UI

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | SEARCH |

**설명**

에이전트가 현재 탐색 중인 파일과 단계를 실시간으로 화면에 표시. 사용자가 AI 사고 과정을 투명하게 확인 가능.

**구현 노트**

- 탐색 중 파일명 및 단계 스트리밍 표시
- 단계: 검색 → 컨텍스트 구성 → 답변 생성


### AGENT-SEARCH-B-205: 에이전트 탐색 도구 정의

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | SEARCH |

**설명**

에이전트가 호출할 코드 탐색 도구(grep 검색, 파일 읽기, 디렉토리 탐색) 정의 및 등록.

**구현 노트**

- LangChain Tool 정의
- tools: `grep_search`, `read_file`, `list_directory`
- LangGraph 노드에 바인딩


---

## Phase 2

> Phase 2 기능은 Phase 1 MVP 완성 이후 우선순위에 따라 구현합니다.

### AGENT-SEARCH-B-206: 자율 외부 도구 사용

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | SEARCH |
| 우선순위 | 보류 |

**설명**

에이전트가 인터넷 검색 등 외부 도구를 자율적으로 사용하는 로직. 현재 **보류** 상태.


### AGENT-SEARCH-B-207: Advanced Reasoning

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | SEARCH |
| 우선순위 | 보류 |

**설명**

단순 질의응답을 넘어서는 심층 추론 로직. LangGraph 기반 멀티스텝 코드 탐색 및 추론. 현재 **보류** 상태.


