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
| PROJECT-REPO-B-206 | Windows 로컬 업로드 경로 방어 | Backend | Phase 1 | - | 제안 |
| PROJECT-REPO-B-301 | Git 저장소 URL 검증 | Backend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-B-302 | 프로젝트 메타데이터 저장 | Backend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-B-401 | 분석 생성 시 개인/팀 visibility 저장 | Backend | Phase 2 |  | 제안 |
| PROJECT-REPO-B-402 | job scoped 파일 코드 읽기 API | Backend | Phase 2 | - | 제안 |
| PROJECT-REPO-F-101 | progress WebSocket endpoint 정리 | Frontend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-F-201 | GitHub URL 입력 UI | Frontend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-F-202 | 저장소 분석 요청 버튼 | Frontend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-F-203 | 분석 진행 상태 UI | Frontend | Phase 1 | 김효, oosuhada | 시작 전 |
| PROJECT-REPO-F-204 | 로컬 업로드 제외 사유 표시 UI | Frontend | Phase 1 | - | 제안 |
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
- Phase 2 팀 기능에서는 `visibility`, `team_id`, `created_by_user_id`를 함께 저장하여 개인 private 분석과 팀 공유 분석을 구분


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

### PROJECT-REPO-B-206: Windows 로컬 업로드 경로 방어

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | REPO |
| 관련 이슈 | Issue #156 |
| 작업상태 | 제안 |

**설명**

로컬 프로젝트 폴더 업로드 시 Windows 경로 길이 제한, 예약 파일명, trailing dot/space, 제어문자/금지문자, symlink/junction, 권한 부족 파일 때문에 전체 업로드가 실패하지 않도록 프론트와 백엔드에 동일한 경로 정책을 둡니다.

**구현 노트**

- 프론트 후보 수집 단계에서 전체 경로 길이, 세그먼트 길이, 예약명(`CON`, `PRN`, `AUX`, `NUL`, `COM1` 등), 금지문자, trailing dot/space를 사전 분류합니다.
- 백엔드 `save_local_upload()`도 동일 정책을 재검증하여 브라우저 차이나 우회 요청을 방어합니다.
- `OSError`, `PermissionError`, 파일명/경로 초과 오류는 `INVALID_LOCAL_PATH`, `LOCAL_UPLOAD_PERMISSION_DENIED`, `LOCAL_UPLOAD_LIMIT_EXCEEDED`처럼 사용자에게 설명 가능한 오류로 변환합니다.
- 업로드 전/후 응답에는 `acceptedCount`, `skippedCount`, `skippedByReason`을 포함해 대형 저장소에서 제외 사유를 확인할 수 있게 합니다.

**완료 조건**

- Windows Chrome/Edge에서 깊은 경로, 예약 파일명, 권한 불가 파일, symlink/junction 포함 폴더를 선택해도 전체 화면이 무조건 실패하지 않습니다.
- 실패 시 문제 파일 경로 또는 사유 카테고리를 사용자에게 보여줍니다.
- macOS 로컬 폴더 업로드와 GitHub URL 분석 흐름이 회귀하지 않습니다.


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

- `analysis_jobs` 테이블: id, repo_url, repo_name, owner, branch, status, progress, report_json, created_at, updated_at
- Phase 2 확장: created_by_user_id, visibility(private/team), team_id
- GitHub API 응답으로 repo_name, owner, default_branch 추출


### PROJECT-REPO-F-101: progress WebSocket endpoint 정리

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | REPO |
| 담당자 | 김효, oosuhada |
| 작업상태 | 시작 전 |

**설명**

frontend ProgressPanel에 이벤트 전달. 실제 구현 경로는 `/ws/list/progress/{job_id}` 이며, SSE 대체 채널은 `/api/repo/analysis/{job_id}/events` 이다. 연결, subscribe, disconnect cleanup 처리.

> Phase 2 격리: WebSocket/SSE는 Authorization 헤더를 보낼 수 없으므로 `?token={access_token}` query param으로 인증한다. private/team job은 `can_access_job` 정책(PROJECT_TEAM_SPEC)을 통과한 사용자만 진행률을 구독할 수 있다.

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

### PROJECT-REPO-F-204: 로컬 업로드 제외 사유 표시 UI

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | REPO |
| 관련 이슈 | Issue #156 |
| 작업상태 | 제안 |

**설명**

로컬 폴더 선택 후 업로드 후보 파일을 만들 때 분석 가능한 파일과 제외된 파일을 사유별로 보여줍니다. 단순 `skippedCount`가 아니라 사용자가 조치할 수 있는 카테고리별 안내가 필요합니다.

**구현 노트**

- 제외 사유 예: `ignored_directory`, `too_many_files`, `too_large_file`, `windows_reserved_name`, `path_too_long`, `invalid_character`, `permission_denied`, `symlink_or_junction`
- 대형 저장소는 업로드 전 "업로드 가능 N개 / 제외 M개"를 확인할 수 있게 합니다.
- 개별 파일명은 민감정보가 될 수 있으므로 전체 경로를 장황하게 노출하지 않고 basename과 사유 중심으로 표시합니다.


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
- Phase 2에서는 visibility와 team_id까지 포함해 중복 기준을 분리합니다. 같은 repo URL이라도 사용자 private 분석과 팀 공유 분석은 서로 자동 공유하지 않습니다.

### PROJECT-REPO-B-401: 분석 생성 시 개인/팀 visibility 저장

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | REPO |
| 관련 명세 | `PROJECT_TEAM_SPEC.md`, Issue #164 |

**설명**

분석 생성 시 현재 사용자의 개인 workspace 또는 선택한 팀 workspace를 명시적으로 저장합니다. 이 값은 LIST 분석 이력 조회와 CHAT run/thread 접근 권한의 기준이 됩니다.

**구현 노트**

- 기본값은 `visibility='private'`, `team_id=NULL`
- `visibility='team'` 요청은 current user가 해당 team의 active member인지 먼저 확인
- local upload 분석과 GitHub URL 분석 모두 동일한 ownership 필드를 저장
- 권한 실패 시 403 `TEAM_ACCESS_DENIED`

### PROJECT-REPO-B-402: job scoped 파일 코드 읽기 API

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | REPO |
| 관련 이슈 | Issue #160, Issue #161 |
| 작업상태 | 제안 |

**설명**

`/analyze`의 Repository 패널과 채팅 근거 클릭에서 실제 코드를 확인할 수 있도록, 분석 job 기준으로 안전하게 파일 내용을 읽는 API를 제공합니다.

**구현 노트**

- API 예: `GET /api/repo/analysis/{job_id}/files?path=src/app/page.tsx`
- `path`는 repo 내부 상대 경로만 허용하고, `..`, 절대경로, symlink 탈출, clone workspace 외부 접근을 차단합니다.
- 텍스트 파일만 반환하며 바이너리/대용량 파일은 `UNSUPPORTED_FILE_TYPE`, `FILE_TOO_LARGE`로 거절합니다.
- 응답에는 `path`, `content`, `encoding`, `lineCount`, `characterCount`, `truncated`, `maxBytes`를 포함합니다.
- Phase 2 팀 기능과 함께 적용할 경우 `job_id` 접근 권한은 `PROJECT_TEAM_SPEC.md`의 private/team visibility 정책을 따릅니다.

**완료 조건**

- Repository 파일 클릭 시 실제 파일 내용이 표시됩니다.
- 채팅 근거 클릭 시 파일과 line range를 함께 전달해 해당 줄로 이동할 수 있습니다.
- 허용되지 않는 경로, 바이너리, 대용량 파일은 안전한 오류로 표시됩니다.
