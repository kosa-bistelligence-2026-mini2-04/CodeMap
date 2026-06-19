# PROJECT LIST 기능 명세서

> **도메인**: PROJECT | **모듈**: PROJECT-LIST | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase | 우선순위 | 담당자 | 상태 |
| --- | --- | --- | --- | --- | --- | --- |
| PROJECT-LIST-B-101 | 레포 목록 조회 API | Backend | Phase 1 |  | 강 강영우 성 성민 신 | 시작 전 |
| PROJECT-LIST-F-101 | 분석 이력 목록 화면 | Frontend | Phase 1 |  | 강 강영우 성 성민 신 | 시작 전 |
| PROJECT-LIST-B-201 | 레포 크기, 파일 수 사전 검증 | Backend | Phase 2 |  | 강 강영우 성 성민 신 | 시작 전 |
| PROJECT-LIST-B-202 | 프로젝트 목록 조회 및 관리 | Backend | Phase 2 |  | 성 성민 신 강 강영우 | 시작 전 |
| PROJECT-LIST-B-301 | 분석 job metadata 저장 | Backend | Phase 2 |  | 성 성민 신 강 강영우 | 시작 전 |
| PROJECT-LIST-F-201 | store에서 job 목록 조회 | Frontend | Phase 2 |  | 성 성민 신 강 강영우 | 시작 전 |
| PROJECT-LIST-F-202 | job 상태 업데이트 | Frontend | Phase 2 |  | 성 성민 신 강 강영우 | 시작 전 |
| PROJECT-LIST-F-203 | 실패 job error 저장 | Frontend | Phase 2 |  | 성 성민 신 강 강영우 | 시작 전 |
| PROJECT-LIST-B-202 | Service | Backend | Phase 2 | 단일 레포 분석 우선으로 인한 보류 (UI/API) |  |  |
| PROJECT-LIST-B-301 | Repository | Backend | Phase 2 | job id, repo url, status, created_at, updated_at 저장 |  |  |
| PROJECT-LIST-F-201 | UI Component | Frontend | Phase 2 | frontend HistoryList 표시 가능 |  |  |
| PROJECT-LIST-F-202 | UI Component | Frontend | Phase 2 | queued/running/completed/failed 상태 저장, frontend가 최신 상태 재조회 가능 |  |  |
| PROJECT-LIST-F-203 | UI Component | Frontend | Phase 2 | exception message, failed agent, timestamp 저장, frontend에서 실패 원인 표시 가능 |  |  |

---

## Phase 1

### PROJECT-LIST-B-101: 레포 목록 조회 API

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 모듈명 | LIST |
| 담당자 | 강 강영우 성 성민 신 |
| 작업상태 | 시작 전 |

**설명**

전체 분석 이력 목록 반환


### PROJECT-LIST-F-101: 분석 이력 목록 화면

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | PROJECT |
| 모듈명 | LIST |
| 담당자 | 강 강영우 성 성민 신 |
| 작업상태 | 시작 전 |

**설명**

이미 분석한 레포 목록과 각 분석상태(완료,처리중,실패)를 조회하는 홈화면


---

## Phase 2

### PROJECT-LIST-B-201: 레포 크기, 파일 수 사전 검증

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 모듈명 | LIST |
| 담당자 | 강 강영우 성 성민 신 |
| 작업상태 | 시작 전 |

**설명**

clone 전 파일 수·용량이 제한 초과 여부 확인 및 초과 시 사용자 안내


### PROJECT-LIST-B-202: 프로젝트 목록 조회 및 관리

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 모듈명 | LIST |
| 담당자 | 성 성민 신 강 강영우 |
| 작업상태 | 시작 전 |

**설명**

이전에 사용자가 진행한 작업에 대한 조회, 삭제 기능


### PROJECT-LIST-B-301: 분석 job metadata 저장

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 모듈명 | LIST |
| 담당자 | 성 성민 신 강 강영우 |
| 작업상태 | 시작 전 |

**설명**

분석 결과물에 대한 생성 시간 저장


### PROJECT-LIST-F-201: store에서 job 목록 조회

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | PROJECT |
| 모듈명 | LIST |
| 담당자 | 성 성민 신 강 강영우 |
| 작업상태 | 시작 전 |

**설명**

이전 작업한 내용 확인 가능하게 프론트 구성


### PROJECT-LIST-F-202: job 상태 업데이트

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | PROJECT |
| 모듈명 | LIST |
| 담당자 | 성 성민 신 강 강영우 |
| 작업상태 | 시작 전 |

**설명**

작업 결과물에 대한 상태 확인가능하게 프론트 구성


### PROJECT-LIST-F-203: 실패 job error 저장

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | PROJECT |
| 모듈명 | LIST |
| 담당자 | 성 성민 신 강 강영우 |
| 작업상태 | 시작 전 |

**설명**

실패한 작업에 대한 프론트 구성


### PROJECT-LIST-B-202: Service

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 소분류 ID | LIST |
| 우선순위 | 단일 레포 분석 우선으로 인한 보류 (UI/API) |

**설명**

프로젝트 목록 조회 및 관리


### PROJECT-LIST-B-301: Repository

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 소분류 ID | LIST |
| 우선순위 | job id, repo url, status, created_at, updated_at 저장 |

**설명**

분석 job metadata 저장


### PROJECT-LIST-F-201: UI Component

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | PROJECT |
| 소분류 ID | LIST |
| 우선순위 | frontend HistoryList 표시 가능 |

**설명**

store에서 최근 job 목록 조회


### PROJECT-LIST-F-202: UI Component

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | PROJECT |
| 소분류 ID | LIST |
| 우선순위 | queued/running/completed/failed 상태 저장, frontend가 최신 상태 재조회 가능 |

**설명**

job 상태 업데이트


### PROJECT-LIST-F-203: UI Component

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | PROJECT |
| 소분류 ID | LIST |
| 우선순위 | exception message, failed agent, timestamp 저장, frontend에서 실패 원인 표시 가능 |

**설명**

실패 job error 저장


