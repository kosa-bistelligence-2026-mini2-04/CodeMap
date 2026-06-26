# LLM TOOL 기능 명세서

> **도메인**: Tool | **모듈**: LLM-TOOL | **최종 업데이트**: 2026-06-25

## 범위

`LLM-TOOL`은 RAG 검색, 디렉토리 조회, Grep 검색, 파일 읽기 등 소스코드 탐색 도구의 **실제 실행**을 담당하는 결정론적 계층입니다. 결과를 요약하지 않고 **Raw Data를 그대로 `worker_results`에 병합(fan-in)**합니다.

> **구현 구조(중요)**: LangGraph 워커는 `backend/app/agent/workers/{search,dir,grep,read}_worker.py`에 분리되어 있고, 실제 결정론적 도구 실행은 `backend/app/tool/`의 `hybrid_search.py`, `rrf.py`, `dir_scan.py`, `grep_scan.py`, `file_read.py`에 둡니다. `backend/app/tool/`의 `CodeMapToolService`는 **MCP-style 외부 도구 Job 인터페이스**로, 단일 JSON Job을 내부 결정론적 도구로 라우팅합니다.

| 구분 | 기준 |
| --- | --- |
| 구현 위치 | `backend/app/agent/workers/`(4 워커 adapter), `backend/app/tool/hybrid_search.py`(RAG RRF), `backend/app/tool/rrf.py`(RRF 알고리즘), `backend/app/tool/dir_scan.py`, `backend/app/tool/grep_scan.py`, `backend/app/tool/file_read.py` / MCP 인터페이스: `backend/app/tool/service.py` |
| 성격 | Deterministic Code Domain (search 워커는 임베딩 호출 포함) |
| 책임 | 4개 단일목적 도구 실행, RAG RRF 검색, 경로 보안 검증, 자원 제한, raw 결과 fan-in |
| 비책임 | 계획 수립(→ PLANNER), 실행 순서/충분성 평가(→ EVALUATOR), 사용자 답변 스트리밍(→ Chat) |

---

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| LLM-TOOL-B-201 | 단일 목적 Worker 실행 (search/dir/grep/read) | Backend | Phase 1 |
| LLM-TOOL-B-202 | RAG RRF 하이브리드 검색 (pgvector + BM25) | Backend | Phase 1 |
| LLM-TOOL-B-203 | 경로 보안 검증 및 자원 제한 | Backend | Phase 1 |
| LLM-TOOL-B-204 | MCP-style 외부 도구 Job 인터페이스 | Backend | Phase 2 |

---

## LLM-TOOL-B-201: 단일 목적 Worker 실행

### 1. 설명
`dispatcher_node`가 `Send`로 전달한 `_plan_item`을 읽어 4개 워커 중 하나가 단일 도구를 실행한다. 각 워커는 실행 시작 시 `worker_started` 이벤트를 발행하고, 결과를 `WorkerResult`로 만들어 `worker_results`(operator.add)에 병합한 뒤 `worker_result` 이벤트를 발행한다.

### 2. 입/출력 규격
- **공통 Input**: `state["_plan_item"]`(`{tool, path, query, scope}`), `clone_path`, (search는 `repo_id`)
- **공통 Output**: `{ "worker_results": [WorkerResult...], "events": [{"type":"worker_started","worker","target"}, {"type":"worker_result","worker","resultCount","evidenceIds"}] }`
- **워커별 동작**:
  - `search_worker`: 하이브리드 검색(B-202) → 실패/미준비 시 키워드 검색(`search_repository`) 폴백 → 그것도 실패 시 실패 사유 스니펫
  - `dir_worker`: `tool/dir_scan.py`의 `scan_directory_tree` 호출
  - `grep_worker`: `tool/grep_scan.py`의 `grep_repository_path` 호출
  - `read_worker`: `tool/file_read.py`의 `read_repository_file` 호출
- **`WorkerResult` 필드**: `id`(`ev_<hex8>`), `path`, `lineStart`, `lineEnd`, `score`, `snippet`, `metadata{worker, tool, query}`

### 3. 완료 조건
- 각 워커는 결과를 요약하지 않고 raw `snippet` 그대로 반환한다.
- 도구 실행 결과가 비어도 `worker_started`와 `worker_result(resultCount=0)` 이벤트를 발행해 프론트 타임라인 계약을 유지한다.

---

## LLM-TOOL-B-202: RAG RRF 하이브리드 검색

### 1. 설명
시맨틱 임베딩(pgvector) 검색과 키워드(BM25) 검색 순위를 **RRF(Reciprocal Rank Fusion)**로 병합한다. 구현: `tool/hybrid_search.py::hybrid_search`, 순수 함수 `tool/rrf.py`.

