# RAG PARSE 기능 명세서

> **도메인**: RAG | **모듈**: RAG-PARSE | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase | 우선순위 |
| --- | --- | --- | --- | --- |
| RAG-PARSE-B-101 | 분석 결과 조회 API | Backend | Phase 1 |  |
| RAG-PARSE-B-201 | README 분석 | Backend | Phase 2 |  |
| RAG-PARSE-B-202 | 디렉토리 구조 분석 | Backend | Phase 2 |  |
| RAG-PARSE-B-203 | 핵심 파일 탐색 | Backend | Phase 2 |  |
| RAG-PARSE-B-204 | 설정 파일 탐색 | Backend | Phase 2 |  |
| RAG-PARSE-B-205 | 실행 방법 추론 | Backend | Phase 2 |  |
| RAG-PARSE-B-206 | 기술 스택 추론 | Backend | Phase 2 |  |
| RAG-PARSE-B-207 | AST 기반 코드 청킹 | Backend | Phase 2 |  |
| RAG-PARSE-B-208 | 파일 간 import 관계 분석 | Backend | Phase 2 |  |
| RAG-PARSE-B-209 | 계층형 Bottom-up 요약 로직 | Backend | Phase 2 |  |
| RAG-PARSE-B-210 | 구조 분석 agent 구현 | Backend | Phase 2 |  |
| RAG-PARSE-F-201 | 구조 분석 결과 표시 UI | Frontend | Phase 2 |  |
| RAG-PARSE-B-211 | Service | Backend | Phase 2 | auth, db, env, payment, external API, migration, security 키워드 탐지. 위험 파일 목록 생성 |
| RAG-PARSE-B-212 | Service | Backend | Phase 2 | 기술 스택 숙련도 및 품질 상세 메트릭 분석 기능 보류 |
| RAG-PARSE-F-202 | UI Component | Frontend | Phase 2 | 파일 크기, import 수, 위험 키워드, config 여부 기반 점수화, frontend HeatmapChart 입력 데이터 생성 |

---

## Phase 1

### RAG-PARSE-B-101: 분석 결과 조회 API

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | RAG |
| 모듈명 | PARSE |

**설명**

`GET /api/analysis/{repo_id}` 반환


---

## Phase 2

### RAG-PARSE-B-201: README 분석

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | RAG |
| 모듈명 | PARSE |

**설명**

README를 기반으로 프로젝트 목적 및 핵심 기능 추출


### RAG-PARSE-B-202: 디렉토리 구조 분석

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | RAG |
| 모듈명 | PARSE |

**설명**

프로젝트 폴더 트리 구조 생성


### RAG-PARSE-B-203: 핵심 파일 탐색

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | RAG |
| 모듈명 | PARSE |

**설명**

entry point(`main.py`, `App.tsx` 등) 자동 탐색


### RAG-PARSE-B-204: 설정 파일 탐색

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | RAG |
| 모듈명 | PARSE |

**설명**

`package.json`, `requirements.txt`, `docker-compose` 등 분석


### RAG-PARSE-B-205: 실행 방법 추론

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | RAG |
| 모듈명 | PARSE |

**설명**

install/run command 자동 생성


### RAG-PARSE-B-206: 기술 스택 추론

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | RAG |
| 모듈명 | PARSE |

**설명**

package.json, requirements.txt, Dockerfile, docker-compose.yml 기반 프레임워크·런타임 자동 탐지


### RAG-PARSE-B-207: AST 기반 코드 청킹

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | RAG |
| 모듈명 | PARSE |

**설명**

함수/클래스 단위 코드 분리


### RAG-PARSE-B-208: 파일 간 import 관계 분석

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | RAG |
| 모듈명 | PARSE |

**설명**

의존 파일 목록 추출 [7. CODE-MAP ANALYSIS] AST 청킹, 의존성 트리, 엔트리포인트, 설정파일 종합 분석 파이프라인 간단히 파싱


### RAG-PARSE-B-209: 계층형 Bottom-up 요약 로직

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | RAG |
| 모듈명 | PARSE |

**설명**

파일 요약 → 폴더 요약 → 프로젝트 마스터 요약 순서로 상향식 요약 파이프라인 구성 (Tree-based RAG 핵심)


### RAG-PARSE-B-210: 구조 분석 agent 구현

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | RAG |
| 모듈명 | PARSE |

**설명**

파일 트리, stack, entrypoint, risk, heatmap 결과 반환


### RAG-PARSE-F-201: 구조 분석 결과 표시 UI

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | RAG |
| 모듈명 | PARSE |

**설명**

파일 트리·기술 스택·진입점 탐지 결과를 화면에 시각적으로 표시


### RAG-PARSE-B-211: Service

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | RAG |
| 소분류 ID | PARSE |
| 우선순위 | auth, db, env, payment, external API, migration, security 키워드 탐지. 위험 파일 목록 생성 |

**설명**

위험 신호 태깅


### RAG-PARSE-B-212: Service

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | RAG |
| 소분류 ID | PARSE |
| 우선순위 | 기술 스택 숙련도 및 품질 상세 메트릭 분석 기능 보류 |

**설명**

기술 스택 점수화


### RAG-PARSE-F-202: UI Component

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | RAG |
| 소분류 ID | PARSE |
| 우선순위 | 파일 크기, import 수, 위험 키워드, config 여부 기반 점수화, frontend HeatmapChart 입력 데이터 생성 |

**설명**

heatmap용 risk score 생성


