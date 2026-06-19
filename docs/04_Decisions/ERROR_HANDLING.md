# CodeMap API 에러 처리 가이드 (Error Handling Guide)

API 개발 시 발생할 수 있는 에러 상황에 대해 프로젝트 내 통일된 규격을 정의합니다.
PR 리뷰 피드백에서 지적된 바와 같이, **모든 에러를 일괄적으로 `404 Not Found`로 처리하는 것은 엄격히 금지**됩니다. 상황에 맞는 HTTP Status Code와 정해진 응답 포맷을 사용하여야 합니다.

## 1. 기본 에러 응답 포맷

모든 에러 응답은 성공 응답과 동일하게 `code`, `message` 구조를 포함해야 하며, 클라이언트가 에러를 파악할 수 있도록 작성되어야 합니다.

`code`, `message`, `data`는 모든 응답의 공통 필드입니다. 에러 응답은 클라이언트의
분기 처리와 서버 디버깅을 위해 `error` 객체를 추가합니다.

```json
{
  "code": 400,
  "message": "유효하지 않은 요청 파라미터입니다.",
  "data": null,
  "error": {
    "code": "INVALID_REQUEST",
    "detail": "repoUrl must be a public GitHub repository URL",
    "field": "repoUrl",
    "retryable": false
  }
}
```

- `code`는 실제 HTTP status와 같아야 합니다.
- `message`는 사용자에게 노출 가능한 안전한 메시지여야 합니다.
- 오류 응답의 `data`는 항상 `null`입니다.
- `error.code`는 `UPPER_SNAKE_CASE`의 도메인 오류 코드입니다.
- `error.detail`에는 토큰, 내부 경로, stack trace를 포함하지 않습니다.
- 기존의 최상위 `error`, `errorCode` 문자열은 신규 API에서 사용하지 않습니다.

API별 오류 코드는 `docs/03_API/ERROR_CODES.md`를 기준으로 합니다.

## 2. HTTP Status Code 사용 규칙

API 명세서(Notion)에 정의된 에러 코드 규칙을 엄격히 준수합니다.

| Status Code | 에러 이름 | 발생 상황 및 설명 |
|---|---|---|
| `400` | Bad Request | 클라이언트의 요청 파라미터가 누락되었거나, 형식이 잘못된 경우 (예: 필수 필드 누락, 유효하지 않은 URL 형태) |
| `401` | Unauthorized | 인증 토큰이 없거나 만료된 경우 (로그인 필요) |
| `403` | Forbidden | 토큰은 유효하나 해당 자원에 대한 접근 권한이 없는 경우 (예: 타인의 프로젝트 접근) |
| `404` | Not Found | 요청한 리소스를 찾을 수 없는 경우 (예: 존재하지 않는 `job_id`, 삭제된 프로젝트 조회) |
| `409` | Conflict | 리소스 상태와 충돌이 발생하는 경우 (예: 이미 진행 중인 분석 작업의 중복 요청) |
| `408` | Request Timeout | 서버에서 수행한 clone 등 제한 시간이 초과된 경우 |
| `413` | Content Too Large | clone 이후 실제 파일 수 또는 크기 제한을 초과한 경우 |
| `422` | Unprocessable Content | 요청 형식은 맞지만 선행 분석 미완료 등 의미상 처리할 수 없는 경우 |
| `500` | Internal Server Error | 서버 내부 로직 오류, DB 연결 실패, 외부 API(GitHub 등) 호출 중 서버 측 처리 실패 |

## 3. 세부 API (Notion 명세) 에러 처리 주의사항

최근 PR 리뷰(예: PR #13)에서 지적된 가장 흔한 실수는 다음과 같습니다.

### 🚨 모든 예외를 404로 던지지 마세요
데이터베이스 조회 시 결과가 없을 때만 `404 Not Found`를 사용해야 합니다.
- **잘못된 예시**: 파라미터가 이상하거나 비즈니스 로직 예외가 터졌는데 404를 리턴함
- **올바른 예시**: `job_id` 형식이 틀리면 `400`, DB에서 `job_id`를 조회했는데 없으면 `404`, 파일 파싱 중 에러나면 `500`으로 명확히 구분하여 반환합니다.

### FastAPI 구현 참고
FastAPI 백엔드에서는 `HTTPException`을 사용하여 명확히 상태 코드를 반환해야 합니다.

```python
from fastapi import HTTPException

# 잘못된 예 (절대 사용 금지)
if not job_id:
    raise HTTPException(status_code=404, detail="에러 발생")

# 올바른 예
if not job_id:
    raise HTTPException(status_code=400, detail="job_id가 제공되지 않았습니다.")

job = db.get_job(job_id)
if not job:
    raise HTTPException(status_code=404, detail="해당 job_id를 찾을 수 없습니다.")
```

## 4. 스트리밍 오류 규칙

### SSE

- 스트림 연결 전에 검증이 실패하면 일반 HTTP status와 표준 오류 envelope를 반환합니다.
- `text/event-stream` 응답이 시작된 뒤에는 status를 바꿀 수 없으므로 `error` 이벤트를 발행합니다.
- `error` 이벤트에는 `code`, `message`, `retryable`만 포함하고 내부 예외는 노출하지 않습니다.
- 치명적 `error`, `completed`, `failed` 이벤트를 보낸 뒤 스트림을 종료합니다.

```text
event: error
data: {"code":"AGENT_INTERNAL_ERROR","message":"답변 생성 중 오류가 발생했습니다.","retryable":true}
```

### WebSocket

| Close Code | Error Code | 설명 |
| :--- | :--- | :--- |
| 1000 | `NORMAL_CLOSURE` | 최종 이벤트 전송 후 정상 종료 |
| 1008 | `POLICY_VIOLATION` | 인증 또는 정책 검증 실패 |
| 1011 | `SERVER_ERROR` | 서버 내부 오류 |
| 4004 | `JOB_NOT_FOUND` | job_id가 없거나 형식이 유효하지 않음 |
| 4008 | `JOB_ALREADY_DONE` | 완료 또는 실패한 작업에 연결 시도 |

## 5. 재시도 규칙

- `401`: 재인증 후 새 요청으로 실행합니다.
- `403`, `404`, `413`, `422`: 자동 재시도하지 않습니다.
- `408` 및 `retryable=true`인 `500`: 멱등 요청만 제한적으로 재시도합니다.
- 작업 생성 `POST`는 중복 생성 위험이 있으므로 상태 조회 후 재시도합니다.
