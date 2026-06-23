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

## Worker-Tool 바인딩 패턴

### Code Worker (Dir / Grep / Read)

- tool wrapper 함수를 직접 호출 (LLM `tool_call` 불필요)
- 패턴: `result = tool_fn(validated_args)` → evidence shape 변환 → `worker_results` append
- tool은 `agent_graph/tools/` 디렉토리에 순수 함수로 정의

### LLM Worker (Search, Reasoning)

- LangChain `ChatModel.bind_tools([tool])` + `tool_call` 패턴 사용
- LLM이 `tool_call` 메시지를 생성하면 worker가 tool을 실행하고 결과를 evidence로 변환
- `tool_call` 실패 시 재시도 정책: 최대 2회, 실패 시 partial evidence 기록

### State 갱신: `Command(update={})` 패턴

수업 실습(sec07 `tool_state.py`)에서 배운 `Command(update={...})` 패턴을 Worker에 적용합니다.
Worker가 evidence 결과를 `worker_results`에 append할 때 `Command`를 반환하여 State를 직접 갱신합니다.

```python
from langgraph.types import Command

# Worker 노드 반환값 예시
return Command(
    update={
        "worker_results": [evidence],  # Annotated[list, add] reducer가 자동 병합
        "events": [worker_event],
    }
)
```

- Code Worker와 LLM Worker 모두 `Command(update={"worker_results": [evidence]})` 형태로 반환
- `worker_results`의 `Annotated[list, add]` reducer가 fan-in 시 병렬 결과를 자동 병합
- `Command.goto` 없이 `update`만 사용하면 기본 Edge 흐름을 유지하면서 State 갱신 가능

### Tool 시그니처 요약

| Tool | 파일 | 입력 | 출력 |
| --- | --- | --- | --- |
| `search` | `tools/search.py` | query, top_k, filters, mode, scope | list[SearchResult] |
| `dir` | `tools/dir.py` | path, depth, exclude_patterns | DirTree |
| `grep` | `tools/grep.py` | pattern, paths, is_regex, max_results | list[GrepMatch] |
| `read` | `tools/read.py` | path, line_start, line_end | FileContent |

---

## AGENT-WORKER-B-201: Search Worker Agent

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | WORKER |
| 성격 | LLM Agent (`tool_call` 기반) |
| 구현 위치 | `agent_graph/workers/search_worker.py` |

**설명**

한국어 자연어 질문, 오타, 축약 표현을 코드 검색용 query로 확장하고 embedding/vector search 또는 metadata search 전략을 실행합니다.

**입력**

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `rewritten_query` | String | Supervisor가 정리한 검색 질의 |
| `search_hints` | Array\<String\> | Supervisor가 제안한 키워드, 동의어, alias 목록 |
| `allowed_paths` | Array\<String\> | Route Node가 검증한 탐색 허용 경로 |
| `embedding_config` | Object | 사용할 임베딩 모델/차원 설정 (`EMBEDDING_MODEL_DECISION.md` 참조) |
| `search_scope` | String | 검색 단위: `chunk`(기본), `file`, `directory` |
| `search_mode` | String | 검색 전략: `semantic`(기본), `hybrid` |

**구현 노트**

- LLM을 활용한 query rewrite: 한국어 오타 교정, 축약 표현 확장, 코드 관련 동의어(login → signin, auth, authentication 등) 생성
- search tool (`agent_graph/tools/search.py`) 호출을 통해 pgvector 기반 semantic/hybrid search 실행
- embedding 모델과 dimension은 `EMBEDDING_MODEL_DECISION.md` 문서 기준 적용
- 검색 결과는 score 기준 정렬 후 상위 N건을 evidence로 변환
- snippet을 과도하게 요약하지 않고 원본 evidence shape로 반환
- 검색 결과가 부족할 경우 query 변형 재시도 가능 (최대 2회)

**Hybrid Search 전략** _(레퍼런스: CodeRAG, Deep-RAG 프로젝트)_

검색 품질 향상을 위해 두 가지 검색 모드를 지원합니다:

| 모드 | 방식 | 적용 기준 |
| --- | --- | --- |
| `semantic` (기본) | pgvector cosine similarity 기반 | 자연어 질문, 개념 검색 |
| `hybrid` | semantic + keyword(pg_trgm/BM25) → RRF(Reciprocal Rank Fusion) 결합 | `search_hints`에 정확한 심볼/함수명이 있을 때 자동 선택 |

Hybrid 모드 선택 기준: Supervisor의 `access_plan.searchHints`에 식별자 형식(camelCase, snake_case)이 포함되면 Search Worker가 `hybrid` 모드로 자동 전환합니다.

**계층적 검색 Scope** _(레퍼런스: RepoMind, Codebase Onboarding 프로젝트 + 아키텍처 합의 AGENTIC_RAG_ARCHITECTURE.md)_

RAG DB에 저장된 계층적 벡터(chunk → file → directory 요약)를 활용하여 검색 단위를 동적으로 선택합니다:

| scope | 대상 벡터 | 적합한 질문 유형 |
| --- | --- | --- |
| `chunk` (기본) | 코드 청크 단위 벡터 | 특정 함수/로직 위치 파악 |
| `file` | 파일 단위 LLM 요약 벡터 | 특정 기능을 담당하는 파일 파악 |
| `directory` | 디렉토리 단위 LLM 요약 벡터 | 아키텍처/모듈 구조 파악 |

**search tool 호출 인터페이스**

```python
search_tool.invoke({
    "query": str,           # rewritten_query 또는 변형 query
    "top_k": int,           # 검색 결과 상위 N건 (기본 10)
    "mode": str,            # "semantic" | "hybrid" (기본 "semantic")
    "scope": str,           # "chunk" | "file" | "directory" (기본 "chunk")
    "filters": {
        "paths": list[str], # allowed_paths 기반 필터
        "languages": list[str]  # 선택적 언어 필터
    }
}) -> list[SearchResult]
```
```

`SearchResult` shape:

| 필드 | 타입 | 설명 |
| --- | --- | --- |
| `path` | str | repo 내부 상대 경로 |
| `lineStart` | int | 시작 라인 |
| `lineEnd` | int | 종료 라인 |
| `score` | float | similarity score |
| `snippet` | str | 원본 코드 조각 |
| `metadata` | Object | `{ language, chunk_type, embedding_model }` |

**완료 조건**

- search tool 호출 결과를 evidence shape로 변환하여 `worker_results`에 append
- 검색 실패 시 빈 결과를 evidence로 기록하고 `AGENT_WORKER_FAILED`를 발생시키지 않음 (검색 결과 없음은 실패가 아님)
- query rewrite 이력을 metadata에 포함

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

**Phase 1/2 Re-ranking 전략** _(레퍼런스: Deep-RAG 프로젝트)_

| Phase | rank 방식 | 설명 |
| --- | --- | --- |
| Phase 1 | Deterministic scoring | score(벡터 유사도) × worker_priority × path_relevance 가중합으로 정렬. LLM 미사용, 빠름 |
| Phase 2 | LLM-based re-ranking | `compact_context` 생성 전 cross-encoder 또는 경량 LLM으로 최종 relevance 재판정. 정밀도 향상 |

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
