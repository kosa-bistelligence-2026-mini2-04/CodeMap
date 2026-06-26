# PROJECT LIST API 명세서

> **최종 업데이트**: 2026-06-26


## API 목록

| API ID | Method | Endpoint | 목적 | 담당 | 상태 |
| --- | --- | --- | --- | --- | --- |
| PROJECT-LIST-API-001 | `GET` | `/api/list/analysis` | 전체 저장소 분석 이력 및 작업 목록 조회 | 강영우 | 완료 |
| PROJECT-LIST-API-002 | `POST` | `/api/list/validate` | 클론 전 저장소 파일 수 및 용량 사전 검증 | 성민 신 | 시작 전 |
| PROJECT-LIST-API-003 | `WS` | `/ws/list/progress/{job_id}` | 실시간 분석 작업 상태 및 진행률 공유 (WebSocket) | 강영우 | 진행 중 |
| PROJECT-LIST-API-004 | `GET` | `/api/list/analysis/{job_id}` | 특정 분석 작업 상세 조회 | - | 시작 전 |
| PROJECT-LIST-API-005 | `POST` | `/api/list/validate` | 저장소 검증 (API-002 참조) | - | 시작 전 |
| PROJECT-LIST-API-006 | `PATCH` | `/api/list/analysis/{job_id}/status` | 분석 작업 상태 수동 업데이트 | - | 시작 전 |
| PROJECT-LIST-API-007 | `POST` | `/api/list/analysis/{job_id}/retry` | 실패 분석 작업 재시도 | - | 제안 |
| PROJECT-LIST-API-008 | `DELETE` | `/api/list/analysis/{job_id}` | 분석 이력 삭제 또는 숨김 | - | 제안 |

---

## PROJECT-LIST-API-001: 전체 저장소 분석 이력 및 작업 목록 조회

사용자가 이전에 분석을 시도했거나 완료한 전체 레포지토리 및 작업(Job) 목록을 반환. 페이징 처리를 지원하여 성능 부하를 방지.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `GET` |
| Endpoint | `/api/list/analysis` |
| 관련 기능 ID | PROJECT-LIST-B-101, PROJECT-LIST-B-202, PROJECT-LIST-B-301, PROJECT-LIST-F-101 |
| 담당자 | 강영우 |
| 상태 | 완료 |

### 요청 (Request)

**Headers**

| 헤더명 | 값 | 필수 | 설명 |
| --- | --- | --- | --- |
| Authorization | Bearer {token} | Y | JWT 인증 토큰 |
| Content-Type | application/json | Y | |

**Query Parameters**

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| page | Integer | 선택 | 1 | 조회할 페이지 번호 |
| limit | Integer | 선택 | 10 | 페이지당 반환할 이력 수 |
| scope | String | 선택 | private | Phase 2: `private`, `team`, `all` |
| teamId | UUID | 조건부 | null | Phase 2: `scope=team`일 때 조회할 팀 ID |
| query | String | 선택 | null | Issue #177: repoName 또는 repoUrl 검색어 |
| status | String | 선택 | null | Issue #177: `queued`, `running`, `completed`, `failed` 필터 |
| sort | String | 선택 | `updatedAt:desc` | Issue #177: `updatedAt`, `createdAt`, `status` 기준 정렬 |

**요청 예시**
```
GET /api/list/analysis?page=1&limit=10 HTTP/1.1
Authorization: Bearer eyJhbGci...
```

### 응답 (Response)

**성공 응답 — 200 OK**

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| code | Integer | HTTP 상태 코드 (200) |
| message | String | "success" |
| data.totalCount | Integer | 전체 분석 이력 수 |
| data.page | Integer | 현재 페이지 번호 |
| data.limit | Integer | 페이지당 반환 개수 |
| data.jobs | Array | 분석 작업 목록 배열 |
| data.jobs[].jobId | String (UUID) | 분석 작업 고유 ID |
| data.jobs[].repoUrl | String | GitHub 저장소 URL |
| data.jobs[].branch | String | 분석 대상 브랜치 |
| data.jobs[].status | String | 작업 상태 (queued / running / completed / failed) |
| data.jobs[].progress | Integer | 작업 진행률 (0~100) |
| data.jobs[].failedAgent | String | 실패한 에이전트명 (실패 시에만, 그 외 null) |
| data.jobs[].errorMessage | String | 구체적인 에러 메시지 (실패 시에만, 그 외 null) |
| data.jobs[].canRetry | Boolean | Issue #177: 실패 job 재시도 가능 여부 |
| data.jobs[].canDelete | Boolean | Issue #177: 현재 사용자의 삭제/숨김 가능 여부 |
| data.jobs[].createdAt | String (ISO 8601) | 작업 생성 시각 |
| data.jobs[].updatedAt | String (ISO 8601) | 작업 최종 변경 시각 |
| data.jobs[].visibility | String | Phase 2: `private` 또는 `team` |
| data.jobs[].teamId | String(UUID) \| null | Phase 2: 팀 공유 분석이면 팀 ID |

