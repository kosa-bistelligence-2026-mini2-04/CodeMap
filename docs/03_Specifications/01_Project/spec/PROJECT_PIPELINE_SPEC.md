# PROJECT PIPELINE 기능 명세서

> **도메인**: PROJECT | **모듈**: PROJECT-PIPELINE | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase |
| --- | --- | --- | --- |
| PROJECT-PIPELINE-B-201 | 분석 단계 상태 관리 | Backend | Phase 2 |
| PROJECT-PIPELINE-B-202 | 비동기 깊은 분석 파이프라인 | Backend | Phase 2 |
| PROJECT-PIPELINE-B-203 | 파이프라인 외부 연동 | Backend | Phase 2 |
| PROJECT-PIPELINE-F-201 | 현재 분석 수준 안내 메시지 | Frontend | Phase 2 |
| PROJECT-PIPELINE-F-202 | 얕은/깊은 분석 분리 프로그레스 UI | Frontend | Phase 2 |
| PROJECT-PIPELINE-F-301 | 진행률 실시간 수신 | Frontend | Phase 2 |

---

## Phase 2

> Phase 2 기능은 Phase 1 MVP 완성 이후 우선순위에 따라 구현합니다.

### PROJECT-PIPELINE-B-201: 분석 단계 상태 관리

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PIPELINE |
| 우선순위 | Phase 2 기능 |

**설명**

repository 상태를 `shallow_done` / `deep_processing` / `deep_done`으로 분리 저장 및 전환 처리. 얕은 분석과 깊은 분석을 분리하여 단계별 진행 상태 추적.


### PROJECT-PIPELINE-B-202: 비동기 깊은 분석 파이프라인

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PIPELINE |
| 우선순위 | Phase 2 기능 |

**설명**

얕은 분석 완료 후 함수/클래스 요약, 의존성 추적, Map-Reduce를 백그라운드 비동기 병렬 처리. 깊은 분석은 얕은 분석 결과를 즉시 제공한 후 백그라운드에서 실행.

**구현 노트**

- asyncio 병렬 처리
- 깊은 분석 완료 시 알림 이벤트 발행


### PROJECT-PIPELINE-B-203: 파이프라인 외부 연동

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | PIPELINE |
| 우선순위 | 보류 — 초기 기능 명세 외 범위 |

**설명**

초기 기능 명세 외 범위로 현재 **보류** 상태. 외부 시스템(Slack, GitHub Actions 등)과의 연동 기능.


### PROJECT-PIPELINE-F-201: 현재 분석 수준 안내 메시지

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | PIPELINE |
| 우선순위 | Phase 2 기능 |

**설명**

심층 요약 요청 시 '현재 1차 분석만 완료 — 파일 트리, 주요 파일 목적, 실행 단서는 지금도 제공 가능'처럼 현재 가능한 범위를 투명하게 안내.


### PROJECT-PIPELINE-F-202: 얕은/깊은 분석 분리 프로그레스 UI

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | PIPELINE |
| 우선순위 | Phase 2 기능 |

**설명**

Phase 1 기본 상태 UI(로딩, 성공, 실패)를 얕은 분석(파일 트리, README)과 깊은 분석(함수 요약, 의존성 Map-Reduce) 2단계로 고도화한 프로그레스 바 표시.


### PROJECT-PIPELINE-F-301: 진행률 실시간 수신

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | PIPELINE |
| 우선순위 | Phase 2 기능 |

**설명**

SSE 또는 Polling으로 분석 진행률 수신 후 프로그레스 바에 반영.

**구현 노트**

- SSE 우선, 미지원 환경에서는 폴링 fallback
- 1초 간격 폴링


