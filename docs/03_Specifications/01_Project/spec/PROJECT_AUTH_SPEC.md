# PROJECT AUTH 기능 명세서

> **도메인**: PROJECT | **모듈**: PROJECT-AUTH | **최종 업데이트**: 2026-06-26


## 전체 기능 요약

| 기능 ID | 기능명 | 계층 | Phase | 담당자 | 작업 상태 |
| --- | --- | --- | --- | --- | --- |
| PROJECT-AUTH-B-101 | 회원가입 API | Backend | Phase 1 | oosuhada | 진행 중 |
| PROJECT-AUTH-B-102 | 로그인 API | Backend | Phase 1 | oosuhada | 진행 중 |
| PROJECT-AUTH-B-103 | 토큰 갱신 API | Backend | Phase 1 | oosuhada | 진행 중 |
| PROJECT-AUTH-B-104 | JWT 검증 의존성 (전역 미들웨어) | Backend | Phase 1 | oosuhada | 진행 중 |
| PROJECT-AUTH-B-105 | 로그아웃 API | Backend | Phase 1 | oosuhada | 진행 중 |
| PROJECT-AUTH-B-201 | current user 기반 resource scope 전달 | Backend | Phase 2 | oosuhada | 제안 |
| PROJECT-AUTH-F-101 | 로그인 UI 및 토큰 저장 | Frontend | Phase 1 | oosuhada | 진행 중 |
| PROJECT-AUTH-F-102 | 회원가입 UI | Frontend | Phase 1 | oosuhada | 진행 중 |
| PROJECT-AUTH-F-103 | 인증 상태 전역 관리 (Zustand) | Frontend | Phase 1 | oosuhada | 진행 중 |
| PROJECT-AUTH-F-104 | Auth 실패 메시지 사용자 언어 정규화 | Frontend | Phase 1 | - | 제안 |
| PROJECT-AUTH-F-105 | 회원가입 실시간 검증 및 입력 피드백 | Frontend | Phase 1 | - | 제안 |

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
- Phase 2 팀/개인 기록 분리에서는 보호된 LIST/REPO/CHAT endpoint가 `get_current_user`의 `sub`를 사용해 `analysis_jobs.created_by_user_id`, `visibility`, `team_id` 권한을 검사해야 합니다.


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

### PROJECT-AUTH-B-201: current user 기반 resource scope 전달

| 항목 | 내용 |
| --- | --- |
| 분류 | Backend |
| 모듈명 | AUTH |
| 관련 명세 | `PROJECT_TEAM_SPEC.md` |

**설명**

Phase 2 팀 기능에서는 인증이 단순 로그인 여부 확인에 그치지 않고, 분석 이력과 채팅 기록의 조회 범위를 결정하는 기준이 됩니다. `get_current_user`는 최소 `{ sub, email }`을 안정적으로 반환해야 하며, LIST/REPO/CHAT 도메인은 이 값을 사용해 private/team resource 접근 권한을 확인합니다.

**구현 노트**

- private resource: `created_by_user_id == current_user.sub`
- team resource: `team_members.team_id == resource.team_id` AND `team_members.user_id == current_user.sub` AND `status='active'`
- 권한 실패 시 403 `FORBIDDEN`, 세부 코드 `TEAM_ACCESS_DENIED` 또는 `PRIVATE_RESOURCE_DENIED`


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
- Issue #175: 이메일 형식, 비밀번호 규칙, 비밀번호 확인 일치 여부는 제출 전 field-level로 실시간 검증합니다.
- Issue #175: invalid submit 시 입력칸 강조 또는 짧은 shake 같은 micro interaction을 사용할 수 있으나, `prefers-reduced-motion` 환경에서는 정적 강조로 대체합니다.


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

### PROJECT-AUTH-F-104: Auth 실패 메시지 사용자 언어 정규화

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | AUTH |
| 관련 이슈 | Issue #174 |
| 관련 계약 | `ERROR_CODES.md`, `ERROR_HANDLING.md` |

**설명**

