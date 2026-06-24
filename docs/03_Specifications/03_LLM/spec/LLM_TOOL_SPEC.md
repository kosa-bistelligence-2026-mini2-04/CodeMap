# LLM TOOL 기능 명세서

> **도메인**: Tool | **모듈**: LLM-TOOL | **최종 업데이트**: 2026-06-24

## 범위

`LLM-TOOL`은 RAG 검색, 파일/디렉토리 조회, Grep 키워드 검색 등 소스코드 탐색용 도구들의 실제 실행을 담당하는 독립 서비스 계층입니다. `{tool, directory}` 중심의 JSON Job을 수신하여 실행을 전담합니다.

| 구분 | 기준 |
| --- | --- |
| 구현 위치 | `backend/app/tool/` |
| 성격 | Deterministic Code Domain |
| 책임 | JSON Job 수신 처리, RAG RRF 검색, Symlink 차단 파일 조회, 디렉토리 트리 조회, 결과 반환 |
| 비책임 | 계획 수립, 실행 순서 제어, 충분성 평가, 사용자 답변 스트리밍 |

---

## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| LLM-TOOL-B-201 | MCP I/O JSON Job 수신 처리 | Backend | Phase 1 |
| LLM-TOOL-B-202 | RAG RRF 하이브리드 검색 | Backend | Phase 1 |
| LLM-TOOL-B-203 | Symlink 방어 파일 조회 | Backend | Phase 1 |

---

## LLM-TOOL-B-201: MCP I/O JSON Job 수신 처리

### 1. 설명
에이전트나 외부 시스템으로부터 `{tool_name, arguments}` 로 구성된 표준 JSON Job 구조를 수신받아 대응하는 도구 메서드로 분기 실행합니다.

### 2. DTO 규격
- **AgentJob DTO**:
  - `job_id`: UUID (작업 고유 식별자)
  - `run_id`: UUID (실행 세션 식별자)
  - `tool_name`: String ("vector_search", "file_read", "dir_scan", "grep_scan")
  - `arguments`: Dict (도구 인자값)
- **WorkerResult DTO**:
  - `evidence_id`: UUID (수집된 근거 식별자)
  - `job_id`: UUID
  - `status`: String ("success", "failed")
  - `path`: String (상대 경로)
  - `line_start`: Integer
  - `line_end`: Integer
  - `snippet`: String (코드 조각)
  - `score`: Float
  - `metadata`: Dict

---

## LLM-TOOL-B-202: RAG RRF 하이브리드 검색

### 1. 설명
시맨틱 임베딩(pgvector) 검색 순위와 키워드(BM25/pg_trgm) 검색 순위를 RRF 가중합 알고리즘으로 병합하여 고정밀 검색을 수행합니다.
