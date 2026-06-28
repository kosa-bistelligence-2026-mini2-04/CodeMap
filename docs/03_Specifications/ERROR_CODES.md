# API Error Codes Specification

본 문서는 CodeMap 백엔드 API에서 발생하는 HTTP 에러 코드 및 WebSocket Close Code에 대한 통합 명세서입니다.

모든 REST 오류는 `docs/04_Decisions/ERROR_HANDLING.md`의 표준 envelope를 사용합니다. 표의 Error Code는
`error.code`에, HTTP Status는 최상위 `code`와 실제 HTTP status에 동일하게 기록합니다.

```json
{
  "code": 404,
  "message": "요청한 분석 작업을 찾을 수 없습니다.",
  "data": null,
  "error": {
    "code": "JOB_NOT_FOUND",
    "detail": null,
    "field": "jobId",
    "retryable": false
  }
}
```

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

## 1A. PROJECT-AUTH-API (인증)
`POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/refresh`, `POST /api/auth/logout`

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_EMAIL` | 회원가입 입력 검증 | 이메일 형식이 올바르지 않음 |
| 400 | `PASSWORD_TOO_SHORT` | 회원가입 입력 검증 | 비밀번호가 최소 길이를 만족하지 않음 |
| 400 | `PASSWORD_RULE_VIOLATION` | 회원가입 입력 검증 | 비밀번호가 서비스 비밀번호 규칙을 만족하지 않음 |
| 401 | `INVALID_CREDENTIALS` | 로그인 인증 | 이메일 또는 비밀번호가 일치하지 않음 |
| 401 | `INVALID_REFRESH_TOKEN` | 토큰 갱신 | Refresh Token 만료 또는 위조 |
| 404 | `USER_NOT_FOUND` | 로그인 인증 | 존재하지 않는 이메일 |
| 409 | `EMAIL_ALREADY_EXISTS` | 회원가입 중복 검사 | 이미 등록된 이메일 |

Issue #174, #175: Auth UI는 위 오류를 HTTP status 중심 문구가 아니라 사용자 언어와 field-level 피드백으로 표시합니다. `error.field`가 `email`, `password`, `confirmPassword` 중 하나이면 해당 입력칸에 표시하고, 필드가 없으면 form 상단 전역 오류로 표시합니다.

## 1B. PROJECT-REPO-API-009 (로컬 폴더 업로드 분석 작업 생성)
`POST /api/repo/analysis/local`

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_LOCAL_PATH` | 경로 검증 | 상대 경로가 비어 있거나 Windows/서버 정책상 허용되지 않음 |
| 400 | `SYMLINK_NOT_ALLOWED` | 파일 검증 | 심볼릭 링크는 업로드할 수 없음 |
| 403 | `LOCAL_UPLOAD_PERMISSION_DENIED` | 파일 처리 | 권한 부족 파일 접근 또는 저장 실패 |
| 403 | `TEAM_ACCESS_DENIED` | 팀 권한 검증 | 지정한 팀에 분석을 생성할 권한이 없음 |
| 413 | `LOCAL_UPLOAD_LIMIT_EXCEEDED` | 용량 검증 | 파일 수/전체 용량/단일 파일 크기 제한 초과 |
| 415 | `UNSUPPORTED_FILE_TYPE` | 파일 검증 | 분석 대상이 아닌 바이너리 또는 허용되지 않은 파일 형식 |
| 500 | `LOCAL_UPLOAD_SAVE_FAILED` | 저장 처리 | 서버 workspace 저장 중 처리 불가 오류 |

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

## 5A. REPO-FILE-API-001 (저장소 파일 컨텐츠 조회)
`GET /api/repo/analysis/{job_id}/files/content`

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 403 | `FILE_PATH_FORBIDDEN` | 파일 경로 해결 시 | 요청된 경로가 분석 대상 작업의 workspace 디렉토리를 벗어남 (Path Traversal 탐지) |
| 404 | `WORKSPACE_NOT_READY` | 파일 검증 시 | 해당 분석 작업의 로컬 workspace가 준비되지 않았거나 요청된 파일이 존재하지 않음 |
| 422 | `BINARY_FILE` | 파일 확장자 검증 | 미리보기가 불가능한 바이너리 파일(이미지, 압축파일 등) 조회를 시도함 |


## 6. RAG-PARSE-API (코드 분석 - 파싱)
`GET /api/parse/analysis/{repo_id}`

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `REPO_NOT_FOUND` | DB 조회 | repo_id가 존재하지 않음 |
| 404 | `PARSE_RESULT_NOT_FOUND` | DB 조회 | 분석 결과가 아직 생성되지 않음 |
| 404 | `README_NOT_FOUND` | 파일 탐색 | README 파일이 저장소에 없음 |
| 404 | `CODEMAP_NOT_FOUND` | DB 조회 | 코드 맵 분석 결과가 없음 |
| 500 | `TREE_PARSE_FAILED` | 파일 탐색 | 디렉토리 트리 생성 실패 |
| 500 | `STACK_DETECTION_FAILED` | 파일 파싱 | 기술 스택 탐지 실패 |
| 500 | `AST_PARSE_FAILED` | AST 처리 | AST 청킹 또는 의존성 분석 실패 |
| 500 | `SUMMARY_FAILED` | LLM 처리 | Bottom-up 요약 생성 실패 |

