# 📋 중간발표 교수님 피드백 및 RDB 설계 보완 방향

> [!NOTE]
> **작성일**: 2026-06-24 (중간발표 직후)
> **최종 수정**: 2026-06-24 — KimHyo1 PR #104 리뷰 반영 (실제 `code_nodes` 스키마 기준으로 전면 정정)
> **목적**: 교수님 구두 피드백 원문 보존 + 실제 구현 기준 RDB 공백 분석 + 미반영 이슈 연계

---

## 1. 교수님 피드백 원문 (중간발표)

> "로컬과 GitHub 주소 넣는 거 분리한 건 좋다. 로컬에서 Zip 파일을 올리면 서버에서 압축 풀기 기능이 필요하다."
>
> "DB에 벡터 DB와 RDB가 있는데 구분 잘하고 설계 잘 해야 할 것 같다."
>
> "이 파일이 뭔지 질문은 RDB 검색이 더 유리하고, 어떤 검색은 유사도 검색이 더 유리할 수 있음. 아마 이 검색 구현이 힘들 수 있다. 왜냐하면 파일 안에 변수도 있고 함수도 있을 텐데, 파일 선택도 LLM이 하지만 파일 전체 분석도 LLM이 해야 하기 때문에 파일 자체 코드도 DB에 들어가야 하는데, 또 자체 코드만 넣는 것만으로는 안 됨. 파일에 대한 데이터뿐만 아니라 추가적으로… 그래서 결론적으로는 RDB 설계를 잘 해야 함. 다른 팀보다 벡터 DB보다 RDB 비중이 더 높을 수 있음."

### 핵심 요점 정리

| # | 피드백 주제 | 요약 |
|---|---|---|
| 1 | **입력 방식 다양화** | GitHub URL / 로컬 ZIP 업로드 분기 처리 필요 |
| 2 | **벡터 DB vs RDB 역할 분리** | 질문 유형에 따라 어느 DB를 우선 쿼리할지 명확한 전략이 있어야 함 |
| 3 | **파일 단위 정형 검색** | "이 파일이 뭐야?" → Vector Search보다 RDB Exact Match 유리 |
| 4 | **파일 내부 구조의 복잡성** | 함수·클래스·변수를 구조화된 메타데이터로 RDB에 저장해야 함 |
| 5 | **파일 원문 + 메타데이터 동시 저장** | 원문만으로는 부족, 구조적 데이터를 함께 저장해야 함 |
| 6 | **RDB 비중이 타 팀보다 높을 것** | 코드베이스 구조 파악이 핵심 → 정형 메타데이터 조회가 핵심 |

---

## 2. 추가 기능 도출: 로컬 ZIP 업로드 지원

| 기능 ID (안) | 기능명 | 설명 |
|---|---|---|
| `PROJECT-REPO-B-206` | ZIP 파일 업로드 수신 | `multipart/form-data`로 `.zip` 파일 수신 및 임시 디렉토리 저장 |
| `PROJECT-REPO-B-207` | ZIP 압축 해제 및 보안 검증 | Python `zipfile` 모듈. ZipSlip 방어 포함 |
| `PROJECT-REPO-F-205` | ZIP 업로드 UI | 드래그&드롭 / 파일 선택 폼. GitHub URL 탭과 분리 |

> [!IMPORTANT]
> 클론/해제 후 파일 필터링 파이프라인은 두 경로 모두 동일하게 통과하도록 공통 인터페이스로 추상화하는 것이 좋습니다.

---

## 3. RDB 설계 공백 분석 — `code_nodes` 실제 스키마 기준 (정정본)

> [!CAUTION]
> **초안은 레거시 테이블(`source_files`/`code_chunks`) 기준으로 분석되어 일부 공백이 과장됐습니다.**
> KimHyo1 PR #104 리뷰(2026-06-24) 및 GitHub Issue #101 실측 데이터를 반영하여 전면 정정합니다.

### 3-0. 실제 DB 현황 (실측값 기준, Issue #101)

