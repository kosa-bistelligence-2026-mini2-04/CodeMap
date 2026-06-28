# PROJECT REPO API 명세서

> **최종 업데이트**: 2026-06-26


## API 목록

| API ID | Method | Endpoint | 목적 | 담당 | 상태 |
| --- | --- | --- | --- | --- | --- |
| PROJECT-REPO-API-001 | `POST` | `/api/repo/analysis` | 저장소 분석 작업 생성 | oosuhada | 완료 |
| PROJECT-REPO-API-002 | `POST` | `/api/repo/validate` | GitHub URL 형식 및 접근 가능 여부 검증 | 김효 | 완료 |
| PROJECT-REPO-API-003 | `GET` | `/api/repo/analysis/{job_id}` | 분석 작업 상태 및 메타데이터 조회 | oosuhada | 완료 |
| PROJECT-REPO-API-004 | `POST` | `/api/repo/analysis/{job_id}/clone` | 특정 job 기준 저장소 clone 실행 | 김효 | 완료 |
| PROJECT-REPO-API-005 | `GET (SSE)` | `/api/repo/analysis/{job_id}/events` | 분석 진행 상태 이벤트 스트림 수신 (SSE) | oosuhada | 완료 |
| PROJECT-REPO-API-006 | `WS` | `/ws/progress/{job_id}` | WebSocket 기반 분석 진행 상태 수신 | oosuhada | 완료 |
| PROJECT-REPO-API-007 | `POST` | `/api/repo/analysis/{job_id}/start` | clone 이후 전체 분석 파이프라인 시작 | oosuhada | 완료 |
| PROJECT-REPO-API-008 | `DELETE` | `/api/repo/analysis/{job_id}/workspace` | 실패/취소 시 임시 clone 디렉토리 cleanup | 김효 | 완료 |
| PROJECT-REPO-API-009 | `POST` | `/api/repo/analysis/local` | 로컬 폴더 업로드 분석 작업 생성 | - | 제안 |
| PROJECT-REPO-API-010 | `GET` | `/api/repo/analysis/{job_id}/files` | 분석 job scoped 파일 코드 읽기 | - | 제안 |

---

## PROJECT-REPO-API-001: 저장소 분석 작업 생성

GitHub 저장소 URL을 받아 분석 작업을 등록하고 job_id를 발급. 내부적으로 URL 검증 → Clone → 파일 필터링 → Code Map → Doc Generation → Onboarding Guide → Report 저장 순서로 비동기 처리. 각 단계 진행 상태는 WebSocket(`/ws/progress/{job_id}`)으로 실시간 push.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `POST` |
| Endpoint | `/api/repo/analysis` |
| 관련 기능 ID | PROJECT-REPO-B-101, PROJECT-REPO-B-303, PROJECT-REPO-F-202 |
| 담당자 | oosuhada |
| 상태 | 완료 |

### 요청 (Request)

