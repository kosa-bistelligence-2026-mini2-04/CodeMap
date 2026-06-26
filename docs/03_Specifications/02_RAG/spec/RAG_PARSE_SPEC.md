# RAG PARSE 기능 명세서

> **도메인**: RAG | **모듈**: RAG-PARSE | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| RAG-PARSE-B-101 | 분석 결과 조회 API | Backend | Phase 1 |
| RAG-PARSE-B-201 | README 분석 | Backend | Phase 1 |
| RAG-PARSE-B-202 | 디렉토리 구조 분석 | Backend | Phase 1 |
| RAG-PARSE-B-203 | 핵심 파일 탐색 | Backend | Phase 1 |
| RAG-PARSE-B-204 | 설정 파일 탐색 | Backend | Phase 1 |
| RAG-PARSE-B-205 | 실행 방법 추론 | Backend | Phase 1 |
| RAG-PARSE-B-206 | 기술 스택 추론 | Backend | Phase 1 |
| RAG-PARSE-B-207 | AST 기반 코드 청킹 | Backend | Phase 1 |
| RAG-PARSE-B-208 | 파일 간 import 관계 분석 | Backend | Phase 1 |
| RAG-PARSE-B-209 | 계층형 Bottom-up 요약 로직 | Backend | Phase 1 |
| RAG-PARSE-B-210 | 구조 분석 agent 구현 | Backend | Phase 1 |
| RAG-PARSE-F-201 | 구조 분석 결과 표시 UI | Frontend | Phase 1 |
| RAG-PARSE-B-211 | 위험 신호 태깅 | Backend | Phase 2 |
| RAG-PARSE-B-212 | 기술 스택 점수화 | Backend | Phase 2 |
| RAG-PARSE-B-213 | 파일 line count / character count 추출 | Backend | Phase 2 |
| RAG-PARSE-F-202 | heatmap용 risk score 생성 | Frontend | Phase 2 |
| RAG-PARSE-F-203 | 파일 메타데이터 UI 노출 | Frontend | Phase 2 |

---

## Phase 1

### RAG-PARSE-B-101: 분석 결과 조회 API

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PARSE |

**설명**

`GET /api/analysis/{repo_id}` — 저장된 분석 결과(파일 트리, 기술 스택, 진입점 등)를 반환. 온보딩 문서 생성의 기반 데이터 제공.

**구현 노트**

- 분석 결과가 없으면 404 반환
- JSON 형태로 구조화된 분석 결과 반환


### RAG-PARSE-B-201: README 분석

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PARSE |

**설명**

README를 기반으로 프로젝트 목적 및 핵심 기능 추출. README 파일이 없는 경우 package.json/requirements.txt 기반으로 대체 분석.


### RAG-PARSE-B-202: 디렉토리 구조 분석

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PARSE |

**설명**

프로젝트 폴더 트리 구조 생성. 파일 시스템을 재귀적으로 탐색하여 디렉토리 계층 구조 및 파일 목록 생성.

**구현 노트**

- 필터링된 파일 목록 기반 트리 구성
- 각 디렉토리의 역할 추론 (예: `routes/` → API 라우터)


### RAG-PARSE-B-203: 핵심 파일 탐색

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PARSE |

**설명**

진입점(`main.py`, `App.tsx` 등) 자동 탐색. 프로젝트 실행의 시작점이 되는 파일을 자동으로 식별.

**구현 노트**

- 후보 파일명 목록: main.py, app.py, index.ts, App.tsx, server.js 등
- 파일 내용 분석으로 실제 진입점 확인


### RAG-PARSE-B-204: 설정 파일 탐색

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PARSE |

**설명**

`package.json`, `requirements.txt`, `docker-compose` 등 분석. 프로젝트 의존성, 실행 명령어, 환경 변수 추출.

**구현 노트**

- 탐색 대상: package.json, requirements.txt, Dockerfile, docker-compose.yml, .env.example
- 의존성 목록 및 실행 스크립트 추출


### RAG-PARSE-B-205: 실행 방법 추론

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PARSE |

**설명**

install/run command 자동 생성. 설정 파일 분석을 기반으로 로컬 실행 방법(설치 → 환경 변수 설정 → 실행)을 자동 추론.

**구현 노트**

- pnpm install + pnpm dev
- pip install -r requirements.txt + uvicorn main:app
- 등 패턴 기반 추론


### RAG-PARSE-B-206: 기술 스택 추론

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PARSE |

**설명**

package.json, requirements.txt, Dockerfile, docker-compose.yml 기반 프레임워크·런타임 자동 탐지.

**구현 노트**

- 프론트엔드: React, Next.js, Vue, Angular 등
- 백엔드: FastAPI, Django, Express, Spring 등
- DB: PostgreSQL, MySQL, MongoDB 등


### RAG-PARSE-B-207: AST 기반 코드 청킹

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PARSE |

**설명**