### 2. 입/출력 규격
- **시그니처**: `hybrid_search(db, job_id, query, top_n=5)`
- **흐름**:
  1. `embed_ready(db, job_id)` 가드 — 임베딩 미준비면 `[]` 반환(caller 키워드 폴백)
  2. `vector_search(db, job_id, query, k=20)` — **RAG 단일 진입점**(`app.embed.service`) 사용, 결과 `[{file, snippet, score}]`
  3. BM25 재스코어링: 시맨틱 후보 풀(`content`)을 corpus로 `bm25_rank`(rank_bm25 `BM25Okapi`, 미설치 시 빈 리스트 → 시맨틱 단독)
  4. `rrf_score = Σ 1/(k + rank)`, **k=60**, 내림차순 정렬 후 `top_n`
- **반환**: `[{file_path, content, summary, rrf_score, semantic_rank, bm25_rank}]`
- **폴백**: 시맨틱 결과 없음/연동 실패 → `[]`(caller가 키워드 검색으로 폴백)

### 3. 완료 조건
- 쿼리 임베딩·스코어·모델/차원 설정은 `vector_search` 한 곳으로 수렴한다(중복 임베딩 경로 금지).
- BM25 미설치 환경에서도 시맨틱 순위만으로 정상 동작(graceful degradation)한다.

---

## LLM-TOOL-B-203: 경로 보안 검증 및 자원 제한

### 1. 설명
파일 시스템에 접근하는 워커(dir/grep/read)는 워크스페이스 경계를 벗어나는 접근을 차단하고, 과대 입력으로부터 자원을 보호한다.

### 2. 입/출력 규격
- **경로 경계 검증**: `target = (Path(clone_path) / rel_path).resolve()` 후 `target.relative_to(Path(clone_path).resolve())`가 실패하면 차단(빈 결과 반환) — `..`/심볼릭 링크 경유 탈출 및 `/repo` vs `/repo-other` 같은 문자열 prefix 착시 방지
- **자원 제한**: 파일당 `_MAX_FILE_SIZE = 50_000`자 초과 시 절단, grep 결과 `_MAX_GREP_RESULTS = 30`개 상한, dir 트리 200줄 상한
- (참고) `dispatcher_node`(LLM-AGENT-B-203)는 plan 단계에서 절대경로·`..`·민감 파일 패턴을 1차 차단하며, 본 항목은 워커 실행 단계의 2차 경계 검증이다.

### 3. 완료 조건
- 경계 밖 경로 접근은 실행되지 않고 조용히 빈 결과로 처리된다.
- 대용량 파일/대량 매칭에서도 응답 크기가 상한 내로 제한된다.

---

## LLM-TOOL-B-204: MCP-style 외부 도구 Job 인터페이스 (Phase 2)

### 1. 설명
에이전트/외부 시스템이 `{tool_name, arguments}` 표준 JSON Job으로 도구를 호출하는 MCP-style I/O 인터페이스. 구현: `app/tool/service.py::CodeMapToolService.execute_job`.

### 2. 입/출력 규격
- **요청 계약**: `POST /tools/execute`는 `{tool_name, arguments}`(+`job_id`, `run_id`)를 **단일 JSON body**로 수신한다 — 전용 Pydantic 요청 스키마로 받으며, 개별 필드를 쿼리 파라미터로 분산 수신하지 않는다(외부 MCP가 JSON 객체 하나로 전송 시 `422` 방지).
- **인증 정책**: 내부 MCP/agent 전용 API로 간주하며, `Authorization: Bearer {SERVICE_TOKEN}`이 설정값과 일치할 때만 실행한다. 토큰 누락 또는 불일치 시 `401`을 반환한다.
- **`execute_job(job_id, run_id, tool_name, arguments)`** — `tool_name` 분기: `vector_search` | `file_read` | `dir_scan` | `grep_scan` (미지원 시 `ValueError`)
- **반환 DTO**: `{code, message, status, data:{jobId, runId, toolName, results:[WorkerResult...]}}`
- **현황**: `/tools/execute`는 `CodeMapToolService.execute_job`을 호출해 B-201/B-202의 내부 결정론적 도구를 동일 `WorkerResult` 규격으로 반환합니다.

### 3. 완료 조건
- 요청은 단일 JSON body(Pydantic 스키마)로만 수신한다.
- 실제 도구 실행은 서비스 토큰 검증 후에만 수행한다.
- `execute_job`이 B-201 워커/B-202 하이브리드 검색 실구현을 호출해 동일 `WorkerResult` 규격으로 반환하고, 실구현 결과에 대해서만 `success`를 반환한다.
- 미지원 `tool_name`은 `400`으로 거부하고, 잘못된 UUID는 `422`로 거부한다.