**Request Body**

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| repoUrl | String | Y | - | 분석할 GitHub 저장소 URL (https://github.com/owner/repo 형식) |
| branch | String | 선택 | 저장소 기본 브랜치 | 분석 대상 브랜치 |
| visibility | String | 선택 | private | Phase 2: `private` 또는 `team` |
| teamId | UUID | 조건부 | null | Phase 2: `visibility=team`일 때 공유 대상 팀 ID |

```json
{
  "repoUrl": "https://github.com/user/repo",
  "branch": "main",
  "visibility": "private"
}
```

### 응답 (Response)

**성공 응답 — 201 Created**

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| code | Integer | 201 |
| message | String | "created" |
| data.jobId | String (UUID) | 발급된 분석 작업 고유 ID |
| data.repoName | String | 저장소 이름 |
| data.owner | String | 저장소 소유자 |
| data.branch | String | 분석 대상 브랜치 |
| data.status | String | 초기 상태: IN_PROGRESS |
| data.createdAt | String (ISO 8601) | 작업 생성 시각 |

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 400 | INVALID_REPO_URL | GitHub URL 형식이 올바르지 않음 |
| 403 | TEAM_ACCESS_DENIED | Phase 2: 지정한 팀에 분석을 생성할 권한이 없음 |
| 404 | REPOSITORY_NOT_FOUND | 저장소가 없거나 접근 불가 (private/삭제) |
| 408 | CLONE_TIMEOUT | clone 제한 시간 초과 |
| 409 | ALREADY_IN_PROGRESS | 동일 저장소 분석이 이미 진행 중 |
| 413 | FILE_LIMIT_EXCEEDED | 실제 파일 수 또는 용량 제한 초과 |
| 413 | LOCAL_UPLOAD_LIMIT_EXCEEDED | Phase 2: 로컬 업로드 파일 수/전체 용량/단일 파일 크기 제한 초과 |
| 422 | REPO_LIMIT_EXCEEDED | Clone 전 GitHub API 기준 용량 초과 |
| 500 | CLONE_FAILED | clone 중 subprocess 오류 발생 |
| 500 | WORKSPACE_CLEANUP_FAILED | 임시 디렉토리 삭제 실패 (내부 알람 발송) |

> **비고**: branch 미입력 시 GitHub REST API `GET /repos/{owner}/{repo}`의 `default_branch` 필드 사용. 분석 진행 상태는 WebSocket `/ws/progress/{job_id}`로 실시간 수신. Phase 2 팀 기능의 visibility/teamId 계약은 `PROJECT_TEAM_SPEC.md`를 따른다.


---

## PROJECT-REPO-API-002: GitHub URL 형식 및 접근 가능 여부 검증

입력된 GitHub 저장소 URL의 형식 유효성을 검사하고, 실제 접근 가능 여부를 확인. Clone 이전 단계에서 호출되며, 검증 통과 시 저장소 기본 정보를 반환. 유효하지 않거나 접근 불가한 경우 즉시 오류를 반환하여 불필요한 Clone을 방지.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `POST` |
| Endpoint | `/api/repo/validate` |
| 관련 기능 ID | PROJECT-REPO-B-301, PROJECT-REPO-F-201 |
| 담당자 | 김효 |
| 상태 | 완료 |

### 요청 (Request)

**Request Body**

| 필드명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| repoUrl | String | Y | 검증할 GitHub 저장소 URL |

### 응답 (Response)

**성공 응답 — 200 OK**

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| code | Integer | 200 |
| message | String | "success" |
| data.valid | Boolean | 검증 통과 여부 (true) |
| data.repoName | String | 저장소 이름 |
| data.owner | String | 저장소 소유자 |
| data.defaultBranch | String | 저장소 기본 브랜치 |
| data.isPrivate | Boolean | private 저장소 여부 |

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 400 | INVALID_REPO_URL | GitHub URL 형식이 올바르지 않음 |
| 404 | REPOSITORY_NOT_FOUND | 저장소가 없거나 접근 불가 (private/삭제) |
| 500 | GITHUB_API_ERROR | GitHub API 호출 중 오류 발생 |

> **비고**: 이 API는 `POST /api/repo/analysis` 호출 전 선택적으로 사용 가능. 분석 등록 API 내부에서도 동일한 검증이 수행됨.


---

## PROJECT-REPO-API-003: 분석 작업 상태 및 메타데이터 조회

job_id에 해당하는 분석 작업의 현재 상태(IN_PROGRESS / COMPLETED / FAILED)와 저장소 메타데이터를 반환. 폴링 방식으로 진행 상태를 확인할 때 사용하며, 실시간 수신은 WebSocket(API-006)을 권장.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `GET` |
| Endpoint | `/api/repo/analysis/{job_id}` |
| 관련 기능 ID | PROJECT-REPO-B-302 |
| 담당자 | oosuhada |
| 상태 | 완료 |

### 요청 (Request)

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| job_id | String (UUID) | Y | POST /api/repo/analysis 응답의 jobId 값 |

### 응답 (Response)

**성공 응답 — 200 OK**

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| code | Integer | 200 |
| message | String | "success" |
| data.jobId | String (UUID) | 분석 작업 고유 ID |
| data.repoName | String | 저장소 이름 |
| data.owner | String | 저장소 소유자 |
| data.branch | String | 분석 대상 브랜치 |
| data.clonePath | String | 서버 내 임시 clone 경로 (참조용) |
| data.status | String | 현재 상태: IN_PROGRESS / COMPLETED / FAILED |
| data.reportReady | Boolean | Issue #178: 분석 리포트 표시 가능 여부 |
| data.ragReady | Boolean | Issue #178: RAG 임베딩/인덱싱 완료 여부 |
| data.chatReady | Boolean | Issue #178: Chat run 생성 가능 여부 |
| data.indexingStatus | String | Issue #178: `pending`, `running`, `completed`, `failed` |
| data.indexingMessage | String \| null | Issue #178: RAG/Chat 준비 상태 사용자 안내 문구 |
| data.createdAt | String (ISO 8601) | 작업 생성 시각 |
| data.updatedAt | String (ISO 8601) | 마지막 상태 변경 시각 |

> Issue #178: `status=COMPLETED`는 report 생성 완료를 의미할 수 있으므로, Chat 사용 가능 여부는 `ragReady`와 `chatReady`를 별도로 확인합니다. `reportReady=true`, `ragReady=false`인 경우 `/analyze`는 리포트를 표시하고 Chat 영역에 인덱싱 중 상태를 보여줍니다.

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 404 | JOB_NOT_FOUND | 존재하지 않는 job_id |
| 500 | INTERNAL_ERROR | 서버 내부 오류 |


---

## PROJECT-REPO-API-004: 특정 job 기준 저장소 clone 실행

clone 전 파일 수·용량 사전 검증을 수행하며, clone 완료 후 node_modules, .git, build, dist, venv, .next, .env, key 등 불필요한 파일을 자동 필터링. timeout 설정이 적용되며 실패 시 임시 디렉토리를 자동 cleanup.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `POST` |
| Endpoint | `/api/repo/analysis/{job_id}/clone` |
| 관련 기능 ID | PROJECT-REPO-B-201, PROJECT-REPO-B-202, PROJECT-REPO-B-203 |
| 담당자 | 김효 |
| 상태 | 완료 |

### 요청 (Request)

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| job_id | String (UUID) | Y | 분석 작업 고유 ID |

**Request Body**

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| timeoutSeconds | Integer | 선택 | 300 | clone 제한 시간 (초) |

### 응답 (Response)

**성공 응답 — 200 OK**

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| code | Integer | 200 |
| message | String | "success" |
| data.jobId | String (UUID) | 분석 작업 고유 ID |
| data.clonePath | String | 서버 내 clone 완료 경로 |
| data.fileCount | Integer | 필터링 후 분석 대상 파일 수 |
| data.sizeKb | Integer | 필터링 후 총 용량 (KB) |

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 404 | JOB_NOT_FOUND | 존재하지 않는 job_id |
| 404 | REPOSITORY_NOT_FOUND | 저장소가 없거나 접근 불가 |
| 408 | CLONE_TIMEOUT | clone 제한 시간 초과 후 cleanup |
| 409 | CLONE_ALREADY_DONE | 이미 clone이 완료된 job |
| 413 | FILE_LIMIT_EXCEEDED | 실제 파일 수 또는 용량 제한 초과 |
| 500 | CLONE_FAILED | clone 중 subprocess 오류 발생 |

> **비고**: 필터링 제외 대상: node_modules/, .git/, build/, dist/, venv/, .next/, .env, key*, 바이너리 파일. 이 API는 `POST /api/repo/analysis` 내부에서 자동 호출됨.


---

## PROJECT-REPO-API-005: 분석 진행 상태 이벤트 스트림 수신 (SSE)

Server-Sent Events(SSE) 방식으로 분석 파이프라인의 진행 상태를 실시간 스트리밍. 클라이언트는 EventSource API로 연결하며, 각 파이프라인 단계(CLONE → CODE_MAP → DOC_GEN → ONBOARDING → REPORT) 전환 시마다 이벤트를 수신.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `GET (SSE)` |
| Endpoint | `/api/repo/analysis/{job_id}/events` |
| 관련 기능 ID | PROJECT-REPO-B-205, PROJECT-REPO-F-101, PROJECT-REPO-F-203 |
| 담당자 | oosuhada |
| 상태 | 완료 |

### 요청 (Request)

**Headers**

| 헤더명 | 값 | 필수 |
| --- | --- | --- |
| Authorization | Bearer {token} | Y |
| Accept | text/event-stream | Y |

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| job_id | String (UUID) | Y | 분석 작업 고유 ID |

### 응답 (Response)

**SSE 이벤트 구조 (text/event-stream)**

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| stage | String | 현재 단계 (CLONE / CODE_MAP / DOC_GEN / ONBOARDING / REPORT) |
| status | String | 단계 상태 (IN_PROGRESS / COMPLETED / FAILED) |
| progress | Integer | 전체 진행률 (0~100) |
| message | String | 진행 상태 메시지 |
| timestamp | String (ISO 8601) | 이벤트 발생 시각 |

```
data: {"stage":"CLONE","status":"IN_PROGRESS","progress":10,"message":"저장소 복제 중..."}

data: {"stage":"CODE_MAP","status":"IN_PROGRESS","progress":35,"message":"코드 구조 분석 중..."}

data: {"stage":"REPORT","status":"COMPLETED","progress":100,"message":"분석 완료!"}
```

| stage | progress 범위 |
| --- | --- |
| CLONE | 0~20% |
| CODE_MAP | 21~50% |
| DOC_GEN | 51~70% |
| ONBOARDING | 71~90% |
| REPORT | 91~100% |

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 404 | JOB_NOT_FOUND | 존재하지 않는 job_id |
| 409 | JOB_ALREADY_DONE | 이미 COMPLETED/FAILED 상태인 job |
| 500 | STREAM_ERROR | 이벤트 큐 오류 |


---

## PROJECT-REPO-API-006: WebSocket 기반 분석 진행 상태 수신

분석 작업의 진행 상태를 Frontend ProgressPanel에 WebSocket으로 실시간 push. 클라이언트가 연결하면 서버는 해당 job의 이벤트 큐를 subscribe하고, 각 파이프라인 단계 전환 시마다 JSON 이벤트를 push.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `WS` |
| Endpoint | `/ws/progress/{job_id}` |
| 관련 기능 ID | PROJECT-REPO-B-205, PROJECT-REPO-F-101 |
| 담당자 | oosuhada |
| 상태 | 완료 |

### 요청 (Request)

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| job_id | String (UUID) | Y | POST /api/repo/analysis 응답의 jobId 값 |

**Headers**

| 헤더명 | 값 | 필수 |
| --- | --- | --- |
| Authorization | Bearer {token} | Y |

### 응답 (Response)

**서버 Push 이벤트 JSON**

```json
{
  "stage":     "CLONE",
  "status":    "IN_PROGRESS",
  "progress":  10,
  "message":   "저장소를 복제하고 있습니다...",
  "timestamp": "2026-06-19T09:01:00Z"
}
```

**stage 정의**

| stage 값 | 단계 설명 | progress 범위 |
| --- | --- | --- |
| CLONE | 저장소 복제 | 0~20% |
| CODE_MAP | 코드 구조 분석 | 21~50% |
| DOC_GEN | 문서 자동 생성 | 51~70% |
| ONBOARDING | 온보딩 가이드 생성 | 71~90% |
| REPORT | 최종 결과 DB 저장 | 91~100% |

**연결 오류**

| WS Close Code | Error Code | 설명 |
| --- | --- | --- |
| 1008 | POLICY_VIOLATION | Authorization 헤더 인증 실패 |
| 1011 | SERVER_ERROR | 서버 내부 오류로 인한 강제 종료 |
| 4004 | JOB_NOT_FOUND | 존재하지 않는 job_id |
| 4008 | JOB_ALREADY_DONE | 이미 COMPLETED/FAILED 상태인 job_id로 연결 시도 |

> **비고**: 컴포넌트 언마운트 시 반드시 `ws.close()` 호출. 네트워크 단절 등 비정상 종료 시(onclose code !== 1000), 최대 3회 재연결 로직 구현 권장.


---

## PROJECT-REPO-API-007: clone 이후 전체 분석 파이프라인 시작

clone이 완료된 job에 대해 Code Map → Doc Generation → Onboarding Guide → Report 저장 순서로 전체 분석 파이프라인을 비동기 시작. 각 단계의 진행 상태는 이벤트 큐에 publish되어 WebSocket(API-006) 및 SSE(API-005)로 전달.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `POST` |
| Endpoint | `/api/repo/analysis/{job_id}/start` |
| 관련 기능 ID | PROJECT-REPO-B-204 |
| 담당자 | oosuhada |
| 상태 | 완료 |

### 요청 (Request)

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| job_id | String (UUID) | Y | clone이 완료된 분석 작업 고유 ID |

### 응답 (Response)

**성공 응답 — 202 Accepted**

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| code | Integer | 202 |
| message | String | "accepted" |
| data.jobId | String (UUID) | 분석 작업 고유 ID |
| data.status | String | 파이프라인 시작 상태: IN_PROGRESS |
| data.startedAt | String (ISO 8601) | 파이프라인 시작 시각 |

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 404 | JOB_NOT_FOUND | 존재하지 않는 job_id |
| 409 | PIPELINE_ALREADY_RUNNING | 이미 파이프라인이 실행 중인 job |
| 422 | CLONE_NOT_COMPLETED | clone이 완료되지 않은 상태에서 호출 |
| 500 | PIPELINE_START_FAILED | 파이프라인 시작 중 오류 발생 |

> **비고**: 이 API는 `POST /api/repo/analysis` 내부에서 자동 호출됨. clone 실패 후 수동 재시작 시에만 직접 호출.


---

## PROJECT-REPO-API-008: 실패/취소 시 임시 clone 디렉토리 cleanup

분석 실패 또는 취소 시 서버 내부에 생성된 임시 clone 디렉토리를 삭제. CLONE_TIMEOUT, CLONE_FAILED 등의 오류 발생 시 내부적으로 자동 호출되며, 수동으로 디스크 공간을 회수해야 할 때 직접 호출 가능.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `DELETE` |
| Endpoint | `/api/repo/analysis/{job_id}/workspace` |
| 관련 기능 ID | PROJECT-REPO-B-203 |
| 담당자 | 김효 |
| 상태 | 완료 |

### 요청 (Request)

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| job_id | String (UUID) | Y | cleanup 대상 분석 작업 고유 ID |

### 응답 (Response)

**성공 응답 — 200 OK**

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| code | Integer | 200 |
| message | String | "success" |
| data.jobId | String (UUID) | cleanup된 분석 작업 고유 ID |
| data.cleanedPath | String | 삭제된 임시 디렉토리 경로 |
| data.cleanedAt | String (ISO 8601) | cleanup 완료 시각 |

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 404 | JOB_NOT_FOUND | 존재하지 않는 job_id |
| 404 | WORKSPACE_NOT_FOUND | 이미 삭제되었거나 존재하지 않는 임시 디렉토리 |
| 409 | WORKSPACE_IN_USE | 분석 파이프라인이 진행 중인 상태에서 삭제 시도 |
| 500 | WORKSPACE_CLEANUP_FAILED | 파일 시스템 오류로 삭제 실패 |

> **비고**: status가 IN_PROGRESS인 job의 workspace는 삭제 불가 (WORKSPACE_IN_USE 반환). WORKSPACE_CLEANUP_FAILED 발생 시 내부 Slack 알람 발송.

---

## PROJECT-REPO-API-009: 로컬 폴더 업로드 분석 작업 생성

브라우저에서 선택한 로컬 프로젝트 폴더의 파일 목록을 업로드하여 분석 job을 생성합니다. Issue #156에 따라 Windows 위험 경로, 권한 실패, symlink/junction, 파일 수/용량 제한은 파일 단위로 분류하고 제외 사유를 응답에 포함합니다.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `POST` |
| Endpoint | `/api/repo/analysis/local` |
| 관련 기능 ID | PROJECT-REPO-B-206, PROJECT-REPO-F-204 |
| 상태 | 제안 |

### 요청 (Request)

**Request Body**

`multipart/form-data`를 사용합니다.

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| files | File[] | Y | - | 업로드 대상 파일 목록 |
| rootName | String | Y | - | 사용자가 선택한 폴더명 |
| manifest | JSON String | Y | - | 각 파일의 상대 경로, 크기, 프론트 사전 검사 결과 |
| visibility | String | 선택 | private | Phase 2: `private` 또는 `team` |
| teamId | UUID | 조건부 | null | Phase 2: `visibility=team`일 때 공유 대상 팀 ID |

### 응답 (Response)

**성공 응답 — 201 Created**

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| code | Integer | 201 |
| message | String | "created" |
| data.jobId | UUID | 생성된 분석 job ID |
| data.acceptedCount | Integer | 저장된 파일 수 |
| data.skippedCount | Integer | 제외된 파일 수 |
| data.skippedByReason | Object | 제외 사유별 카운트 |
| data.warnings | Array | 사용자에게 표시할 경고 메시지 |

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 400 | INVALID_LOCAL_PATH | 상대 경로가 비어 있거나 Windows/서버 정책상 허용되지 않음 |
| 400 | SYMLINK_NOT_ALLOWED | 심볼릭 링크는 업로드할 수 없음 |
| 403 | LOCAL_UPLOAD_PERMISSION_DENIED | 권한 부족 파일 접근 또는 저장 실패 |
| 403 | TEAM_ACCESS_DENIED | Phase 2: 지정한 팀에 분석을 생성할 권한이 없음 |
| 413 | LOCAL_UPLOAD_LIMIT_EXCEEDED | 파일 수/전체 용량/단일 파일 크기 제한 초과 |
| 415 | UNSUPPORTED_FILE_TYPE | 분석 대상이 아닌 바이너리 또는 허용되지 않은 파일 형식 |
| 500 | LOCAL_UPLOAD_SAVE_FAILED | 서버 workspace 저장 중 처리 불가 오류 |

---

## PROJECT-REPO-API-010: 분석 job scoped 파일 코드 읽기

분석된 job의 workspace 내부 파일을 안전하게 읽어 `/analyze` Repository 코드 프리뷰와 채팅 근거 라인 이동에 사용합니다. Issue #160, #161의 기준 API입니다.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `GET` |
| Endpoint | `/api/repo/analysis/{job_id}/files` |
| 관련 기능 ID | PROJECT-REPO-B-402 |
| 상태 | 제안 |

### 요청 (Request)

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| job_id | UUID | Y | 분석 작업 고유 ID |

**Query Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| path | String | Y | repo 내부 상대 파일 경로 |
| startLine | Integer | N | 부분 읽기 시작 라인 |
| endLine | Integer | N | 부분 읽기 종료 라인 |

### 응답 (Response)

**성공 응답 — 200 OK**

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| code | Integer | 200 |
| message | String | "success" |
| data.path | String | repo 내부 상대 경로 |
| data.content | String | 파일 내용 또는 부분 내용 |
| data.encoding | String | 감지된 인코딩 |
| data.lineCount | Integer | 전체 라인 수 |
| data.characterCount | Integer | 전체 글자 수 |
| data.startLine | Integer | 반환된 첫 라인 |
| data.endLine | Integer | 반환된 마지막 라인 |
| data.truncated | Boolean | 크기 제한으로 일부만 반환했는지 여부 |

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 400 | INVALID_FILE_PATH | path traversal, 절대 경로, 빈 경로 |
| 401 | UNAUTHORIZED | 인증 토큰 누락 또는 만료 |
| 403 | TEAM_ACCESS_DENIED | Phase 2: 해당 job에 접근 권한 없음 |
| 403 | PRIVATE_RESOURCE_DENIED | Phase 2: 다른 사용자의 private job 접근 |
| 404 | JOB_NOT_FOUND | 존재하지 않는 job |
| 404 | FILE_NOT_FOUND | workspace 내부에 해당 파일 없음 |
| 413 | FILE_TOO_LARGE | 프리뷰 허용 크기 초과 |
| 415 | UNSUPPORTED_FILE_TYPE | 바이너리 또는 텍스트로 표시할 수 없는 파일 |