| 테이블 | 실제 행 수 | 역할 | 상태 |
|---|---|---|---|
| `analysis_jobs` | - | 분석 작업 상태 관리 | ✅ 정상 운용 중 |
| `code_nodes` | **787행** (CHUNK 389 / FILE 292 / DIR 106) | 청크·파일·디렉토리 통합, 임베딩 포함 | ✅ 핵심 테이블 |
| `code_dependencies` | **10건** | 파일 간 import 관계 | ⚠️ 과소 적재 (Issue #101) |
| `source_files` | **0행** (레거시) | — | 🗑️ DROP 대상 |
| `code_chunks` | **0행** (레거시) | — | 🗑️ DROP 대상 |
| `file_dependencies` | **0행** (레거시) | — | 🗑️ DROP 대상 |
| `chat_conversations` | - | 대화 세션 | ✅ 정상 운용 중 |
| `chat_messages` | - | 메시지 이력 | ✅ 정상 운용 중 |

> [!WARNING]
> `source_files`, `code_chunks`, `file_dependencies`는 **0행 레거시 테이블**입니다. `code_nodes`/`code_dependencies`로 완전 대체됐으므로 `init.sql`에서 DROP 또는 deprecation 처리가 필요합니다. (Issue #101 참조)

### 3-1. `code_nodes` 실제 구조

`code_nodes`는 파일·청크·디렉토리를 `type` 컬럼으로 구분하는 **통합 테이블**입니다.

| type 값 | 역할 | 주요 컬럼 |
|---|---|---|
| `CHUNK` | AST 청킹 단위 (임베딩 대상) | `content`, `embedding`, `file_metadata`(symbol/chunk_type/start_line/end_line) |
| `FILE` | 파일 단위 메타데이터 | `path`, `language`, `summary` |
| `DIRECTORY` | 폴더 단위 메타데이터 | `path`, `depth`, `summary`(현재 **None**), `embedding`(현재 **None**) |

---

### 공백 A (정정): 심볼 조회 — 데이터 있음, **JSONB 인덱스만 없음**

**초안 주장**: "file_symbols 테이블 없어 심볼 RDB 조회 불가" → **부분 오류**

- CHUNK 노드 `file_metadata` JSONB에 `symbol`, `chunk_type`, `start_line`, `end_line` **이미 저장됨**
- `WHERE file_metadata->>'symbol' = 'login' AND type = 'CHUNK'` 지금도 가능
- **실제 공백**: 인덱스 없어 full scan + 변수 레벨 미수집

```sql
-- 새 테이블 불필요, 인덱스만 추가
CREATE INDEX IF NOT EXISTS idx_code_nodes_symbol
    ON code_nodes ((file_metadata->>'symbol'))
    WHERE type = 'CHUNK' AND file_metadata->>'symbol' IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_code_nodes_chunk_type
    ON code_nodes ((file_metadata->>'chunk_type'))
    WHERE type = 'CHUNK';
```

---

### 공백 B (유지): `file_role` 분류 컬럼 없음

`language`는 있으나 `file_role`(router/service/config 등) 없음 — FILE 타입 노드 확장 필요

```sql
ALTER TABLE code_nodes ADD COLUMN IF NOT EXISTS file_role VARCHAR(50);
ALTER TABLE code_nodes ADD COLUMN IF NOT EXISTS is_entry_point BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS idx_code_nodes_file_role
    ON code_nodes (job_id, file_role) WHERE type = 'FILE';
```

연관 이슈: **#93** (lines/size 메타데이터 추가 — 동일 FILE 노드 확장 작업)

---

### 공백 C (유지): 질문 유형 → DB 라우팅 전략 없음

orchestrator 빈 스캐폴드, `access_plan`에 `search_strategy` 필드 없음

| 질문 유형 | 예시 | 전략 | 쿼리 힌트 |
|---|---|---|---|
| 파일 정체 | "auth.py 가 뭐야?" | **RDB Exact** | `WHERE path LIKE '%auth.py' AND type='FILE'` |
| 심볼 존재 | "login 함수 어디?" | **RDB JSONB** | `WHERE file_metadata->>'symbol'='login'` |
| 역할 기반 | "라우터 파일 목록" | **RDB Filter** | `WHERE file_role='router'` |
| 의존성 | "이 파일 import 하는 곳?" | **RDB Graph** | `code_dependencies` JOIN |
| 개념 | "인증 로직이 어떻게 돼?" | **Vector** | cosine similarity |
| 구현 세부 | "JWT 검증 코드" | **Hybrid** | Vector → path → FILE 원문 JOIN |

---

### 공백 D (정정): 디렉토리 엔티티 — DIRECTORY 노드 106개 **이미 있음**

**초안 주장**: "directory_nodes 테이블 없음" → **오류**

- `code_nodes`에 DIRECTORY 타입 106개 존재
- **실제 공백**: `summary`와 `embedding`이 모두 **None** (Tree-RAG 폴더 요약 미실행)

```sql
-- 새 테이블 불필요, 기존 DIRECTORY 노드 업데이트
UPDATE code_nodes
SET summary = :folder_summary, embedding = :folder_embedding
WHERE type = 'DIRECTORY' AND job_id = :job_id AND path = :dir_path;
```

---

### 공백 E (유지): `report_json` JSONB 집중

> [!NOTE]
> **Issue #92는 PR #99(2026-06-23 main 머지)에서 해결 완료**됐습니다. `repo/service.py`의 `_run_parse_and_embed`에서 `run_parse_pipeline` 결과를 `report_json`에 병합하는 연결이 구현됐으며, `embed_ready` / `vector_search` 계약도 함께 추가됐습니다.
> `report_json` 구조 정규화(분리) 여부는 실데이터 운용 후 별도 판단 예정입니다.

---

## 4. GitHub 열린 이슈 현황 및 문서 연계

> [!IMPORTANT]
> 아래 이슈들을 다음 스프린트 계획에 포함해야 합니다.

### 설계 문서 반영 필요 이슈

| Issue | 제목 | 우선순위 | 연계 |
|---|---|---|---|
| **#101** | `code_dependencies` 과소 적재 + 레거시 테이블 정리 | 🔴 높음 | `init.sql` DROP + RAG-PARSE-B-208 보강 |
| **#93** | 파일 `lines`/`size` 메타데이터 추가 | 🔴 높음 | 공백 B — `code_nodes` FILE 노드 확장 |
| ~~**#92**~~ | ~~`ParseResult` → `report_json` 저장 연결 누락~~ | ✅ **PR #99에서 해결 (main 머지 완료)** | `repo/service.py` `_run_parse_and_embed` 구현 |
| **#94** | Risk Score 오탐 개선 | 🟡 중간 | guard 도메인 명세 보강 |
| **#103** | 다수 job_id 시 벡터검색 효율 (스케일) | 🟢 낮음 | Phase 2 후순위 |

### 버그 이슈 (명세 보완 필요)

| Issue | 제목 |
|---|---|
| **#66** | list/validate API 응답 필드 누락 · 계약 불일치 |
| **#57** | repo/pipeline 노드 예외처리 부재 · event_manager 레이스 |
| **#56** | chat 고아 user 메시지 · 무제한 컨텍스트/인젝션 |
| **#53** | parse/directory 민감파일 대소문자 우회 · rglob 무제한 |

---

## 5. 즉시 반영 액션 플랜

### 다음 회의 전

- [ ] `init.sql` 레거시 테이블 정리 — `source_files`, `code_chunks`, `file_dependencies` DROP (Issue #101)
- [ ] `code_nodes` JSONB 인덱스 추가 — `file_metadata->>'symbol'` (공백 A 핵심)
- [ ] `code_nodes` FILE 타입에 `file_role`, `is_entry_point` 추가 (공백 B)
- [x] ~~Issue #92 저장 연결 작업~~ — PR #99에서 해결 완료

### 중기 반영 (다음 스프린트)

- [ ] Issue #93 — FILE 노드에 `lines`/`size` 추가
- [ ] Issue #101 — 모노레포 import 경로 해결 (`backend/` prefix 탐지)
- [ ] DIRECTORY 노드 `summary`/`embedding` 채우기 (Tree-RAG 파이프라인)
- [ ] Supervisor Agent `access_plan`에 `search_strategy` 필드 추가
- [ ] 로컬 ZIP 업로드 명세 (`PROJECT-REPO-B-206/207`, `PROJECT-REPO-F-205`)

### 관련 문서 업데이트 체크리스트

- [ ] `database/init.sql` — 레거시 DROP + 인덱스 추가
- [ ] `docs/03_Specifications/02_RAG/spec/RAG_EMBED_SPEC.md` — `code_nodes` 실제 구조 기준 업데이트
- [ ] `docs/03_Specifications/01_Project/spec/PROJECT_REPO_SPEC.md` — ZIP 업로드 기능 추가
- [ ] `docs/04_Decisions/MULTI_AGENT_ARCHITECTURE_DECISION.md` — 검색 라우팅 전략 섹션 추가

---

## 6. 현 아키텍처 강점 (Keep)

| 항목 | 현재 상태 | 평가 |
|---|---|---|
| 벡터 + RDB 통합 (pgvector) | `code_nodes` 단일 테이블에 임베딩·메타데이터 통합 | ✅ 방향성 맞음 |
| import 의존성 그래프 | `code_dependencies` (구조는 맞음, 해결률 개선 필요) | ⚠️ Issue #101 |
| AST 기반 청킹 + 심볼 메타데이터 | `file_metadata` JSONB에 symbol/start_line/end_line | ✅ 데이터 있음, 인덱스만 추가하면 됨 |
| HNSW 인덱스 | `code_nodes.embedding` HNSW 적용 | ✅ 벡터 검색 성능 고려됨 |
| Agentic RAG | Supervisor Agent 설계 존재 | ✅ 검색 라우팅 자동화 기반 있음 |

**결론**: 핵심 데이터는 이미 `code_nodes`에 잘 쌓여 있습니다. **"새 RDB 테이블 추가"가 아니라 이미 있는 데이터를 인덱싱·분류·라우팅**하는 것이 실제 보완 방향이며, 이것이 교수님 피드백의 본질과도 일치합니다.

---

## 7. 타 팀 발표 벤치마킹 — 3팀

### 총평

> "3팀 발표 제일 잘함. 특히 gem이라는 예전 GPTs와 같이 바로 에이전트를 커스텀화해서 사용하는 방식, 분석 파이프라인 흐름 시각화 부분이 돋보이는데 분석 매트릭스 / 파이프라인 그래프 탭이 따로 있었고 파이프라인 그래프는 HTML CSS SVG를 활용해서 구현했다고 함"

### 에이전트 커스터마이징 UX — "Gem" 방식

| 적용 포인트 | 방향 | 기능 ID (안) |
|---|---|---|
| **분석 프리셋 저장** | "신입 온보딩 모드" / "보안 감사 모드" 등 | `AGENT-CHAT-F-207` |
| **답변 스타일 커스텀** | Final Answer Agent 프롬프트 파라미터 사용자 설정 | `AGENT-CHAT-B-205` |
| **질문 템플릿 저장** | 자주 쓰는 질문 즐겨찾기 | `AGENT-CHAT-F-208` |

### 파이프라인 시각화 — 별도 탭 구성

| 항목 | 3팀 | CodeMap 현재 | 보완 방향 |
|---|---|---|---|
| 파이프라인 흐름 시각화 | ✅ SVG 그래프 | ❌ Progress Bar | 단계별 노드 그래프 (기존 SSE `stage` 필용) |
| 분석 매트릭스 뷰 | ✅ 별도 탭 | ❌ 없음 | `code_nodes` FILE 조회로 구현 가능 |

### 벤치마킹 우선순위

| 항목 | 난이도 | 임팩트 | 우선순위 |
|---|---|---|---|
| 파이프라인 그래프 탭 (HTML/SVG) | 낮음 (SSE 활용) | 높음 | **🔴 높음** |
| 분석 매트릭스 탭 (파일별 테이블) | 중간 (공백 B 보완 후) | 높음 | **🟡 중간** |
| 에이전트 커스텀 프리셋 UI | 중간 (UI 먼저, 로직 Phase 2) | 중간 | **🟡 중간** |