## 7. RAG-EMBED-API (벡터 임베딩)
`POST /api/embed/analysis/{repo_id}`

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 409 | `EMBEDDING_IN_PROGRESS` | 중복 검사 | 이미 임베딩이 진행 중인 저장소 |
| 422 | `PARSE_NOT_COMPLETED` | 사전 검증 | 파싱이 완료되지 않은 상태에서 임베딩 요청 |
| 500 | `EMBEDDING_FAILED` | 임베딩 처리 | OpenAI API 호출 또는 벡터 저장 중 오류 |

## 8. LLM-CHAT-RUN-API (멀티에이전트 Q&A)
`POST /api/chat/{repo_id}/runs` 및 연관 엔드포인트

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_CHAT_REQUEST` | 입력 검증 | 요청이 유효하지 않음 (예: 최대 길이 초과) |
| 404 | `REPO_NOT_FOUND` | repo 조회 | repo_id가 존재하지 않거나 현재 사용자가 접근할 수 없음 |
| 409 | `REPO_NOT_ANALYZED` | 사전 검증 | 임베딩 및 분석이 완료되지 않아 에이전트 실행 불가 |
| 404 | `LLM_RUN_NOT_FOUND` | 상태 조회/스트림 | 존재하지 않는 run_id |
| 404 | `AGENT_EVIDENCE_NOT_FOUND` | 근거 조회 | 존재하지 않거나 만료된 증거 데이터 |
| 409 | `DUPLICATE_CHAT_RUN` | Run 생성 | 같은 clientRequestId 또는 동일 질문 run이 이미 생성/진행 중 |
| 409 | `RUN_REPO_MISMATCH` | 상태 조회/스트림 | run_id는 존재하지만 path의 repo_id와 연결되지 않음 |
| 409 | `LLM_RUN_ALREADY_FINISHED` | 취소/스트림 | 이미 종료된 run_id에 대한 요청 |
| 409 | `AGENT_EVIDENCE_NOT_READY` | 근거 조회 | 아직 워커 수집이 완료되지 않아 Evidence 접근 불가 |
| 500 | `LLM_RUN_CREATE_FAILED` | Run 생성 | LangGraph 초기화 및 Run 생성 실패 |
| 500 | `AGENT_STREAM_FAILED` | 스트리밍 | SSE 연결 또는 결과 스트리밍 중 오류 |

## 9. LLM-WORKER-INTERNAL-ERRORS (내부 에러)
*이 에러들은 REST 응답이 아닌 State 내부에 기록되며 Error Recovery에 사용됩니다.*

| 발생 도구 | Error Code | 설명 |
| :--- | :--- | :--- |
| Dispatcher Node | `AGENT_TOOL_POLICY_FAILED` | Planner의 접근 계획이 Path Traversal 등 보안 정책에 위배됨 |
| Reasoning Worker | `AGENT_REASONING_FAILED` | 코드 추론 중 LLM 응답 파싱 또는 실행 실패 |
| Search / Grep Worker | `VECTOR_SEARCH_FAILED` / `GREP_FAILED` | 임베딩 검색 또는 grep 도구 실행 실패 |

## 10. DOCS-GEN-API (가이드북 생성)
`POST /api/gen/docs/{repo_id}`

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `DOCS_NOT_FOUND` | DB 조회 | 가이드북이 아직 생성되지 않음 |
| 409 | `DOCS_ALREADY_EXISTS` | 중복 검사 | 가이드북이 이미 존재 (force=false) |
| 409 | `DOCS_GENERATION_IN_PROGRESS` | 중복 검사 | 가이드북 생성이 이미 진행 중 |
| 422 | `ANALYSIS_NOT_COMPLETED` | 사전 검증 | RAG 파이프라인이 완료되지 않음 |
| 500 | `DOCS_GENERATION_FAILED` | LLM 처리 | 가이드북 생성 중 오류 |
| 500 | `FILE_GENERATION_FAILED` | 파일 생성 | Markdown/PDF 파일 생성 실패 |

## 11. DOCS-GUARD-API (민감정보 보호)
`POST /api/gen/docs/{repo_id}/guard`

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_CONTENT` | 입력 검증 | 검사 대상 content가 비어있음 |
| 500 | `GUARD_FAILED` | 패턴 탐지 | 민감정보 탐지 처리 중 오류 |

