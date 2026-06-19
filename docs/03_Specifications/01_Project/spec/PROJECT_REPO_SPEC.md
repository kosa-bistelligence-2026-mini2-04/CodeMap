# PROJECT REPO 기능 명세서

> **도메인**: PROJECT | **모듈**: PROJECT-REPO | **최종 업데이트**: 2026-06-19


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase | 담당자 | 작업 상태 |
| --- | --- | --- | --- | --- | --- |
| PROJECT-REPO-B-101 | 프로젝트 등록 API | Backend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-B-201 | Git Clone 처리 | Backend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-B-202 | 파일 필터링 | Backend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-B-203 | clone timeout 처리 | Backend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-B-204 | 전체 분석 순서 정의 | Backend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-B-205 | job별 event queue 관리 | Backend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-B-301 | Git 저장소 URL 검증 | Backend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-B-302 | 프로젝트 메타데이터 저장 | Backend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-F-101 | progress WebSocket endpoint 정리 | Frontend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-F-201 | GitHub URL 입력 UI | Frontend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-F-202 | 저장소 분석 요청 버튼 | Frontend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-F-203 | 분석 진행 상태 UI | Frontend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-B-303 | 중복 저장소 검사 | Backend | Phase 2 |  |  |

---

## Phase 1

### PROJECT-REPO-B-101: 프로젝트 등록 API

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | REPO |
| 담당자 | 김효, oosuhada |
| 작업상태 | 시작 전 |

**설명**

`POST /api/repo/analysis` — GitHub 저장소 URL을 받아 분석 작업을 등록하고 job_id를 발급. 내부적으로 URL 검증 → Clone → 파일 필터링 → Code Map → Doc Generation 순서로 비동기 처리. 각 단계 진행 상태는 WebSocket으로 실시간 push.

**구현 노트**

- 비동기 파이프라인 실행
- clone 완료 전 202 Accepted 즉시 반환
- branch 미입력 시 GitHub API의 default_branch 사용


### PROJECT-REPO-B-201: Git Clone 처리

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | REPO |
| 담당자 | 김효, oosuhada |
| 작업상태 | 시작 전 |

**설명**

서버 내부 임시 디렉토리에 저장소 복제. `git clone --depth 1` 옵션으로 얕은 clone 실행하여 속도 최적화.

**구현 노트**

- clone 경로: /tmp/codemap/{job_id}/
- `--depth 1` 옵션으로 최신 커밋만 clone
- branch 파라미터 지원


### PROJECT-REPO-B-202: 파일 필터링

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | REPO |
| 담당자 | 김효, oosuhada |
| 작업상태 | 시작 전 |

**설명**

`node_modules`, `.git`, `build`, `dist`, `venv`, `.next`, `.env`, `key`, 바이너리 파일 제외. 분석 대상 파일만 필터링하여 파싱 효율 향상.

**구현 노트**

- 필터링 제외 목록: node_modules/, .git/, build/, dist/, venv/, .next/, .env, key*, 바이너리 파일
- 지원 확장자: .py, .ts, .tsx, .js, .jsx, .java, .go


### PROJECT-REPO-B-203: clone timeout 처리

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | REPO |
| 담당자 | 김효, oosuhada |
| 작업상태 | 시작 전 |

**설명**

timeout seconds 설정, subprocess error capture, 실패 시 cleanup. clone이 설정 시간(기본 300초)을 초과하면 작업 중단 및 임시 디렉토리 자동 정리.

**구현 노트**

- asyncio.wait_for() 타임아웃
- 실패 시 /tmp/codemap/{job_id}/ 자동 삭제
- 에러 코드: CLONE_TIMEOUT (408)


### PROJECT-REPO-B-204: 전체 분석 순서 정의

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | REPO |
| 담당자 | 김효, oosuhada |
| 작업상태 | 시작 전 |

**설명**

clone → code map → doc generation → onboarding guide → report 저장 순서로 전체 분석 파이프라인 실행 및 조율.

**구현 노트**

- `POST /api/repo/analysis/{job_id}/start` 엔드포인트
- 각 단계 성공 확인 후 다음 단계 진행
- 단계별 진행 상태 WebSocket 이벤트 발행


### PROJECT-REPO-B-205: job별 event queue 관리

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | REPO |
| 담당자 | 김효, oosuhada |
| 작업상태 | 시작 전 |

