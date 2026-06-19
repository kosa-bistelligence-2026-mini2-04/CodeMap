# AGENT CHAT 기능 명세서

> **도메인**: AGENT | **모듈**: AGENT-CHAT | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| AGENT-CHAT-B-101 | Repo Chat API | Backend | Phase 1 |
| AGENT-CHAT-B-201 | 코드 컨텍스트 생성 | Backend | Phase 1 |
| AGENT-CHAT-B-202 | 출처 파일 반환 | Backend | Phase 1 |
| AGENT-CHAT-F-201 | AI 응답 UI | Frontend | Phase 1 |
| AGENT-CHAT-F-204 | 스트리밍 응답 처리 | Frontend | Phase 1 |
| AGENT-CHAT-F-205 | 답변 스트리밍 UI | Frontend | Phase 1 |
| AGENT-CHAT-F-202 | 탐색 루프 횟수/시간 제한 | Frontend | Phase 2 |
| AGENT-CHAT-F-203 | 관련 파일 검색 | Frontend | Phase 2 |
| AGENT-CHAT-F-206 | 질문 의도 분석 | Frontend | Phase 2 |
| AGENT-CHAT-B-203 | 장기 기억 (Long-term Memory) | Backend | Phase 2 |

---

## Phase 1

### AGENT-CHAT-B-101: Repo Chat API

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CHAT |

**설명**

`POST /api/chat/{repo_id}` — RAG 기반 코드베이스 질문 응답 API 엔드포인트. LangGraph 워크플로우를 실행하여 관련 코드 청크를 검색한 뒤 LLM 응답을 SSE 스트리밍으로 반환.

**구현 노트**

- LangGraph 워크플로우 실행
- SSE(Server-Sent Events) 스트리밍 응답
- AGENT-SEARCH 모듈과 연동하여 관련 청크 검색 후 LLM Context 구성


### AGENT-CHAT-B-201: 코드 컨텍스트 생성

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CHAT |

**설명**

관련 파일을 묶어 LLM Context 구성. 컨텍스트 윈도우 한도(token limit) 내에서 최대한 많은 관련 코드를 포함하도록 선별.

**구현 노트**

- AGENT-SEARCH 검색 결과를 입력으로 받음
- 토큰 수 기반 청크 선택 (tiktoken 사용)


### AGENT-CHAT-B-202: 출처 파일 반환

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CHAT |

**설명**

파일명 및 line 정보 제공. LLM 응답 생성에 사용된 청크의 출처(파일명, 시작/끝 라인번호)를 응답 payload에 포함.

**구현 노트**

- 청크 메타데이터(file_path, start_line, end_line)를 응답에 포함
- 사용자가 근거를 추적할 수 있도록 출처 파일 목록 제공


### AGENT-CHAT-F-201: AI 응답 UI

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | CHAT |

**설명**

답변 및 참조 파일명 표시. LLM 응답 텍스트와 참조 파일명을 화면에 표시. Markdown 렌더링 및 코드 블록 하이라이팅 포함.

**구현 노트**

- react-markdown + remark-gfm
- 파일 참조 목록 사이드패널 표시


### AGENT-CHAT-F-204: 스트리밍 응답 처리

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | CHAT |

**설명**

FastAPI SSE(Server-Sent Events) 기반 LLM 응답 스트리밍 처리. EventSource API로 청크 단위 텍스트를 수신하여 실시간으로 누적.

**구현 노트**

- EventSource API 사용
- 청크 단위 텍스트 누적 처리


### AGENT-CHAT-F-205: 답변 스트리밍 UI

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | CHAT |

**설명**

LLM 답변을 실시간 스트리밍으로 받아 타이핑 효과로 표시. 스트리밍 중 로딩 커서 표시, 완료 시 복사 버튼 활성화.

**구현 노트**

- 타이핑 커서 애니메이션
- 완료 시 복사 버튼 활성화


---

## Phase 2

> Phase 2 기능은 Phase 1 MVP 완성 이후 우선순위에 따라 구현합니다.

### AGENT-CHAT-F-202: 탐색 루프 횟수/시간 제한

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | CHAT |
| 우선순위 | Phase 2 기능 |

**설명**

에이전트 도구 호출 최대 5회 · 처리 시간 최대 20초 제한. 초과 시 수집 정보 기반 최선 답변 반환.


### AGENT-CHAT-F-203: 관련 파일 검색

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | CHAT |
| 우선순위 | Phase 2 기능 |

**설명**

벡터 검색 기반 관련 코드 탐색. 질문과 관련된 파일 목록을 사이드패널에 표시.


### AGENT-CHAT-F-206: 질문 의도 분석

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | CHAT |
| 우선순위 | Phase 2 기능 |

**설명**

자연어 질문 파싱. 질문 유형을 분류(코드 설명 / 버그 분석 / 아키텍처 질문 등)하여 라우팅.


### AGENT-CHAT-B-203: 장기 기억 (Long-term Memory)

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | CHAT |
| 우선순위 | 보류 — 사용자 세션 기반 지속적인 장기 기억 관리 로직 |

**설명**

사용자 세션 기반 지속적인 장기 기억 관리 로직. 현재 **보류** 상태.


