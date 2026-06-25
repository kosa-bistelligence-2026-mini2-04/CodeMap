# PROJECT AUTH 기능 명세서

> **도메인**: PROJECT | **모듈**: PROJECT-AUTH | **최종 업데이트**: 2026-06-22


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase | 담당자 | 작업 상태 |
| --- | --- | --- | --- | --- | --- |
| PROJECT-AUTH-B-101 | 회원가입 API | Backend | Phase 1 | oosuhada | 진행 중 |
| PROJECT-AUTH-B-102 | 로그인 API | Backend | Phase 1 | oosuhada | 진행 중 |
| PROJECT-AUTH-B-103 | 토큰 갱신 API | Backend | Phase 1 | oosuhada | 진행 중 |
| PROJECT-AUTH-B-104 | JWT 검증 의존성 (전역 미들웨어) | Backend | Phase 1 | oosuhada | 진행 중 |
| PROJECT-AUTH-B-105 | 로그아웃 API | Backend | Phase 1 | oosuhada | 진행 중 |
| PROJECT-AUTH-F-101 | 로그인 UI 및 토큰 저장 | Frontend | Phase 1 | oosuhada | 진행 중 |
| PROJECT-AUTH-F-102 | 회원가입 UI | Frontend | Phase 1 | oosuhada | 진행 중 |
| PROJECT-AUTH-F-103 | 인증 상태 전역 관리 (Zustand) | Frontend | Phase 1 | oosuhada | 진행 중 |

---

## Phase 1

### PROJECT-AUTH-B-101: 회원가입 API

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | AUTH |
| Endpoint | `POST /api/auth/register` |

**설명**

이메일 + 비밀번호 기반 회원가입. 비밀번호는 bcrypt로 해싱하여 저장.

**구현 노트**

- 이메일 중복 검사 (409 CONFLICT)
- 비밀번호 최소 8자, bcrypt 해싱
- 응답: `{ code: 201, message: "created", data: { userId, email } }`
- `users` 테이블에 저장


### PROJECT-AUTH-B-102: 로그인 API

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | AUTH |
| Endpoint | `POST /api/auth/login` |

**설명**

이메일 + 비밀번호로 인증하여 JWT Access Token + Refresh Token 발급.

**구현 노트**

- Access Token: 만료 시간 1시간 (HS256)
- Refresh Token: 만료 시간 7일, DB에 저장 (`cm-refresh-token` HttpOnly 쿠키로 전달)
- 응답: `{ code: 200, message: "success", data: { accessToken, expiresIn } }`
- `python-jose` 라이브러리 사용


### PROJECT-AUTH-B-103: 토큰 갱신 API

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | AUTH |
| Endpoint | `POST /api/auth/refresh` |

**설명**

Refresh Token(HttpOnly 쿠키 또는 Body)으로 새로운 Access Token 발급.

**구현 노트**

- 쿠키 기반 요청 기본 (`cm-refresh-token`), 하위 호환성을 위해 body의 refreshToken도 선택적 지원
- Refresh Token DB 조회 → 유효성 검증 → 새 Access Token 발급
- 오래된 Refresh Token 교체 (Rotation), 응답 시 새 토큰을 HttpOnly 쿠키로 재설정
- 에러: 401 `INVALID_REFRESH_TOKEN`


### PROJECT-AUTH-B-104: JWT 검증 의존성 (전역 미들웨어)

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | AUTH |

**설명**

FastAPI `Depends()`로 주입 가능한 JWT 검증 함수. 각 보호된 엔드포인트에 적용.

**구현 노트**

- `app/infra/auth.py`에 `get_current_user(token: str = Depends(oauth2_scheme))` 구현
- JWT 서명 검증 (HS256), 만료 시간 확인
- 검증 실패 시 401 `UNAUTHORIZED` 반환
- 적용 대상: `/api/list/*`, `/api/parse/*`, `/api/repo/*` (일부 예외 제외)
- `JWT_SECRET`, `JWT_ALGORITHM` 환경변수로 관리


### PROJECT-AUTH-B-105: 로그아웃 API

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | AUTH |
| Endpoint | `POST /api/auth/logout` |

**설명**

서버 측 Refresh Token 무효화 및 쿠키 삭제.

**구현 노트**

- DB에서 해당 유저의 Refresh Token 삭제
- `cm-refresh-token` HttpOnly 쿠키 삭제 (만료 처리)
- Access Token은 만료 시간 그대로 유지 (stateless)


### PROJECT-AUTH-F-101: 로그인 UI 및 토큰 저장

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | AUTH |

