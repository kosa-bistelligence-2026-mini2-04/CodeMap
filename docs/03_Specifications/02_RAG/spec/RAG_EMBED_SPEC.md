# RAG EMBED 기능 명세서

> **도메인**: RAG | **모듈**: RAG-EMBED | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| RAG-EMBED-B-201 | 임베딩 생성 | Backend | Phase 1 |
| RAG-EMBED-B-301 | pgvector 저장 | Backend | Phase 1 |

---

## Phase 1

### RAG-EMBED-B-201: 임베딩 생성

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | EMBED |

**설명**

코드 및 문서를 벡터화. 파싱된 청크 텍스트를 OpenAI `text-embedding-3-large` 모델로 임베딩 벡터 생성. 배치 API 호출로 비용 최적화.

**구현 노트**

- 모델: `text-embedding-3-large` + `dimensions=1536`
  - large 모델의 다국어(한국어↔영어) 검색 강점 유지
  - 1536차원으로 저장 용량·pgvector HNSW 인덱스 호환성 확보
  - 결정 근거: [`docs/04_Decisions/EMBEDDING_MODEL_DECISION.md`](../../../../04_Decisions/EMBEDDING_MODEL_DECISION.md)
- 구현 방식: LangChain `OpenAIEmbeddings` wrapper 사용 (`langchain-openai` 패키지)
  ```python
  from langchain_openai import OpenAIEmbeddings

  embeddings = OpenAIEmbeddings(
      model="text-embedding-3-large",
      dimensions=1536,  # 마트료시카 축소 파라미터
  )
  ```
- 배치 크기: 100개 청크 (환경변수 `EMBEDDING_BATCH_SIZE`로 제어)
- API 호출 실패 시 지수 백오프 재시도 (최대 3회, `tenacity` 라이브러리 사용)
  - 1회 실패 → 1초 대기, 2회 실패 → 2초 대기, 3회 실패 → 4초 대기
- 환경변수: `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, `EMBEDDING_BATCH_SIZE`, `EMBEDDING_MAX_RETRIES` (`core/config.py` 관리)


### RAG-EMBED-B-301: pgvector 저장

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | EMBED |

**설명**

임베딩 및 메타데이터 저장. 생성된 임베딩 벡터를 pgvector(PostgreSQL 확장)에 저장. 메타데이터(파일명, 라인, 언어, 심볼명)와 함께 저장.

**구현 노트**

- pgvector extension 활성화 (`CREATE EXTENSION IF NOT EXISTS vector`)
- `source_files` 테이블: `id`, `repo_id`, `file_path`, `raw_code`, `file_summary`
- `code_chunks` 테이블:

  | 컬럼 | 타입 | 설명 |
  | --- | --- | --- |
  | `id` | UUID | 청크 고유 ID |
  | `file_id` | UUID (FK) | `source_files.id` 참조 |
  | `chunk_summary` | TEXT | 청크 텍스트 (임베딩 대상 원문) |
  | `embedding_vector` | vector(1536) | OpenAI 임베딩 벡터 |
  | `start_line` | INTEGER | AST 청킹 시작 라인 (RAG-PARSE-B-207) |
  | `end_line` | INTEGER | AST 청킹 종료 라인 |
  | `symbol` | VARCHAR(255) | 함수/클래스/모듈 심볼명 (검색 필터링용) |
  | `language` | VARCHAR(50) | 프로그래밍 언어 (python, javascript 등) |
  | `created_at` | TIMESTAMPTZ | 생성 시각 |

- 인덱스 타입: **HNSW** (cosine similarity)
  - IVFFlat 대비 빠른 빌드 시간, 증분 삽입 지원, 1536차원에서 안정적 성능
  - `CREATE INDEX USING hnsw (embedding_vector vector_cosine_ops)`
  - 추가 인덱스: `idx_code_chunks_file_id` (file_id 기반 조회), `idx_code_chunks_language` (언어 필터)
- 배치 upsert로 성능 최적화 (100개 단위)
- `forceReembed=true` 시 기존 청크 삭제 후 재삽입


