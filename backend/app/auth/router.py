"""
AUTH 도메인 라우터 (PROJECT-AUTH)

엔드포인트:
  POST /api/auth/register  — 회원가입 (AUTH-API-001)
  POST /api/auth/login     — 로그인 (AUTH-API-002)
  POST /api/auth/refresh   — 토큰 갱신 (AUTH-API-003)
  POST /api/auth/logout    — 로그아웃 (AUTH-API-004)
"""

from fastapi import APIRouter, Body, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import (
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.auth.service import AuthService
from app.infra.auth import get_current_user
from app.infra.config import get_settings
from app.infra.database import get_db

router = APIRouter(prefix="/api/auth", tags=["Auth"])
settings = get_settings()
REFRESH_COOKIE_NAME = "cm-refresh-token"


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        path="/api/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        path="/api/auth",
    )


def _refresh_token_from(request_body: RefreshRequest | None, request: Request) -> str:
    if request_body and request_body.refreshToken:
        return request_body.refreshToken
    return request.cookies.get(REFRESH_COOKIE_NAME, "")


# ──────────────────────────────────────────────
# POST /api/auth/register — 회원가입
# ──────────────────────────────────────────────
@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=201,
    summary="회원가입",
    description="이메일 + 비밀번호로 신규 계정 생성. 비밀번호는 bcrypt로 해싱 저장.",
)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    return await AuthService(db).register(
        email=request.email,
        password=request.password,
    )


# ──────────────────────────────────────────────
# POST /api/auth/login — 로그인
# ──────────────────────────────────────────────
@router.post(
    "/login",
    response_model=LoginResponse,
    summary="로그인",
    description="이메일 + 비밀번호 인증 후 JWT Access Token과 Refresh Token 발급.",
)
async def login(
    request: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    result = await AuthService(db).login(
        email=request.email,
        password=request.password,
    )
    _set_refresh_cookie(response, getattr(result, "refresh_token"))
    return result


# ──────────────────────────────────────────────
# POST /api/auth/refresh — 토큰 갱신
# ──────────────────────────────────────────────
@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="토큰 갱신",
    description="Refresh Token으로 새 Access Token 발급.",
)
async def refresh_token(
    request: Request,
    response: Response,
    request_body: RefreshRequest | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    result = await AuthService(db).refresh(refresh_token=_refresh_token_from(request_body, request))
    _set_refresh_cookie(response, getattr(result, "refresh_token"))
    return result


# ──────────────────────────────────────────────
# POST /api/auth/logout — 로그아웃
# ──────────────────────────────────────────────
@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="로그아웃",
    description="서버 측 Refresh Token 무효화. Access Token은 만료될 때까지 자체 유효.",
)
async def logout(
    response: Response,
    http_request: Request,
    request: RefreshRequest | None = Body(default=None),
    _: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LogoutResponse:
    result = await AuthService(db).logout(refresh_token=_refresh_token_from(request, http_request))
    _clear_refresh_cookie(response)
    return result