**설명**

로그인 폼 제출 → API 호출 → Access Token을 `cm-access-token` 키로 localStorage에 저장.

**구현 노트**

- 토큰 저장 키: `cm-access-token` (통일, 기존 `access_token` / `accessToken` / `token` fallback 제거)
- Refresh Token: httpOnly 쿠키 또는 `cm-refresh-token` 키로 저장
- 로그인 성공 시 이전 페이지로 redirect


### PROJECT-AUTH-F-102: 회원가입 UI

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | AUTH |

**설명**

이메일 + 비밀번호 + 비밀번호 확인 입력 폼.

**구현 노트**

- 클라이언트 사이드 유효성 검사
- 회원가입 성공 시 자동 로그인 처리


### PROJECT-AUTH-F-103: 인증 상태 전역 관리 (Zustand)

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | AUTH |

**설명**

Zustand store에서 인증 상태(isLoggedIn, user, accessToken)를 전역 관리.

**구현 노트**

- `useAuthStore`: `{ user, accessToken, login(), logout(), refreshToken() }`
- Access Token 만료 시 자동 갱신 (axios interceptor 패턴 또는 fetch wrapper)
- 페이지 새로고침 시 localStorage → store 복원

---

## API 명세

### AUTH-API-001: 회원가입

| 항목 | 값 |
| --- | --- |
| Endpoint | `POST /api/auth/register` |
| 상태 | 진행 중 |

**Request Body**

| 필드명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| email | String | Y | 이메일 주소 |
| password | String | Y | 비밀번호 (최소 8자) |

**성공 응답 — 201 Created**

```json
{
  "code": 201,
  "message": "created",
  "data": {
    "userId": "uuid",
    "email": "user@example.com"
  }
}
```

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 400 | INVALID_EMAIL | 이메일 형식 오류 |
| 400 | PASSWORD_TOO_SHORT | 비밀번호 8자 미만 |
| 409 | EMAIL_ALREADY_EXISTS | 이미 등록된 이메일 |

---

### AUTH-API-002: 로그인

| 항목 | 값 |
| --- | --- |
| Endpoint | `POST /api/auth/login` |
| 상태 | 진행 중 |

**Request Body**

| 필드명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| email | String | Y | 이메일 주소 |
| password | String | Y | 비밀번호 |

**성공 응답 — 200 OK**

- `Set-Cookie: cm-refresh-token=...; HttpOnly; SameSite=Lax; Path=/api/auth` 헤더 포함

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "accessToken": "eyJhbGci...",
    "expiresIn": 3600
  }
}
```

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 401 | INVALID_CREDENTIALS | 이메일 또는 비밀번호 불일치 |
| 404 | USER_NOT_FOUND | 존재하지 않는 이메일 |

---

### AUTH-API-003: 토큰 갱신

| 항목 | 값 |
| --- | --- |
| Endpoint | `POST /api/auth/refresh` |
| 상태 | 진행 중 |

**Request Body**

| 필드명 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| refreshToken | String | N | (선택적 하위 호환) 기존 발급된 Refresh Token. 기본적으로 `cm-refresh-token` HttpOnly 쿠키 사용 |

**성공 응답 — 200 OK**

- 새로운 Refresh Token 발급 시 `Set-Cookie: cm-refresh-token=...; HttpOnly; SameSite=Lax; Path=/api/auth` 헤더 포함

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "accessToken": "eyJhbGci...",
    "expiresIn": 3600
  }
}
```

**에러 응답**

| HTTP Status | Error Code | 설명 |
| --- | --- | --- |
| 401 | INVALID_REFRESH_TOKEN | Refresh Token 만료 또는 위조 |

---

### AUTH-API-004: 로그아웃

| 항목 | 값 |
| --- | --- |
| Endpoint | `POST /api/auth/logout` |
| 상태 | 진행 중 |

**Headers**

| 헤더명 | 값 | 필수 |
| --- | --- | --- |
| Authorization | Bearer {accessToken} | Y |

**성공 응답 — 200 OK**

- `cm-refresh-token` 쿠키 무효화 헤더 포함

```json
{
  "code": 200,
  "message": "success",
  "data": null
}
```

---

## 환경변수 추가 사항

`backend/.env` 및 `infra/config.py`에 아래 항목 추가 필요:

```
JWT_SECRET=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## 의존성 추가 사항

`backend/requirements.txt`에 아래 패키지 추가 필요:

```
python-jose[cryptography]
passlib[bcrypt]
```
