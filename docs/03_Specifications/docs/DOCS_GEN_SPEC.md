# DOCS GEN 기능 명세서

> **도메인**: DOCS | **모듈**: DOCS-GEN | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase | 우선순위 |
| --- | --- | --- | --- | --- |
| DOCS-GEN-B-101 | 가이드북 조회 API | Backend | Phase 1 |  |
| DOCS-GEN-F-101 | 온보딩 문서 화면 | Frontend | Phase 1 |  |
| DOCS-GEN-B-201 | 문서 요약 agent 구현 | Backend | Phase 2 |  |
| DOCS-GEN-B-202 | 온보딩 guide agent 구현 | Backend | Phase 2 |  |
| DOCS-GEN-B-203 | 폴더 단위 요약 | Backend | Phase 2 |  |
| DOCS-GEN-B-204 | 프로젝트 마스터 리포트 생성 | Backend | Phase 2 |  |
| DOCS-GEN-B-205 | README 기반 프로젝트 소개 생성 | Backend | Phase 2 |  |
| DOCS-GEN-B-206 | 핵심 실행 플로우 설명 | Backend | Phase 2 |  |
| DOCS-GEN-B-207 | 문서 재생성 | Backend | Phase 2 |  |
| DOCS-GEN-B-301 | Markdown 저장 | Backend | Phase 2 |  |
| DOCS-GEN-F-201 | 문서 다운로드 UI | Frontend | Phase 2 |  |
| DOCS-GEN-F-202 | 파일 단위 요약 | Frontend | Phase 2 |  |
| DOCS-GEN-F-203 | 추천 읽기 순서/수정 전 주의점 생성 | Frontend | Phase 2 |  |
| DOCS-GEN-B-208 | Service | Backend | Phase 2 | github issue 추천. 신규 팀원에게 다음 행동 제안 |

---

## Phase 1

### DOCS-GEN-B-101: 가이드북 조회 API

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | DOCS |
| 모듈명 | GEN |

**설명**

`GET /api/docs/{repo_id}` 생성된 온보딩 가이드북 Markdown 반환


### DOCS-GEN-F-101: 온보딩 문서 화면

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | DOCS |
| 모듈명 | GEN |

**설명**

JSON 기반 결과 렌더링


---

## Phase 2

### DOCS-GEN-B-201: 문서 요약 agent 구현

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | DOCS |
| 모듈명 | GEN |

**설명**

README, config, package, route 파일 기반 프로젝트 설명 생성


### DOCS-GEN-B-202: 온보딩 guide agent 구현

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | DOCS |
| 모듈명 | GEN |

**설명**

읽을 순서, 수정 시작점, 위험 파일, 추천 task 생성


### DOCS-GEN-B-203: 폴더 단위 요약

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | DOCS |
| 모듈명 | GEN |

**설명**

하위 파일 요약 기반 디렉토리 설명 생성


### DOCS-GEN-B-204: 프로젝트 마스터 리포트 생성

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | DOCS |
| 모듈명 | GEN |

**설명**

최종 온보딩 문서 통합


### DOCS-GEN-B-205: README 기반 프로젝트 소개 생성

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | DOCS |
| 모듈명 | GEN |

**설명**

프로젝트 목적 및 핵심 기능 요약


### DOCS-GEN-B-206: 핵심 실행 플로우 설명

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | DOCS |
| 모듈명 | GEN |

**설명**

요청 흐름 및 핵심 구조 설명


### DOCS-GEN-B-207: 문서 재생성

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | DOCS |
| 모듈명 | GEN |

**설명**

기존 분석 기반 재생성 기능


### DOCS-GEN-B-301: Markdown 저장

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | DOCS |
| 모듈명 | GEN |

**설명**

생성 결과 DB 저장


### DOCS-GEN-F-201: 문서 다운로드 UI

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | DOCS |
| 모듈명 | GEN |

**설명**

JSON → Markdown / HTML → PDF 다운로드 버튼 제공


### DOCS-GEN-F-202: 파일 단위 요약

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | DOCS |
| 모듈명 | GEN |

**설명**

개별 코드 파일 요약 생성


### DOCS-GEN-F-203: 추천 읽기 순서/수정 전 주의점 생성

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | DOCS |
| 모듈명 | GEN |

**설명**

신입 개발자 기준 파일 읽기 순서 및 다음행동 제안 제공


### DOCS-GEN-B-208: Service

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | DOCS |
| 소분류 ID | GEN |
| 우선순위 | github issue 추천. 신규 팀원에게 다음 행동 제안 |

**설명**

추천 작업 생성