회원가입/로그인 실패 시 HTTP status나 개발자용 fallback을 그대로 노출하지 않고, 표준 오류 envelope의 `message`, `error.code`, `error.field`를 사용자 문구와 field-level 오류로 변환합니다.

**구현 노트**

- `EMAIL_ALREADY_EXISTS`, `INVALID_EMAIL`, `PASSWORD_TOO_SHORT`, `INVALID_CREDENTIALS`는 한국어 사용자 문구로 매핑합니다.
- `error.field`가 있으면 해당 입력칸 하단에 표시하고, 전역 오류는 form 상단 alert 영역에 표시합니다.
- `HTTP 409` 같은 status 중심 표현은 기본 UI에 직접 노출하지 않고 debug/telemetry context에만 남깁니다.
- 공통 parser 규칙은 Issue #176의 frontend API error parser를 따릅니다.

**완료 조건**

- 이메일 중복, 이메일 형식 오류, 비밀번호 규칙 위반, 로그인 실패가 사용자 언어로 표시됩니다.
- 오류 후 사용자가 수정해야 할 입력 위치를 즉시 알 수 있습니다.

### PROJECT-AUTH-F-105: 회원가입 실시간 검증 및 입력 피드백

| 항목 | 내용 |
| --- | --- |
| 분류 | Frontend |
| 모듈명 | AUTH |
| 관련 이슈 | Issue #175 |

**설명**

회원가입 화면은 제출 전 이메일/비밀번호/비밀번호 확인 상태를 검증하고, 어떤 규칙이 충족되지 않았는지 입력 중에 안내합니다.

**구현 노트**

- 이메일은 blur 및 입력 안정화 시점에 형식 오류를 표시합니다.
- 비밀번호 규칙은 checklist 형태로 분해해 통과/실패 상태를 표시합니다.
- 비밀번호 확인 불일치는 사용자가 확인 입력을 수정하는 즉시 갱신합니다.
- backend schema와 frontend rule이 어긋나지 않도록 최소 길이와 금지 조건을 문서/상수 기준으로 맞춥니다.

**완료 조건**

- 제출 전 주요 입력 오류가 field-level로 보입니다.
- motion 감소 설정 사용자는 애니메이션 없이 동일한 오류 정보를 받습니다.

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

## 환경변수 및 물리 키 파일 추가 사항

`backend/.env`, `infra/config.py` 및 물리 키 파일 설정을 아래와 같이 현행화하여 관리합니다.

* **🔑 JWT 대칭키 물리 격리 파일 (`.jwt_secret_key`)**
  * 보안을 극대화하기 위해 `.env` 파일과 분리된 숨김 파일 **`.jwt_secret_key`**에 암호화 대칭키 문자열을 단독 저장합니다.
  * 해당 키 파일은 원격 형상 관리에 유출되지 않도록 루트 `.gitignore`에 등록하여 관리합니다 (`backend/.jwt_secret_key`).
  * 파일이 실재하지 않는 최초 기동 환경인 경우, 백엔드 기동 단계(`config.py` validator)에서 `secrets.token_urlsafe(32)` 보안 난수를 적용해 키 파일을 자동 생성 및 유닉스/리눅스 권한 격리(`chmod 600`)를 자동 보장합니다.
  * 수동 또는 배포 파이프라인에서 키를 사전 생성하기 위한 스크립트(`scripts/generate_jwt_key.ps1` 및 `.sh`)를 제공합니다.

* **⚙️ 환경변수 설정 (`backend/.env`)**
  ```env
  JWT_SECRET_KEY_PATH=.jwt_secret_key
  JWT_ALGORITHM=HS256
  JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
  JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
  ```

---

## 의존성 추가 사항

`backend/requirements.txt`에 아래 호환성 최적화 패키지 및 대칭 암호화 패키지가 지정되어야 합니다:

```
# JWT 검증 및 대칭 암호화 적용 (Issue #262)
PyJWT>=2.8.0
cryptography>=42.0.0
bcrypt>=4.1.0
```