## 12. PROJECT-LIST API

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_JOB_ID` | Path 검증 | job_id가 UUID 형식이 아님 |
| 400 | `INVALID_STATUS` | 상태 저장 | 허용되지 않는 상태 값 |
| 400 | `INVALID_PROGRESS` | 상태 저장 | progress가 0-100 범위를 벗어남 |
| 400 | `INVALID_HISTORY_FILTER` | 이력 조회 | 허용되지 않은 검색/필터/정렬 조건 |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `JOB_NOT_FOUND` | DB 조회 | 분석 작업 없음 |
| 409 | `JOB_NOT_RETRYABLE` | 재시도 요청 | failed 상태가 아니거나 재시도 가능한 오류가 아님 |
| 409 | `JOB_DELETE_CONFLICT` | 삭제/숨김 요청 | running job 등 삭제할 수 없는 상태 |
| 413 | `FILE_LIMIT_EXCEEDED` | 제한 검증 | 파일 수 또는 파일 크기 제한 초과 |
| 422 | `REPO_LIMIT_EXCEEDED` | 제한 검증 | 저장소 규모가 분석 허용 범위 초과 |
| 500 | `VALIDATION_FAILED` | 사전 검증 | 파일 수 또는 용량 계산 실패 |
| 500 | `DATABASE_ERROR` | DB 처리 | 조회 또는 상태 저장 실패 |

## 13. PROJECT-PIPELINE API (Phase 2)

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_WEBHOOK_URL` | Webhook 검증 | 허용되지 않는 Webhook URL |
| 401 | `UNAUTHORIZED` | 인증 검증 | 토큰 누락 또는 만료 |
| 404 | `JOB_NOT_FOUND` | DB 조회 | 분석 작업 없음 |
| 409 | `BASIC_ANALYSIS_NOT_COMPLETED` | 사전 검증 | 기본 분석 미완료 |
| 500 | `PIPELINE_START_FAILED` | 파이프라인 초기화 | 심층 분석 시작 실패 |

## 14. RAG-GRAPH / PARSE-ADVANCED API (Phase 2)

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 404 | `GRAPH_NOT_FOUND` | DB 조회 | 의존성 그래프 미생성 |
| 404 | `RISK_ANALYSIS_NOT_FOUND` | DB 조회 | 위험 분석 결과 없음 |
| 404 | `STACK_SCORE_NOT_FOUND` | DB 조회 | 기술 스택 점수 결과 없음 |
| 500 | `GRAPH_BUILD_FAILED` | 그래프 처리 | 그래프 생성 실패 |
| 500 | `RISK_ANALYSIS_FAILED` | 위험 분석 | 위험 신호 분석 실패 |
| 500 | `STACK_SCORE_FAILED` | 점수 계산 | 기술 스택 점수화 실패 |

## 15. LLM-ADVANCED / DOCS-UTIL API (Phase 2)

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `INVALID_CHANNEL` | 공유 채널 검증 | 이메일 또는 Slack 대상이 유효하지 않음 |
| 404 | `DOCS_NOT_FOUND` | DB 조회 | 공유 또는 변환할 가이드북 없음 |
| 404 | `REPO_NOT_FOUND` | DB 조회 | 저장소 없음 |
| 500 | `MEMORY_RETRIEVAL_FAILED` | 기억 조회 | 장기 기억 조회 실패 |
| 500 | `PDF_RENDER_FAILED` | PDF 변환 | HTML-PDF 렌더링 실패 |
| 500 | `SHARE_FAILED` | 외부 전송 | 이메일 또는 Slack 발송 실패 |

## 16. LLM-MODEL-CATALOG API
`GET /api/llm/models` 또는 동일 책임의 정적/공유 모델 카탈로그 계약

| HTTP Status | Error Code | 발생 시점 | 설명 |
| :--- | :--- | :--- | :--- |
| 400 | `UNSUPPORTED_MODEL` | 모델 선택 검증 | 요청한 model id가 backend allowlist에 없음 |
| 422 | `MODEL_DISABLED` | 모델 선택 검증 | 카탈로그에는 있으나 현재 환경에서 비활성화된 모델 |
| 500 | `MODEL_CATALOG_UNAVAILABLE` | 카탈로그 조회 | 모델 카탈로그를 불러올 수 없음 |

## 17. 클라이언트 처리 원칙

- `400`, `403`, `404`, `413`, `422`: 요청 또는 상태를 수정하기 전 자동 재시도 금지
- `401`: 재인증 후 새 요청
- `408`: 멱등 요청만 제한적으로 재시도
- `409`: 충돌 원인이 해소됐는지 상태를 다시 조회한 뒤 요청
- `500`: `error.retryable`이 true인 경우에만 제한적으로 재시도
- SSE 연결 후 오류는 HTTP status가 아니라 `event: error`로 처리
- WebSocket 종료는 close code와 최종 이벤트를 함께 기록
- Issue #176: frontend API client는 공통 `parseApiError` 규칙으로 `{ status, code, message, field, retryable, detail }`을 정규화한 뒤 UI에 전달합니다.
- Issue #176: `error.detail`이 객체인 경우에도 UI에 `[object Object]`를 직접 표시하지 않고, 사용자 메시지는 최상위 `message` 또는 error code mapping을 우선합니다.
- Issue #180: icon-only control, modal, toast, banner가 오류를 표시할 때 accessible name, focus 이동, reduced motion 설정을 함께 만족해야 합니다.
