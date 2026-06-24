"""
JWT 토큰 생성 및 검증 유틸리티 (PROJECT-AUTH-B-104)

FastAPI Depends()로 주입 가능한 get_current_user 함수와
JWT 생성/검증 헬퍼를 제공한다.

보호된 엔드포인트에서 사용법:
    from app.infra.auth import get_current_user
    from app.auth.schemas import TokenData

    @router.get("/protected")
    async def protected(current_user: TokenData = Depends(get_current_user)):
        ...
"""

from datetime import datetime, timedelta, timezone

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.infra.config import get_settings
from app.common.exceptions import UnauthorizedError

settings = get_settings()

# Bearer 토큰 추출기 — /api/auth/login URL은 인증 불필요이므로 auto_error=False
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ──────────────────────────────────────────────────────────────
# Access Token 생성
# ──────────────────────────────────────────────────────────────

def create_access_token(user_id: str, email: str) -> str:
    """
    JWT Access Token 생성.

    payload:
        sub  — user_id (UUID string)
        email — 이메일
        exp  — 만료 시각 (UTC)
        iat  — 발급 시각 (UTC)
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


# ──────────────────────────────────────────────────────────────
# Access Token 검증
# ──────────────────────────────────────────────────────────────

def verify_access_token(token: str) -> dict:
    """
    JWT Access Token 서명 및 만료 시간 검증.

    Returns:
        dict: 디코딩된 payload (sub, email, exp, iat)

    Raises:
        UnauthorizedError: 서명 불일치 또는 만료
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        raise UnauthorizedError()


# ──────────────────────────────────────────────────────────────
# FastAPI Depends 주입용 — 보호된 엔드포인트에서 사용
# ──────────────────────────────────────────────────────────────

def get_current_user(token: str | None = Depends(oauth2_scheme)) -> dict:
    """
    Authorization: Bearer <token> 헤더에서 토큰을 추출하여 검증.

    Returns:
        dict: { "sub": user_id, "email": email, ... }

    Raises:
        UnauthorizedError (401): 토큰 없음 / 만료 / 서명 불일치
    """
    if not token:
        raise UnauthorizedError()
    return verify_access_token(token)