**설명**

publish, subscribe, timeout, cleanup 구현. 각 분석 job에 대해 독립적인 WebSocket 이벤트 큐를 관리하여 단계 전환 시 이벤트 발행.

**구현 노트**

- Redis pub/sub 또는 인메모리 asyncio.Queue
- job_id 기반 채널 분리
- completed/failed 이후 큐 자동 cleanup


### PROJECT-REPO-B-301: Git 저장소 URL 검증

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | REPO |
| 담당자 | 김효, oosuhada |
| 작업상태 | 시작 전 |

**설명**

GitHub URL 형식 유효성 검사 및 예외 처리, job_id 반환. `POST /api/repo/validate` — 입력된 URL이 유효한 GitHub 저장소인지 실제 접근 가능 여부까지 확인.

**구현 노트**

- 정규식으로 github.com URL 패턴 검사
- GitHub REST API로 저장소 존재 여부 확인
- Private repo 접근 불가 안내


### PROJECT-REPO-B-302: 프로젝트 메타데이터 저장

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | REPO |
| 담당자 | 김효, oosuhada |
| 작업상태 | 시작 전 |

**설명**

repo_name, owner, branch, clone_path 저장. 분석 완료 후 저장소 메타데이터를 DB에 저장하여 이후 조회 시 활용.

**구현 노트**

- `projects` 테이블: id, repo_url, repo_name, owner, branch, clone_path, status, created_at
- GitHub API 응답으로 repo_name, owner, default_branch 추출


### PROJECT-REPO-F-101: progress WebSocket endpoint 정리

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | REPO |
| 담당자 | 김효, oosuhada |
| 작업상태 | 시작 전 |

**설명**

frontend ProgressPanel에 이벤트 전달. `/ws/progress/{job_id}` 연결, subscribe, disconnect cleanup 처리.

**구현 노트**

- useEffect로 WebSocket 연결 관리
- 컴포넌트 언마운트 시 ws.close() 호출
- 비정상 종료 시 최대 3회 재연결


### PROJECT-REPO-F-201: GitHub URL 입력 UI

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | REPO |
| 담당자 | 김효, oosuhada |
| 작업상태 | 시작 전 |

**설명**

사용자가 GitHub 저장소 URL을 입력할 수 있는 입력 폼 제공. 실시간 유효성 검사로 잘못된 형식 즉시 피드백.

**구현 노트**

- 정규식 기반 URL 형식 즉시 검사
- 오류 메시지: 빨간 테두리 + 안내 텍스트


### PROJECT-REPO-F-202: 저장소 분석 요청 버튼

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | REPO |
| 담당자 | 김효, oosuhada |
| 작업상태 | 시작 전 |

**설명**

URL 검증 후 Backend API 호출. 분석 시작 버튼 클릭 시 URL 유효성 검사 → 분석 요청 API 호출 → ProgressPanel로 전환.

**구현 노트**

- URL 유효하지 않으면 버튼 비활성화
- 요청 중 중복 클릭 방지 (로딩 스피너)


### PROJECT-REPO-F-203: 분석 진행 상태 UI

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | REPO |
| 담당자 | 김효, oosuhada |
| 작업상태 | 시작 전 |

**설명**

Clone / 분석 진행 상태(로딩, 성공, 실패) 표시. WebSocket으로 수신한 이벤트를 단계별 진행 바와 상태 메시지로 시각화.

**구현 노트**

- 단계: CLONE → CODE_MAP → DOC_GEN → ONBOARDING → REPORT
- 단계별 progress 범위: CLONE 0-20%, CODE_MAP 21-50%, DOC_GEN 51-70%, ONBOARDING 71-90%, REPORT 91-100%


---

## Phase 2

> Phase 2 기능은 Phase 1 MVP 완성 이후 우선순위에 따라 구현합니다.

### PROJECT-REPO-B-303: 중복 저장소 검사

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | REPO |

**설명**

이미 분석된 URL 여부 확인. 동일 저장소 재분석 시 기존 결과를 재활용하여 중복 분석 방지.

**구현 노트**

- `GET /api/repo/check-duplicate?repo_url={url}`
- DB에서 repo_url 기준 조회
- 기존 project_id 반환으로 재분석 대신 기존 결과 재활용


