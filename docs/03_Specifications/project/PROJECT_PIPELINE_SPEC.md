# PROJECT PIPELINE 기능 명세서

> **도메인**: PROJECT | **모듈**: PROJECT-PIPELINE | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase | 우선순위 |
| --- | --- | --- | --- | --- |
| PROJECT-PIPELINE-B-201 | Service | Backend | Phase 2 | repository상태를 shallo_done/deep_processing/deep_done으로 분리 저장 및 전환 처리 |
| PROJECT-PIPELINE-B-202 | Service | Backend | Phase 2 | 얕은 분석 완료후 함수/클래스 요약,의존성 추적,Map-Reduce를 백그라운드 비동기 병렬 처리 |
| PROJECT-PIPELINE-B-203 | Service | Backend | Phase 2 | 초기 기능 명세 외 범위로 보류 |
| PROJECT-PIPELINE-F-201 | UI Component | Frontend | Phase 2 | 심층 용약 요청시 “ ㅎ현재 1차분서만 완료 - 파일트리, 주요 파일목적, 실행 단서는 지금도 제공가능” 처럼 현재 가능한 범위를 투명하게 안내함 |
| PROJECT-PIPELINE-F-202 | UI Component | Frontend | Phase 2 | PHase1 기본 상태UI(로딩,성공,실패)를 얕은 분석 (파일트리,README)과 깊은 분석(함수 요약, 의존서으MAP-Reduce) 2단계로 고도화한 프로그레스바 표시 |
| PROJECT-PIPELINE-F-301 | API/Query | Frontend | Phase 2 | SSE 또는 Polling으로 분석 진행률 수신후 프로그레스 바에 반영 |

---

## Phase 2

### PROJECT-PIPELINE-B-201: Service

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 소분류 ID | PIPELINE |
| 우선순위 | repository상태를 shallo_done/deep_processing/deep_done으로 분리 저장 및 전환 처리 |

**설명**

분석 단계 상태 관리


### PROJECT-PIPELINE-B-202: Service

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 소분류 ID | PIPELINE |
| 우선순위 | 얕은 분석 완료후 함수/클래스 요약,의존성 추적,Map-Reduce를 백그라운드 비동기 병렬 처리 |

**설명**

비동기 깊은 분석 파이프라인


### PROJECT-PIPELINE-B-203: Service

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 소분류 ID | PIPELINE |
| 우선순위 | 초기 기능 명세 외 범위로 보류 |

**설명**

파이프라인 외부 연동


### PROJECT-PIPELINE-F-201: UI Component

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | PROJECT |
| 소분류 ID | PIPELINE |
| 우선순위 | 심층 용약 요청시 “ ㅎ현재 1차분서만 완료 - 파일트리, 주요 파일목적, 실행 단서는 지금도 제공가능” 처럼 현재 가능한 범위를 투명하게 안내함 |

**설명**

현재 분석 수준 안내 메시지


### PROJECT-PIPELINE-F-202: UI Component

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | PROJECT |
| 소분류 ID | PIPELINE |
| 우선순위 | PHase1 기본 상태UI(로딩,성공,실패)를 얕은 분석 (파일트리,README)과 깊은 분석(함수 요약, 의존서으MAP-Reduce) 2단계로 고도화한 프로그레스바 표시 |

**설명**

얕은/깊은 분석 분리 프로그레스 UI


### PROJECT-PIPELINE-F-301: API/Query

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | PROJECT |
| 소분류 ID | PIPELINE |
| 우선순위 | SSE 또는 Polling으로 분석 진행률 수신후 프로그레스 바에 반영 |

**설명**

진행률 실시간 수신


