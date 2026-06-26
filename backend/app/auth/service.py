"""
AUTH 도메인 Service 계층 (PROJECT-AUTH)

회원가입, 로그인, 토큰 갱신, 로그아웃 비즈니스 로직.
"""

import logging
import bcrypt
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy.exc import IntegrityError
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

logger = logging.getLogger(__name__)
settings = get_settings()


import hashlib

def _prepare_password(plain: str) -> str:
    # bcrypt는 최대 72바이트만 인식하므로 긴 패스워드를 방어하기 위해 SHA-256 선행 해시 사용
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()

def _hash_password(plain: str) -> str:
    prepared = _prepare_password(plain)
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(prepared.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def _verify_password(plain: str, hashed: str) -> bool:
    prepared = _prepare_password(plain)
    try:
        return bcrypt.checkpw(prepared.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


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
        """
        existing = await self.repo.get_user_by_email(email)
        if existing:
            logger.error("[AUTH] 회원가입 실패 (이메일 중복): %s", email)
            return RegisterResponse(success=False, message="이미 가입된 이메일입니다.", error_code="EMAIL_ALREADY_EXISTS")

        hashed = _hash_password(password)
        try:
            user = await self.repo.create_user(email=email, hashed_password=hashed)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            logger.error("[AUTH] 회원가입 실패 (동시성 중복): %s", email)
            return RegisterResponse(success=False, message="이미 가입된 이메일입니다.", error_code="EMAIL_ALREADY_EXISTS")

        logger.info("[AUTH] 회원가입 완료: user_id=%s", user.id)
        return RegisterResponse(
            success=True,
            data=RegisterData(userId=str(user.id), email=user.email)
        )

    # ──────────────────────────────────────────────
    # 로그인 (PROJECT-AUTH-B-102)
    # ──────────────────────────────────────────────
    async def login(self, email: str, password: str) -> LoginResponse:
        """
        이메일/비밀번호 검증 후 Access + Refresh Token 발급.
        """
        user = await self.repo.get_user_by_email(email)
        if not user or not _verify_password(password, user.hashed_password):
            logger.warning("[AUTH] 로그인 실패 (자격증명 불일치): %s", email)
            return LoginResponse(success=False, message="이메일 또는 비밀번호가 올바르지 않습니다.", error_code="INVALID_CREDENTIALS")

        user_id = str(user.id)
        access_token = create_access_token(user_id=user_id, email=user.email)
        refresh_token = _create_refresh_token(user_id=user_id, email=user.email)

        # Refresh Token 증식 방지 (기존 토큰 모두 삭제 후 새 토큰 발급 - 단일 기기 로그인 원칙 적용)
        await self.repo.delete_all_refresh_tokens(user.id)
        
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
        )
        await self.repo.save_refresh_token(
            user_id=user.id, token=refresh_token, expires_at=expires_at
        )
        await self.db.commit()

        logger.info("[AUTH] 로그인 성공: user_id=%s", user_id)
        response = LoginResponse(
            success=True,
            data=LoginData(
                accessToken=access_token,
                expiresIn=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )
        )
        object.__setattr__(response, "refresh_token", refresh_token)
        return response

    # ──────────────────────────────────────────────
    # 토큰 갱신 (PROJECT-AUTH-B-103)
    # ──────────────────────────────────────────────
    async def refresh(self, refresh_token: str) -> RefreshResponse:
        """
        Refresh Token 검증 후 새 Access Token 발급 (Rotation).
        """
        from jose import JWTError, jwt

        # 1. DB에서 토큰 존재 여부 확인
        rt_record = await self.repo.get_refresh_token(refresh_token)
        if not rt_record:
            logger.warning("[AUTH] 토큰 갱신 실패: 토큰이 존재하지 않음")
            return RefreshResponse(success=False, message="유효하지 않은 토큰입니다.")

        # 2. 만료 시간 확인
        if rt_record.expires_at < datetime.now(timezone.utc):
            await self.repo.delete_refresh_token(refresh_token)
            await self.db.commit()
            logger.warning("[AUTH] 토큰 갱신 실패: 토큰 만료")
            return RefreshResponse(success=False, message="토큰이 만료되었습니다. 다시 로그인해주세요.")

        # 3. JWT 서명 검증 및 payload 추출
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            if payload.get("type") != "refresh":
                logger.warning("[AUTH] 토큰 갱신 실패: 타입 불일치")
                return RefreshResponse(success=False, message="유효하지 않은 토큰 타입입니다.")
        except JWTError:
            logger.warning("[AUTH] 토큰 갱신 실패: JWT 서명 검증 실패")
            return RefreshResponse(success=False, message="유효하지 않은 토큰입니다.")

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
        response = RefreshResponse(
            success=True,
            data=RefreshData(
                accessToken=new_access_token,
                expiresIn=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            )
        )
        object.__setattr__(response, "refresh_token", new_refresh_token)
        return response

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
        return LogoutResponse(success=True)
