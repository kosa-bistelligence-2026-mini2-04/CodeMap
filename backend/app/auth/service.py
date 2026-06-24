"""
AUTH 도메인 Service 계층 (PROJECT-AUTH)

회원가입, 로그인, 토큰 갱신, 로그아웃 비즈니스 로직.
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.repository import AuthRepository
from app.auth.schemas import (
    LoginData,
    LoginResponse,
    LogoutResponse,
    RefreshData,
    RefreshResponse,
    RegisterData,
    RegisterResponse,
)
from app.infra.auth import create_access_token
from app.infra.config import get_settings
from app.common.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# bcrypt 컨텍스트 (자동 salt 포함)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_refresh_token(user_id: str, email: str) -> str:
    """
    Refresh Token도 JWT로 생성 (만료 기간만 더 길게).
    payload에 type=refresh 를 추가해 Access Token과 구분.
    """
    from jose import jwt

    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "refresh",
        "jti": str(uuid4()),
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = AuthRepository(db)

    # ──────────────────────────────────────────────
    # 회원가입 (PROJECT-AUTH-B-101)
    # ──────────────────────────────────────────────
    async def register(self, email: str, password: str) -> RegisterResponse:
        """
        이메일 중복 확인 후 bcrypt 해싱하여 저장.

        Raises:
            EmailAlreadyExistsError (409): 이미 등록된 이메일
        """
        existing = await self.repo.get_user_by_email(email)
        if existing:
            raise EmailAlreadyExistsError()

        hashed = _hash_password(password)
        user = await self.repo.create_user(email=email, hashed_password=hashed)
        await self.db.commit()

        logger.info("[AUTH] 회원가입 완료: user_id=%s", user.id)
        return RegisterResponse(
            data=RegisterData(userId=str(user.id), email=user.email)
        )

    # ──────────────────────────────────────────────
    # 로그인 (PROJECT-AUTH-B-102)
    # ──────────────────────────────────────────────
    async def login(self, email: str, password: str) -> LoginResponse:
        """
        이메일/비밀번호 검증 후 Access + Refresh Token 발급.

        Raises:
            InvalidCredentialsError (401): 이메일/비밀번호 불일치
        """
        user = await self.repo.get_user_by_email(email)
        if not user or not _verify_password(password, user.hashed_password):
            raise InvalidCredentialsError()

        user_id = str(user.id)
        access_token = create_access_token(user_id=user_id, email=user.email)
        refresh_token = _create_refresh_token(user_id=user_id, email=user.email)

        # Refresh Token DB 저장
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.repo.save_refresh_token(
            user_id=user.id, token=refresh_token, expires_at=expires_at
        )
        await self.db.commit()

        logger.info("[AUTH] 로그인 성공: user_id=%s", user_id)
        return LoginResponse(
            data=LoginData(
                accessToken=access_token,
                refreshToken=refresh_token,
                expiresIn=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )
        )

    # ──────────────────────────────────────────────
    # 토큰 갱신 (PROJECT-AUTH-B-103)
    # ──────────────────────────────────────────────
    async def refresh(self, refresh_token: str) -> RefreshResponse:
        """
        Refresh Token 검증 후 새 Access Token 발급 (Rotation).

        Raises:
            InvalidRefreshTokenError (401): 토큰 없음/만료/위조
        """
        from jose import JWTError, jwt

        # 1. DB에서 토큰 존재 여부 확인
        rt_record = await self.repo.get_refresh_token(refresh_token)
        if not rt_record:
            raise InvalidRefreshTokenError()

        # 2. 만료 시간 확인
        if rt_record.expires_at < datetime.now(timezone.utc):
            await self.repo.delete_refresh_token(refresh_token)
            await self.db.commit()
            raise InvalidRefreshTokenError()

        # 3. JWT 서명 검증 및 payload 추출
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            if payload.get("type") != "refresh":
                raise InvalidRefreshTokenError()
        except JWTError:
            raise InvalidRefreshTokenError()

        # 4. 새 토큰 발급 (Access & Refresh - Rotation)
        new_access_token = create_access_token(
            user_id=payload["sub"], email=payload["email"]
        )
        new_refresh_token = _create_refresh_token(
            user_id=payload["sub"], email=payload["email"]
        )

        # 5. 기존 토큰 삭제 후 새 토큰 저장
        await self.repo.delete_refresh_token(refresh_token)
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        # rt_record.user_id는 UUID 객체이므로 그대로 사용 가능
        await self.repo.save_refresh_token(
            user_id=rt_record.user_id, token=new_refresh_token, expires_at=expires_at
        )
        await self.db.commit()

        logger.info("[AUTH] 토큰 갱신 (Rotation): user_id=%s", payload["sub"])
        return RefreshResponse(
            data=RefreshData(
                accessToken=new_access_token,
                refreshToken=new_refresh_token,
                expiresIn=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )
        )

    # ──────────────────────────────────────────────
    # 로그아웃 (PROJECT-AUTH-B-105)
    # ──────────────────────────────────────────────
    async def logout(self, refresh_token: str) -> LogoutResponse:
        """
        서버 측 Refresh Token 무효화.
        토큰이 없어도 에러 없이 성공 반환 (idempotent).
        """
        deleted = await self.repo.delete_refresh_token(refresh_token)
        await self.db.commit()
        logger.info("[AUTH] 로그아웃: 삭제된 토큰 %d건", deleted)
        return LogoutResponse()
