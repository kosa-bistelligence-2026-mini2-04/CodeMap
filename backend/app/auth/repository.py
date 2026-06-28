"""
AUTH 도메인 Repository 계층 (PROJECT-AUTH)

users, refresh_tokens 테이블에 대한 CRUD 비동기 함수 모음.
"""

import uuid
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import RefreshToken, User


class AuthRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── User ──────────────────────────────────────────────────────────────────

    async def create_user(self, email: str, hashed_password: str) -> User:
        """새 사용자 생성 후 반환."""
        user = User(email=email, hashed_password=hashed_password)
        self.db.add(user)
        await self.db.flush()   # id 생성을 위해 flush (commit은 service에서)
        await self.db.refresh(user)
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        """이메일로 사용자 조회."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: uuid.UUID) -> User | None:
        """UUID로 사용자 조회."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    # ── RefreshToken ─────────────────────────────────────────────────────────

    async def save_refresh_token(
        self, user_id: uuid.UUID, token: str, expires_at: datetime
    ) -> RefreshToken:
        """Refresh Token 저장."""
        rt = RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
        self.db.add(rt)
        await self.db.flush()
        return rt

    async def get_refresh_token(self, token: str) -> RefreshToken | None:
        """Refresh Token 원문으로 조회."""
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        return result.scalar_one_or_none()

    async def delete_refresh_token(self, token: str) -> int:
        """특정 Refresh Token 삭제. 삭제된 행 수 반환."""
        result = await self.db.execute(
            delete(RefreshToken).where(RefreshToken.token == token)
        )
        return result.rowcount  # type: ignore[return-value]

    async def delete_all_refresh_tokens(self, user_id: uuid.UUID) -> int:
        """해당 유저의 모든 Refresh Token 삭제 (보안 조치용)."""
        result = await self.db.execute(
            delete(RefreshToken).where(RefreshToken.user_id == user_id)
        )
        return result.rowcount  # type: ignore[return-value]

    async def delete_user(self, user_id: uuid.UUID) -> int:
        """사용자 계정 삭제. CASCADE 옵션에 의해 team_members 등도 삭제될 수 있음."""
        result = await self.db.execute(
            delete(User).where(User.id == user_id)
        )
        return result.rowcount  # type: ignore[return-value]
