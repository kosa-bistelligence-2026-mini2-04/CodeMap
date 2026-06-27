"""
AUTH 도메인 Pydantic 스키마 (PROJECT-AUTH)

요청/응답 DTO 정의. 명세서 AUTH-API-001~004 대응.
"""

from pydantic import BaseModel, EmailStr, Field


# ──────────────────────────────────────────────
# AUTH-API-001: 회원가입
# ──────────────────────────────────────────────
class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="이메일 주소")
    password: str = Field(..., min_length=8, description="비밀번호 (최소 8자)")


class RegisterData(BaseModel):
    userId: str
    email: str


class RegisterResponse(BaseModel):
    success: bool = True
    code: int = 201
    message: str = "created"
    error_code: str | None = None
    data: RegisterData | None = None


# ──────────────────────────────────────────────
# AUTH-API-002: 로그인
# ──────────────────────────────────────────────
class LoginRequest(BaseModel):
    email: EmailStr = Field(..., description="이메일 주소")
    password: str = Field(..., description="비밀번호")


class LoginData(BaseModel):
    accessToken: str
    expiresIn: int = 3600  # 초 단위


class LoginResponse(BaseModel):
    success: bool = True
    code: int = 200
    message: str = "success"
    error_code: str | None = None
    data: LoginData | None = None


# ──────────────────────────────────────────────
# AUTH-API-003: 토큰 갱신
# ──────────────────────────────────────────────
class RefreshRequest(BaseModel):
    refreshToken: str | None = Field(default=None, description="기존 Refresh Token")


class RefreshData(BaseModel):
    accessToken: str
    expiresIn: int = 3600


class RefreshResponse(BaseModel):
    success: bool = True
    code: int = 200
    message: str = "success"
    data: RefreshData | None = None


# ──────────────────────────────────────────────
# AUTH-API-004: 로그아웃
# ──────────────────────────────────────────────
class LogoutResponse(BaseModel):
    success: bool = True
    code: int = 200
    message: str = "success"
    data: None = None


# ──────────────────────────────────────────────
# JWT payload 타입 (내부용)
# ──────────────────────────────────────────────
class TokenData(BaseModel):
    sub: str   # user_id (UUID string)
    email: str
