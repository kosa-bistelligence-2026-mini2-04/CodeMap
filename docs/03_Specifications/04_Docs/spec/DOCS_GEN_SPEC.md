# DOCS GEN 기능 명세서

> **도메인**: DOCS | **모듈**: DOCS-GEN | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| DOCS-GEN-B-101 | 가이드북 조회 API | Backend | Phase 1 |
| DOCS-GEN-B-201 | 문서 요약 agent 구현 | Backend | Phase 1 |
| DOCS-GEN-B-202 | 온보딩 guide agent 구현 | Backend | Phase 1 |
| DOCS-GEN-B-203 | 폴더 단위 요약 | Backend | Phase 1 |
| DOCS-GEN-B-204 | 프로젝트 마스터 리포트 생성 | Backend | Phase 1 |
| DOCS-GEN-B-205 | README 기반 프로젝트 소개 생성 | Backend | Phase 1 |
| DOCS-GEN-B-206 | 핵심 실행 플로우 설명 | Backend | Phase 1 |
| DOCS-GEN-B-207 | 문서 재생성 | Backend | Phase 1 |
| DOCS-GEN-B-301 | Markdown 저장 | Backend | Phase 1 |
| DOCS-GEN-F-101 | 온보딩 문서 화면 | Frontend | Phase 1 |
| DOCS-GEN-F-201 | 문서 다운로드 UI | Frontend | Phase 1 |
| DOCS-GEN-F-202 | 파일 단위 요약 | Frontend | Phase 1 |
| DOCS-GEN-F-203 | 추천 읽기 순서/수정 전 주의점 생성 | Frontend | Phase 1 |
| DOCS-GEN-B-208 | 추천 작업 생성 | Backend | Phase 2 |

---

## Phase 1

### DOCS-GEN-B-101: 가이드북 조회 API

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | GEN |

**설명**

`GET /api/docs/{repo_id}` — 생성된 온보딩 가이드북 Markdown 반환. 분석 완료된 프로젝트의 가이드 문서를 조회.

**구현 노트**

- DB에서 최신 버전 문서 조회
- 없을 경우 404 반환


### DOCS-GEN-B-201: 문서 요약 agent 구현

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | GEN |

**설명**

README, config, package, route 파일 기반 프로젝트 설명 생성. GPT-4o-mini를 사용하여 프로젝트 목적 및 핵심 기능 자동 요약.

**구현 노트**

- GPT-4o-mini 사용 (비용 최적화)
- 입력: README, package.json/requirements.txt, 주요 라우터 파일


### DOCS-GEN-B-202: 온보딩 guide agent 구현

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | GEN |

**설명**

읽을 순서, 수정 시작점, 위험 파일, 추천 task 생성. 신규 개발자가 코드베이스를 이해하는 최적 경로를 안내하는 온보딩 가이드 자동 생성.

**구현 노트**

- 추천 파일 읽기 순서 생성
- 위험 파일(auth, DB, env 등) 별도 표시
- 첫 기여 추천 task 제안


### DOCS-GEN-B-203: 폴더 단위 요약

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | GEN |

**설명**

하위 파일 요약 기반 디렉토리 설명 생성. Tree-Based RAG 방식으로 파일 요약 → 폴더 요약 → 마스터 요약 순서로 상향식 통합.

**구현 노트**

- Bottom-up 요약 파이프라인
- 각 폴더별 책임 영역 설명 자동 생성


### DOCS-GEN-B-204: 프로젝트 마스터 리포트 생성

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | GEN |

**설명**

최종 온보딩 문서 통합. 파일 요약, 폴더 요약, 아키텍처 분석, 온보딩 가이드를 하나의 마스터 리포트로 통합.

**구현 노트**

- `summary`, `stack`, `file_map`, `recommendations`, `heatmap`, `durations`, `guide` 필드 포함
- JSON 형태로 DB 저장


### DOCS-GEN-B-205: README 기반 프로젝트 소개 생성

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | GEN |

**설명**

프로젝트 목적 및 핵심 기능 요약. README를 파싱하여 구조화된 프로젝트 소개 섹션 생성.


### DOCS-GEN-B-206: 핵심 실행 플로우 설명

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | GEN |

**설명**

요청 흐름 및 핵심 구조 설명. 사용자 요청이 시스템 내부에서 어떻게 처리되는지 end-to-end 플로우를 문서화.

**구현 노트**

- 진입점(entrypoint)부터 DB까지의 데이터 흐름 추적
- 주요 함수 호출 체인 시각화


### DOCS-GEN-B-207: 문서 재생성

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | GEN |

**설명**

기존 분석 기반 재생성 기능. 이전에 생성된 문서를 최신 코드 분석 결과로 갱신.

**구현 노트**

- 이전 버전 soft delete 후 재생성
- 재생성 완료 시 버전 이력 보존


### DOCS-GEN-B-301: Markdown 저장

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | GEN |

**설명**

생성 결과 DB 저장. 생성된 온보딩 문서를 Markdown 형식으로 PostgreSQL에 저장.

**구현 노트**

- `docs` 테이블: project_id, doc_type, content, version, created_at
- 최신 버전 조회 최적화


### DOCS-GEN-F-101: 온보딩 문서 화면

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | GEN |

**설명**

JSON 기반 결과 렌더링. 마스터 리포트 JSON을 파싱하여 온보딩 문서를 화면에 시각적으로 표시.

**구현 노트**

- `summary`, `stack`, `file_map`, `guide` 섹션별 렌더링
- 탭 또는 사이드바 네비게이션


### DOCS-GEN-F-201: 문서 다운로드 UI

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | GEN |

**설명**

JSON → Markdown / HTML → PDF 다운로드 버튼 제공. 생성된 문서를 다양한 형식으로 내보내기.

**구현 노트**

- Markdown 다운로드: Content-Disposition 헤더
- PDF: 브라우저 print API 또는 라이브러리


### DOCS-GEN-F-202: 파일 단위 요약

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | GEN |

**설명**

개별 코드 파일 요약 생성. 파일 트리에서 파일을 선택하면 해당 파일의 역할 및 주요 함수 요약 표시.


### DOCS-GEN-F-203: 추천 읽기 순서/수정 전 주의점 생성

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | GEN |

**설명**

신입 개발자 기준 파일 읽기 순서 및 다음 행동 제안 제공. 코드베이스 파악을 위한 단계별 가이드 표시.


---

## Phase 2

> Phase 2 기능은 Phase 1 MVP 완성 이후 우선순위에 따라 구현합니다.

### DOCS-GEN-B-208: 추천 작업 생성

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | GEN |
| 우선순위 | v3 포지셔닝 신규 기능 |

**설명**

GitHub issue 추천. 신규 팀원에게 다음 행동 제안. 코드베이스 분석 결과를 기반으로 첫 기여 가능한 이슈 또는 작업을 자동 추천.