함수/클래스 단위 코드 분리. AST 파싱으로 코드의 의미 단위(함수, 클래스, 모듈)를 기준으로 청크 분할.

**구현 노트**

- Python: `ast` 모듈
- JS/TS: `tree-sitter` 라이브러리
- 최대 청크 토큰: 512 tokens, overlap: 50 tokens


### RAG-PARSE-B-208: 파일 간 import 관계 분석

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PARSE |

**설명**

의존 파일 목록 추출. AST 청킹, 의존성 트리, 엔트리포인트, 설정 파일 종합 분석 파이프라인. 파일 간 import/require 관계를 추적하여 의존성 그래프 구성.

**구현 노트**

- Python: `import` 문 분석
- JS/TS: `import`/`require` 분석
- `imports`, `imported_by` 메타데이터로 저장


### RAG-PARSE-B-209: 계층형 Bottom-up 요약 로직

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PARSE |

**설명**

파일 요약 → 폴더 요약 → 프로젝트 마스터 요약 순서로 상향식 요약 파이프라인 구성. Tree-Based RAG의 핵심 구현.

**구현 노트**

- 각 파일별 LLM 요약 생성
- 폴더 내 파일 요약 집계 → 폴더 요약 생성
- 전체 폴더 요약 집계 → 마스터 요약 생성


### RAG-PARSE-B-210: 구조 분석 agent 구현

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PARSE |

**설명**

파일 트리, stack, entrypoint, risk, heatmap 결과 반환. 코드베이스 전체 구조를 분석하는 통합 에이전트 구현.

**구현 노트**

- 출력: {file_tree, stack, entrypoints, risk_files, heatmap_data}
- 각 분석 결과를 ReportJsonResponse 필드에 통합


### RAG-PARSE-F-201: 구조 분석 결과 표시 UI

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | PARSE |

**설명**

파일 트리·기술 스택·진입점 탐지 결과를 화면에 시각적으로 표시. 분석 완료 후 사용자에게 코드베이스 구조 개요 제공.

**구현 노트**

- 파일 트리: 접히기/펼치기 가능한 트리 컴포넌트
- 기술 스택: 아이콘 배지 형태 표시
- 진입점: 강조 표시


---

## Phase 2

> Phase 2 기능은 Phase 1 MVP 완성 이후 우선순위에 따라 구현합니다.

### RAG-PARSE-B-211: 위험 신호 태깅

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PARSE |
| 우선순위 | Phase 2 기능 |

**설명**

auth, db, env, payment, external API, migration, security 키워드 탐지. 위험 파일 목록 생성하여 온보딩 문서에서 주의 파일로 강조.


### RAG-PARSE-B-212: 기술 스택 점수화

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PARSE |
| 우선순위 | 보류 |

### RAG-PARSE-B-213: 파일 line count / character count 추출

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PARSE |
| 관련 이슈 | Issue #167, Issue #168 |
| 우선순위 | Phase 2 기능 |

**설명**

파일 파싱 파이프라인에서 파일 단위 총 라인 수(`lineCount`)와 글자 수(`characterCount`)를 계산해 코드 노드 메타데이터와 `report_json.file_map`에 저장합니다. 이 값은 코드 규모 파악, 온보딩 지표, LLM 청킹/임베딩 비용 예측에 사용합니다.

**구현 노트**

- 텍스트 파일만 계산하며 바이너리/인코딩 실패 파일은 null 또는 제외 사유를 기록합니다.
- `lineCount`는 줄 구분자 기준 총 라인 수로 계산하고, 빈 파일은 0으로 둡니다.
- `characterCount`는 디코딩된 문자열 길이 기준으로 계산합니다.
- `PROJECT-REPO-API-010` 파일 읽기 API와 동일한 값이 반환되도록 parse metadata를 재사용합니다.
- 프론트 파일 트리 또는 코드 프리뷰에 선택적으로 노출합니다.

**완료 조건**

- 파일별 메타데이터에 line count와 character count가 저장됩니다.
- DashboardCharts와 Repository 파일 정보 UI에서 이 값을 사용할 수 있습니다.

### RAG-PARSE-F-203: 파일 메타데이터 UI 노출

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | PARSE |
| 관련 이슈 | Issue #167, Issue #168 |

**설명**

Repository 파일 트리, 코드 프리뷰, DashboardCharts가 `lineCount`와 `characterCount`를 선택적으로 표시할 수 있게 타입 계약을 확장합니다. 작은 화면에서는 기본 메타데이터를 숨기고 tooltip 또는 detail panel에서 확인할 수 있게 합니다.

**설명**

기술 스택 숙련도 및 품질 상세 메트릭 분석 기능. 현재 **보류** 상태.


### RAG-PARSE-F-202: heatmap용 risk score 생성

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | PARSE |
| 우선순위 | Phase 2 기능 |

**설명**

파일 크기, import 수, 위험 키워드, config 여부 기반 점수화. Frontend HeatmapChart 입력 데이터 생성.

