# PROJECT REPO 기능 명세서

> **도메인**: PROJECT | **모듈**: PROJECT-REPO | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase | 우선순위 | 담당자 | 상태 |
| --- | --- | --- | --- | --- | --- | --- |
| PROJECT-REPO-B-101 | 프로젝트 등록 API | Backend | Phase 1 |  | 김효 oosuhada | 시작 전 |
| PROJECT-REPO-F-101 | progress WebSocket endpoint 정리 | Frontend | Phase 1 |  | 김효 oosuhada | 시작 전 |
| PROJECT-REPO-B-201 | Git Clone 처리 | Backend | Phase 2 |  | 김효 oosuhada | 시작 전 |
| PROJECT-REPO-B-202 | 파일 필터링 | Backend | Phase 2 |  | 김효 oosuhada | 시작 전 |
| PROJECT-REPO-B-203 | clone timeout 처리 | Backend | Phase 2 |  | 김효 oosuhada | 시작 전 |
| PROJECT-REPO-B-204 | 전체 분석 순서 정의 | Backend | Phase 2 |  | 김효 oosuhada | 시작 전 |
| PROJECT-REPO-B-205 | job별 event queue 관리 | Backend | Phase 2 |  | 김효 oosuhada | 시작 전 |
| PROJECT-REPO-B-301 | Git 저장소 URL 검증 | Backend | Phase 2 |  | 김효 oosuhada | 시작 전 |
| PROJECT-REPO-B-302 | 프로젝트 메타데이터 저장 | Backend | Phase 2 |  | 김효 oosuhada | 시작 전 |
| PROJECT-REPO-F-201 | GitHub URL 입력 UI | Frontend | Phase 2 |  | 김효 oosuhada | 시작 전 |
| PROJECT-REPO-F-202 | 저장소 분석 요청 버튼 | Frontend | Phase 2 |  | 김효 oosuhada | 시작 전 |
| PROJECT-REPO-F-203 | 분석 진행 상태 UI | Frontend | Phase 2 |  | 김효 oosuhada | 시작 전 |
| PROJECT-REPO-B-303 | Repository | Backend | Phase 2 | 이미 분석된 URL 여부 확인 |  |  |

---

## Phase 1

### PROJECT-REPO-B-101: 프로젝트 등록 API

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 모듈명 | REPO |
| 담당자 | 김효 oosuhada |
| 작업상태 | 시작 전 |

**설명**

`POST /api/analysis` 요청 처리


### PROJECT-REPO-F-101: progress WebSocket endpoint 정리

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | PROJECT |
| 모듈명 | REPO |
| 담당자 | 김효 oosuhada |
| 작업상태 | 시작 전 |

**설명**

frontend ProgressPanel에 이벤트 전달, /ws/progress/{job_id} 연결, subscribe, disconnect cleanup


---

## Phase 2

### PROJECT-REPO-B-201: Git Clone 처리

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 모듈명 | REPO |
| 담당자 | 김효 oosuhada |
| 작업상태 | 시작 전 |

**설명**

서버 내부 임시 디렉토리에 저장소 복제


### PROJECT-REPO-B-202: 파일 필터링

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 모듈명 | REPO |
| 담당자 | 김효 oosuhada |
| 작업상태 | 시작 전 |

**설명**

`node_modules`, `.git`, `build`, `dist`, 'venv', '.next', '.env', 'key' 바이너리 파일 제외


### PROJECT-REPO-B-203: clone timeout 처리

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 모듈명 | REPO |
| 담당자 | 김효 oosuhada |
| 작업상태 | 시작 전 |

**설명**

timeout seconds 설정, subprocess error capture, 실패 시 cleanup


### PROJECT-REPO-B-204: 전체 분석 순서 정의

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 모듈명 | REPO |
| 담당자 | 김효 oosuhada |
| 작업상태 | 시작 전 |

**설명**

clone → code map → doc generation → onboarding guide → report 저장


### PROJECT-REPO-B-205: job별 event queue 관리

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 모듈명 | REPO |
| 담당자 | 김효 oosuhada |
| 작업상태 | 시작 전 |

**설명**

publish, subscribe, timeout, cleanup 구현


### PROJECT-REPO-B-301: Git 저장소 URL 검증

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 모듈명 | REPO |
| 담당자 | 김효 oosuhada |
| 작업상태 | 시작 전 |

**설명**

GitHub URL 형식 유효성 검사 및 예외 처리, job_id 반환


### PROJECT-REPO-B-302: 프로젝트 메타데이터 저장

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 모듈명 | REPO |
| 담당자 | 김효 oosuhada |
| 작업상태 | 시작 전 |

**설명**

repo_name, owner, branch, clone_path 저장


### PROJECT-REPO-F-201: GitHub URL 입력 UI

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | PROJECT |
| 모듈명 | REPO |
| 담당자 | 김효 oosuhada |
| 작업상태 | 시작 전 |

**설명**

사용자가 GitHub 저장소 URL을 입력할 수 있는 입력 폼 제공


### PROJECT-REPO-F-202: 저장소 분석 요청 버튼

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | PROJECT |
| 모듈명 | REPO |
| 담당자 | 김효 oosuhada |
| 작업상태 | 시작 전 |

**설명**

URL 검증 후 Backend API 호출


### PROJECT-REPO-F-203: 분석 진행 상태 UI

| 항목 | 내용 |
| --- | --- |
| 계층 | Frontend |
| 대분류 | PROJECT |
| 모듈명 | REPO |
| 담당자 | 김효 oosuhada |
| 작업상태 | 시작 전 |

**설명**

Clone / 분석 진행 상태(로딩, 성공, 실패) 표시


### PROJECT-REPO-B-303: Repository

| 항목 | 내용 |
| --- | --- |
| 계층 | Backend |
| 대분류 | PROJECT |
| 소분류 ID | REPO |
| 우선순위 | 이미 분석된 URL 여부 확인 |

**설명**

중복 저장소 검사