> Phase 2 권한 계약: `scope=private`는 현재 사용자가 생성한 private job만 반환합니다. `scope=team`은 `teamId`의 active member에게만 결과를 반환합니다. `scope=all`은 private 결과와 접근 가능한 team 결과를 합칩니다. 자세한 기준은 `PROJECT_TEAM_SPEC.md`와 `PROJECT_TEAM_API_SPEC.md`를 따릅니다.

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 401 | UNAUTHORIZED | 토큰이 누락되었거나 만료됨 |
| 403 | TEAM_ACCESS_DENIED | Phase 2: 요청한 팀 기록에 접근 권한이 없음 |
| 400 | INVALID_HISTORY_FILTER | Issue #177: 허용되지 않은 status/sort/query 조건 |
| 500 | DATABASE_ERROR | 데이터베이스 조회 중 예외 발생 |


---

## PROJECT-LIST-API-002: 클론 전 저장소 파일 수 및 용량 사전 검증

본격적인 Git Clone 및 분석 파이프라인 시작 전에, 대상 저장소의 파일 개수 및 용량이 제한 조건(100개 파일 이하, 파일당 100KB 이하 등)을 준수하는지 검증.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `POST` |
| Endpoint | `/api/list/validate` |
| 관련 기능 ID | PROJECT-LIST-B-201, PROJECT-LIST-F-101 |
| 담당자 | 성민 신 |
| 상태 | 시작 전 |

### 요청 (Request)

**Request Body**

| 필드명 | 타입 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- | --- |
| repoUrl | String | Y | - | 검증할 GitHub 저장소 URL |
| branch | String | 선택 | 기본 브랜치 | 검증 대상 브랜치 |

### 응답 (Response)

**성공 응답 — 200 OK**

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| code | Integer | 200 |
| message | String | "success" |
| data.isValid | Boolean | 분석 가능 여부 (제한 조건 이내인 경우 true) |
| data.fileCount | Integer | 저장소 내의 대상 파일 수 |
| data.totalSizeKb | Integer | 저장소 총 용량 (KB) |
| data.warningMessage | String | 제한 조건 초과 시 경고 메시지 (초과하지 않으면 null) |

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 400 | INVALID_REPO_URL | GitHub URL 형식이 올바르지 않음 |
| 401 | UNAUTHORIZED | 토큰이 누락되었거나 만료됨 |
| 404 | REPOSITORY_NOT_FOUND | 저장소가 존재하지 않거나 비공개 |
| 500 | VALIDATION_FAILED | GitHub API 호출 중 서브프로세스 에러 발생 |


---

## PROJECT-LIST-API-003: 실시간 분석 작업 상태 및 진행률 공유 (WebSocket)

클라이언트 화면에서 작업의 상태 변경 사항을 폴링(Polling) 없이 실시간으로 수신하기 위해 WebSocket 연결을 맺고 메시지를 수신.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `WS` |
| Endpoint | `/ws/list/progress/{job_id}` |
| 관련 기능 ID | PROJECT-LIST-F-202, PROJECT-LIST-F-203 |
| 담당자 | 강영우 |
| 상태 | 진행 중 |

### 요청 (Request)

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| job_id | String (UUID) | Y | 상태를 추적할 분석 작업 고유 ID |

**연결 예시**
```
GET /ws/list/progress/0a8cc46e-d954-82c0-897c-013b0f2227b3 HTTP/1.1
Upgrade: websocket
Connection: Upgrade
```

### 응답 (Response)

**서버 Push 이벤트 구조 (JSON)**

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| jobId | String (UUID) | 분석 작업 고유 ID |
| status | String | 현재 작업 상태 (queued / running / completed / failed) |
| progress | Integer | 작업 진행률 (0~100) |
| currentStep | String | 현재 실행 중인 분석 단계명 |
| failedAgent | String | 실패한 에이전트명 (실패 시에만, 그 외 null) |
| errorMessage | String | 에러 메시지 (실패 시에만, 그 외 null) |

> **비고**: failed 또는 completed 상태 수신 시 WebSocket 연결 종료 및 cleanup 필요.


