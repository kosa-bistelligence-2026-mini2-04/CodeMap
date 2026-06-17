# CodeMap API 에러 처리 가이드 (Error Handling Guide)

API 개발 시 발생할 수 있는 에러 상황에 대해 프로젝트 내 통일된 규격을 정의합니다. 
PR 리뷰 피드백에서 지적된 바와 같이, **모든 에러를 일괄적으로 `404 Not Found`로 처리하는 것은 엄격히 금지**됩니다. 상황에 맞는 HTTP Status Code와 정해진 응답 포맷을 사용하여야 합니다.

## 1. 기본 에러 응답 포맷

모든 에러 응답은 성공 응답과 동일하게 `code`, `message` 구조를 포함해야 하며, 클라이언트가 에러를 파악할 수 있도록 작성되어야 합니다.

```json
{
  "code": 400,
  "message": "Bad Request: 유효하지 않은 요청 파라미터입니다.",
  "data": null
}
```

## 2. HTTP Status Code 사용 규칙

API 명세서(Notion)에 정의된 에러 코드 규칙을 엄격히 준수합니다.

| Status Code | 에러 이름 | 발생 상황 및 설명 |
|---|---|---|
| `400` | Bad Request | 클라이언트의 요청 파라미터가 누락되었거나, 형식이 잘못된 경우 (예: 필수 필드 누락, 유효하지 않은 URL 형태) |
| `401` | Unauthorized | 인증 토큰이 없거나 만료된 경우 (로그인 필요) |
| `403` | Forbidden | 토큰은 유효하나 해당 자원에 대한 접근 권한이 없는 경우 (예: 타인의 프로젝트 접근) |
| `404` | Not Found | 요청한 리소스를 찾을 수 없는 경우 (예: 존재하지 않는 `job_id`, 삭제된 프로젝트 조회) |
| `409` | Conflict | 리소스 상태와 충돌이 발생하는 경우 (예: 이미 진행 중인 분석 작업의 중복 요청) |
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
