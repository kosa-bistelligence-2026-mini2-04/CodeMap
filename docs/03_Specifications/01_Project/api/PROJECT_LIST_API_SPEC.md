# PROJECT LIST API 명세서

> **최종 업데이트**: 2026-06-19


## API 목록

| API ID | Method | Endpoint | 목적 | 담당 | 상태 |
| --- | --- | --- | --- | --- | --- |
| PROJECT-LIST-API-001 | `GET` | `/api/list/analysis` | 전체 저장소 분석 이력 및 작업 목록 조회 | 강영우 | 완료 |
| PROJECT-LIST-API-002 | `POST` | `/api/list/validate` | 클론 전 저장소 파일 수 및 용량 사전 검증 | 성민 신 | 시작 전 |
| PROJECT-LIST-API-003 | `WS` | `/ws/list/progress/{job_id}` | 실시간 분석 작업 상태 및 진행률 공유 (WebSocket) | 강영우 | 진행 중 |
| PROJECT-LIST-API-004 | `GET` | `/api/list/analysis/{job_id}` | 특정 분석 작업 상세 조회 | - | 시작 전 |
| PROJECT-LIST-API-005 | `POST` | `/api/list/validate` | 저장소 검증 (API-002 참조) | - | 시작 전 |
| PROJECT-LIST-API-006 | `PATCH` | `/api/list/analysis/{job_id}/status` | 분석 작업 상태 수동 업데이트 | - | 시작 전 |

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
| data.jobs[].createdAt | String (ISO 8601) | 작업 생성 시각 |
| data.jobs[].updatedAt | String (ISO 8601) | 작업 최종 변경 시각 |

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 401 | UNAUTHORIZED | 토큰이 누락되었거나 만료됨 |
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


