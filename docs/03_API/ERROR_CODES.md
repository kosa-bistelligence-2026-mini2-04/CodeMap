# API Error Codes Specification

본 문서는 CodeMap 백엔드 API에서 발생하는 HTTP 에러 코드 및 WebSocket Close Code에 대한 통합 명세서입니다.

## 1. PROJECT-REPO-API-001 (분석 작업 생성)
`POST /api/repo/analysis`

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_REPO_URL` | URL 파싱 | GitHub URL 형식이 올바르지 않음 |
| 404 | `REPOSITORY_NOT_FOUND` | Clone 시도 | 저장소가 없거나 접근 불가 (private/삭제) |
| 408 | `CLONE_TIMEOUT` | Clone 실행 | clone 제한 시간 초과 |
| 409 | `ALREADY_IN_PROGRESS` | 작업 등록 | 동일 저장소 분석이 이미 진행 중 |
| 413 | `FILE_LIMIT_EXCEEDED` | Clone 후 검증 | 실제 파일 수 또는 용량 제한 초과 |
| 422 | `REPO_LIMIT_EXCEEDED` | 사전 검증 | Clone 전 GitHub API 기준 용량 초과 |
| 500 | `CLONE_FAILED` | Clone 실행 | clone 중 subprocess 오류 발생 |
| 500 | `WORKSPACE_CLEANUP_FAILED` | cleanup 단계 | 임시 디렉토리 삭제 실패 (내부 알람 발송) |

## 2. PROJECT-REPO-API-003 (작업 상태 조회)
`GET /api/repo/analysis/{job_id}`

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `JOB_NOT_FOUND` | 조회 시 | 존재하지 않는 job_id |
| 500 | `INTERNAL_ERROR` | 조회 시 | 서버 내부 오류 |

## 3. PROJECT-REPO-API-005 (작업 이벤트 구독 - SSE)
`GET /api/repo/analysis/{job_id}/events`

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `JOB_NOT_FOUND` | 연결 시 | 존재하지 않는 job_id |
| 409 | `JOB_ALREADY_DONE` | 연결 시 | 이미 COMPLETED/FAILED 상태인 job |
| 500 | `STREAM_ERROR` | 스트리밍 중 | 이벤트 큐 오류 |

## 4. PROJECT-REPO-API-006 (작업 이벤트 구독 - WebSocket)
`WS /ws/progress/{job_id}`

| WS Close Code | Error Code | 설명 |
| :--- | :--- | :--- |
| 1008 | `POLICY_VIOLATION` | Authorization 헤더 인증 실패 |
| 1011 | `SERVER_ERROR` | 서버 내부 오류로 인한 강제 종료 |
| 4004 | `JOB_NOT_FOUND` | 존재하지 않는 job_id |
| 4008 | `JOB_ALREADY_DONE` | 이미 COMPLETED/FAILED 상태인 job_id로 연결 시도 |

## 5. PROJECT-REPO-API-007 (파이프라인 시작 제어)
`POST /api/repo/analysis/{job_id}/start`

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `JOB_NOT_FOUND` | 요청 시 | 존재하지 않는 job_id |
| 409 | `PIPELINE_ALREADY_RUNNING` | 요청 시 | 이미 파이프라인이 실행 중인 job |
| 422 | `CLONE_NOT_COMPLETED` | 요청 시 | clone이 완료되지 않은 상태에서 호출 |
| 500 | `PIPELINE_START_FAILED` | 파이프라인 초기화 | 파이프라인 시작 중 오류 발생 |