---

## PROJECT-LIST-API-004: 특정 분석 작업 상세 조회

job_id에 해당하는 분석 작업의 상세 정보 조회. (명세 작성 예정)

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `GET` |
| Endpoint | `/api/list/analysis/{job_id}` |
| 상태 | 시작 전 |

### 요청 (Request)

**Path Parameters**

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| job_id | String (UUID) | Y | 조회할 분석 작업 고유 ID |

### 응답 (Response)

> ⚠️ 응답 스키마 미작성 — 추후 업데이트 예정


---

## PROJECT-LIST-API-005: 저장소 검증 (API-002 참조)

PROJECT-LIST-API-002와 동일한 엔드포인트. 명세 작성 예정.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `POST` |
| Endpoint | `/api/list/validate` |
| 상태 | 시작 전 |

### 요청 (Request)

> ⚠️ 명세 미작성 — PROJECT-LIST-API-002 참조

### 응답 (Response)

> ⚠️ 명세 미작성 — PROJECT-LIST-API-002 참조


---

## PROJECT-LIST-API-006: 분석 작업 상태 수동 업데이트

분석 작업 상태를 수동으로 업데이트. 명세 작성 예정.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `PATCH` |
| Endpoint | `/api/list/analysis/{job_id}/status` |
| 상태 | 시작 전 |

### 요청 (Request)

> ⚠️ 명세 미작성 — 추후 업데이트 예정

### 응답 (Response)

> ⚠️ 명세 미작성 — 추후 업데이트 예정

---

## PROJECT-LIST-API-007: 실패 분석 작업 재시도

Issue #177에 따라 실패한 분석 job을 사용자가 History에서 다시 실행할 수 있게 합니다. 재시도는 기존 job을 덮어쓰지 않고 새 job을 생성하거나, 구현 정책에 따라 retryOfJobId를 가진 새 실행 단위로 분리합니다.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `POST` |
| Endpoint | `/api/list/analysis/{job_id}/retry` |
| 관련 기능 ID | PROJECT-LIST-F-205 |
| 상태 | 제안 |

### 요청 (Request)

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| job_id | String (UUID) | Y | 재시도할 failed job ID |

### 응답 (Response)

**성공 응답 — 201 Created**

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| code | Integer | 201 |
| message | String | "created" |
| data.jobId | String(UUID) | 새로 생성된 분석 job ID |
| data.retryOfJobId | String(UUID) | 원본 failed job ID |
| data.status | String | `queued` 또는 `running` |

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 403 | FORBIDDEN | 현재 사용자가 해당 job을 재시도할 권한이 없음 |
| 404 | JOB_NOT_FOUND | 원본 job을 찾을 수 없음 |
| 409 | JOB_NOT_RETRYABLE | failed 상태가 아니거나 재시도 가능한 오류가 아님 |
| 500 | DATABASE_ERROR | 재시도 job 생성 실패 |

---

## PROJECT-LIST-API-008: 분석 이력 삭제 또는 숨김

Issue #177에 따라 사용자가 History에서 불필요한 분석 이력을 삭제하거나 숨김 처리할 수 있게 합니다. 팀 공유 이력의 물리 삭제는 권한 정책에 따라 owner/admin으로 제한하고, 일반 멤버는 개인 view에서 숨김 처리만 허용할 수 있습니다.

### 기본 정보

| 항목 | 내용 |
| --- | --- |
| Method | `DELETE` |
| Endpoint | `/api/list/analysis/{job_id}` |
| 관련 기능 ID | PROJECT-LIST-F-205 |
| 상태 | 제안 |

### 요청 (Request)

| 파라미터 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| job_id | String (UUID) | Y | 삭제 또는 숨김 처리할 job ID |
| mode | String | 선택 | `hide` 또는 `delete`; 기본값은 권한에 따라 서버가 결정 |

### 응답 (Response)

**성공 응답 — 200 OK**

| 필드명 | 타입 | 설명 |
| --- | --- | --- |
| code | Integer | 200 |
| message | String | "success" |
| data.jobId | String(UUID) | 처리된 job ID |
| data.mode | String | `hide` 또는 `delete` |

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 403 | FORBIDDEN | 삭제 또는 숨김 권한이 없음 |
| 404 | JOB_NOT_FOUND | job을 찾을 수 없음 |
| 409 | JOB_DELETE_CONFLICT | running job 등 삭제할 수 없는 상태 |
| 500 | DATABASE_ERROR | 삭제 또는 숨김 처리 실패 |
