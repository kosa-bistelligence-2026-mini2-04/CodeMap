# AGENT WORKER EVIDENCE 기능 명세서

> **도메인**: AGENT | **모듈**: AGENT-WORKER / AGENT-EVIDENCE | **최종 업데이트**: 2026-06-23

## 범위

이 문서는 코드 근거를 수집하는 worker와, 수집된 근거를 Final Answer Agent가 사용할 수 있도록 정리하는 Evidence Aggregator를 정의합니다. 기존 `AGENT-SEARCH`의 자가 교정 탐색 개념은 단일 agent 루프가 아니라 worker 분리 구조로 대체합니다.

| 구분 | 기준 |
| --- | --- |
| 구현 위치 | `backend/app/agent_graph/workers/`, `backend/app/agent_graph/tools/`, `backend/app/agent_graph/nodes/evidence_node.py` |
| 원본 근거 저장 | `CodeMapState.worker_results` |
| 답변용 압축 근거 | `CodeMapState.compact_context` |
| 외부 노출 | evidence 조회 API에서 metadata 중심으로 노출 |

---

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| AGENT-WORKER-B-201 | Search Worker Agent | Backend | Phase 1 |
| AGENT-WORKER-B-202 | Dir Worker | Backend | Phase 1 |
| AGENT-WORKER-B-203 | Grep Worker | Backend | Phase 1 |
| AGENT-WORKER-B-204 | Read Worker | Backend | Phase 1 |
| AGENT-WORKER-B-205 | Code Reasoning Worker | Backend | Phase 1 선택 |
| AGENT-EVIDENCE-B-201 | Evidence Aggregator Node | Backend | Phase 1 |
| AGENT-WORKER-B-206 | 허용된 외부 도구 worker 확장 | Backend | Phase 2 |
| AGENT-WORKER-B-207 | Code Reasoning Worker 고도화 | Backend | Phase 2 |

---

## 공통 Worker 계약

모든 worker는 결과를 같은 evidence shape로 반환합니다.

| 필드 | 설명 |
| --- | --- |
| `id` | evidence ID |
| `worker` | worker 이름 |
| `path` | repo 내부 상대 경로 |
| `lineStart` | 시작 라인 |
| `lineEnd` | 종료 라인 |
| `score` | 검색/선정 점수 |
| `snippet` | 원본 snippet |
| `metadata` | language, symbol, query, match type 등 |

Worker는 사용자에게 직접 답변하지 않습니다. 답변 문장 생성은 `Final Answer Agent`가 담당합니다.

---

## AGENT-WORKER-B-201: Search Worker Agent

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | WORKER |
| 구현 위치 | `agent_graph/workers/search_worker.py` |

**설명**

한국어 자연어 질문, 오타, 축약 표현을 코드 검색용 query로 확장하고 embedding/vector search 또는 metadata search 전략을 실행합니다.

**구현 노트**

- LLM query rewrite를 사용할 수 있습니다.
- 검색 모델과 embedding dimension은 RAG embedding 결정 문서를 따릅니다.
- 결과는 snippet을 과도하게 요약하지 않고 evidence로 반환합니다.

---

## AGENT-WORKER-B-202: Dir Worker

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | WORKER |
| 구현 위치 | `agent_graph/workers/dir_worker.py` |

**설명**

Route Node가 허용한 경로 안에서 디렉토리 구조를 탐색합니다. 사용자가 "어디에 있어?"처럼 위치 탐색을 요청할 때 초기 후보를 좁힙니다.

**출력 예시**

| 필드 | 설명 |
| --- | --- |
| `path` | 탐색한 디렉토리 |
| `children` | 하위 파일/폴더 목록 |
| `metadata.depth` | 탐색 깊이 |

---

## AGENT-WORKER-B-203: Grep Worker

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | WORKER |
| 구현 위치 | `agent_graph/workers/grep_worker.py` |

**설명**

키워드, 정규식, alias 기반으로 코드 후보를 검색합니다. Search Worker의 semantic result를 보완하여 정확한 symbol, endpoint, class/function 이름을 찾습니다.

**구현 노트**

- 정규식은 안전한 timeout과 결과 수 제한을 적용합니다.
- binary, generated, dependency directory는 기본 제외합니다.
- pattern 오류는 `AGENT_WORKER_FAILED` 또는 worker-level validation error로 기록합니다.

---

## AGENT-WORKER-B-204: Read Worker

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | WORKER |
| 구현 위치 | `agent_graph/workers/read_worker.py` |

**설명**

Route Node가 허용한 후보 파일만 읽어 raw snippet과 line range를 반환합니다. path traversal 차단은 Route Node에서 먼저 수행하고, Read Worker도 방어적으로 재검증합니다.

**제약**

| 항목 | 기준 |
| --- | --- |
| 최대 라인 | 요청당 기본 200줄 이하 |
| 파일 크기 | 서버 정책 상한 적용 |
| secret file | 기본 차단 |
| 경로 | repo 내부 상대 경로만 허용 |

---

## AGENT-WORKER-B-205: Code Reasoning Worker

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | WORKER |
| Phase | Phase 1 선택 / Phase 2 고도화 |

**설명**

읽힌 코드 조각을 바탕으로 의존성, 데이터 흐름, 위험도 등을 추가 해석하는 선택형 LLM worker입니다. MVP에서는 deep mode 또는 명시적 복잡 질문에서만 사용합니다.

**주의**

- 새로운 파일을 직접 읽지 않습니다.
- 입력 evidence 범위 안에서만 추론합니다.
- 추론 결과는 `worker_results`에 reasoning evidence로 추가하되, Final Answer를 대체하지 않습니다.

---

## AGENT-EVIDENCE-B-201: Evidence Aggregator Node

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | EVIDENCE |
| 구현 위치 | `agent_graph/nodes/evidence_node.py` |

**설명**

Worker 결과를 중복 제거하고, 파일 경로/라인/점수/근거 타입 기준으로 정리하여 `compact_context`를 생성합니다. MVP에서는 LLM agent가 아니라 deterministic code node로 구현하는 것을 기본으로 합니다.

**처리 단계**

| 단계 | 설명 |
| --- | --- |
| normalize | evidence shape 통일 |
| dedupe | 같은 파일/라인/내용 중복 제거 |
| rank | score, worker priority, path relevance 기준 정렬 |
| trim | token budget에 맞게 snippet 축약 |
| compact | Final Answer 입력용 `compact_context` 생성 |

**완료 조건**

- raw evidence와 compact context를 모두 보존합니다.
- compact 과정에서 출처 파일/라인 정보가 사라지지 않습니다.
- evidence가 부족한 경우 `compact_context.status = insufficient`로 표시합니다.

---

## Phase 2 확장

### AGENT-WORKER-B-206: 허용된 외부 도구 worker 확장

GitHub issue, docs, webhook 등 외부 도구는 allowlist 기반 worker로만 확장합니다. 외부 write action은 사용자 확인을 요구합니다.

### AGENT-WORKER-B-207: Code Reasoning Worker 고도화

보안 분석, architecture reasoning, data flow tracing 등 고비용 추론을 별도 reasoning run으로 분리합니다.
