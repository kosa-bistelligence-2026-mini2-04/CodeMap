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
import base64
import hashlib

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from cryptography.fernet import Fernet, InvalidToken as FernetInvalidToken
import jwt

from app.infra.config import get_settings
from app.common.exceptions import UnauthorizedError, TokenExpiredError

settings = get_settings()

# JWT_SECRET 기반 Fernet 32바이트 대칭키 결정론적 도출
_secret_bytes = settings.JWT_SECRET.encode("utf-8")
_key_hash = hashlib.sha256(_secret_bytes).digest()
_fernet_key = base64.urlsafe_b64encode(_key_hash)
_cipher_suite = Fernet(_fernet_key)


def encrypt_token(raw_token: str) -> str:
    """JWT 문자열을 AES 대칭키(Fernet)로 안전하게 암호화합니다."""
    return _cipher_suite.encrypt(raw_token.encode("utf-8")).decode("utf-8")


def decrypt_token(encrypted_token: str) -> str:
    """암호화된 JWT 문자열을 AES 대칭키(Fernet)로 복호화합니다."""
    return _cipher_suite.decrypt(encrypted_token.encode("utf-8")).decode("utf-8")

# Bearer 토큰 추출기 — /api/auth/login URL은 인증 불필요이므로 auto_error=False
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


# ──────────────────────────────────────────────────────────────
# Access Token 생성
# ──────────────────────────────────────────────────────────────

def create_access_token(user_id: str, email: str) -> str:
    """
    JWT Access Token 생성 및 AES 대칭 암호화.

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
    raw_token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encrypt_token(raw_token)


# ──────────────────────────────────────────────────────────────
# Access Token 검증
# ──────────────────────────────────────────────────────────────

def verify_access_token(token: str) -> dict:
    """
    암호화된 토큰을 복호화하고 JWT Access Token 서명 및 만료 시간을 검증.

    Returns:
        dict: 디코딩된 payload (sub, email, exp, iat)

    Raises:
        TokenExpiredError: 만료
        UnauthorizedError: 서명 불일치 또는 복호화 오류
    """
    try:
        # 1. AES 대칭키 복호화 선수행
        raw_token = decrypt_token(token)
        # 2. PyJWT 서명 및 명세 디코딩 검증
        payload = jwt.decode(
            raw_token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError()
    except (jwt.PyJWTError, FernetInvalidToken):
        raise UnauthorizedError()


# ──────────────────────────────────────────────────────────────
# FastAPI Depends 주입용 — 보호된 엔드포인트에서 사용
# ──────────────────────────────────────────────────────────────

def get_current_user(request: Request, token: str | None = Depends(oauth2_scheme)) -> dict:
    """
    Authorization: Bearer <token> 헤더에서 토큰을 추출하여 검증.

    Returns:
        dict: { "sub": user_id, "email": email, ... }

    Raises:
        UnauthorizedError (401): 토큰 없음 / 만료 / 서명 불일치
    """
    token = token or request.cookies.get("cm-access-token")
    if not token:
        raise UnauthorizedError()
    return verify_access_token(token)

def get_current_user_optional(request: Request, token: str | None = Depends(oauth2_scheme)) -> dict | None:
    token = token or request.cookies.get("cm-access-token")
    if not token:
        return None
    try:
        return verify_access_token(token)
    except (UnauthorizedError, TokenExpiredError):
        return None


async def sync_jwt_secret_with_db() -> None:
    """
    로컬 대칭키 파일과 데이터베이스 system_configs 테이블의 대칭키 값을 상호 동기화 및 복원합니다.
    (하드코딩 키가 0% 소멸되며, 파일 유실 시 DB 백업본으로 복원하고 메모리 및 Fernet 인스턴스를 재바인딩합니다.)
    """
    import os
    import uuid
    from sqlalchemy import text
    from app.infra.config import get_settings, backend_dir
    from app.infra.database import engine

    settings = get_settings()
    path = settings.JWT_SECRET_KEY_PATH
    if not os.path.isabs(path):
        path = os.path.join(backend_dir, path)

    # 1. 로컬 키 파일의 존재 여부 및 값 파악
    local_key = None
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                local_key = f.read().strip()
        except Exception as e:
            print(f"[Warning] Failed to read local JWT secret file: {e}")

    # 2. DB에서 저장된 대칭키 값 조회 및 동기화 처리 (최상단 시퀀스 키를 주 사용 대칭키로 취급)
    db_key = None
    async with engine.connect() as conn:
        # 단일 트랜잭션 내에서 조회, 난수 생성, 인서트를 직렬화하여 경쟁 상태 차단
        async with conn.begin():
            # PostgreSQL 환경에서의 테이블 락 획득 (데드락 및 중복 5개 벌크 인서트 방지)
            try:
                await conn.execute(text("LOCK TABLE system_configs IN ACCESS EXCLUSIVE MODE"))
            except Exception:
                # SQLite 등 LOCK TABLE 문법을 지원하지 않는 단위 테스트 환경은 무시하고 통과
                pass

            try:
                result = await conn.execute(
                    text("SELECT secret_key FROM system_configs ORDER BY seq_id ASC LIMIT 1")
                )
                db_key = result.scalar()
            except Exception as e:
                print(f"[Warning] Failed to query system_configs table: {e}")
                return

            # 3. 상황별 동기화 및 복구 처리
            target_key = None

            if db_key:
                # A. DB에 키가 저장되어 있는 경우 (최우선 복구 소스)
                target_key = db_key
                # 로컬 파일이 없거나 DB 키와 다르다면 로컬 파일 복원(Restore)
                if local_key != db_key:
                    try:
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(db_key + "\n")
                        if os.name != "nt":
                            os.chmod(path, 0o600)
                        print(f"[Info] Restored JWT secret key file from database at: {path}")
                    except Exception as e:
                        print(f"[Warning] Failed to restore JWT secret key file: {e}")
            else:
                # B. DB에 키가 없는 경우 (최초 기동 또는 유실 상태)
                if local_key:
                    target_key = local_key
                else:
                    # 둘 다 없는 완전 유실 상태 ➡️ 신규 보안 난수 생성
                    import secrets
                    target_key = secrets.token_urlsafe(32)
                    try:
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(target_key + "\n")
                        if os.name != "nt":
                            os.chmod(path, 0o600)
                        print(f"[Info] Generated new JWT secret key file: {path}")
                    except Exception as e:
                        print(f"[Warning] Failed to write generated JWT secret key file: {e}")

                # DB에 백업본 동기화 저장 (시퀀스 5개 행 사양 엄격 준수)
                try:
                    import secrets
                    count_res = await conn.execute(text("SELECT COUNT(*) FROM system_configs"))
                    
                    if count_res.scalar() == 0:
                        await conn.execute(
                            text(
                                "INSERT INTO system_configs (secret_key) VALUES (:k1), (:k2), (:k3), (:k4), (:k5)"
                            ),
                            {
                                "k1": target_key,
                                "k2": secrets.token_urlsafe(32),
                                "k3": secrets.token_urlsafe(32),
                                "k4": secrets.token_urlsafe(32),
                                "k5": secrets.token_urlsafe(32)
                            }
                        )
                    else:
                        await conn.execute(
                            text("UPDATE system_configs SET secret_key = :k1 WHERE seq_id = (SELECT MIN(seq_id) FROM system_configs)"),
                            {"k1": target_key}
                        )
                except Exception as e:
                    print(f"[Warning] Failed to backup JWT secret key to system_configs table: {e}")
                    # 내부 트랜잭션 에러 시 상위 asynccontextmanager (conn.begin())가 자동으로 롤백을 수행하므로 수동 롤백 생략

        # 4. 메모리상의 설정 캐시 및 Fernet 암복호화 레이어 재바인딩
        if target_key:
            settings.JWT_SECRET = target_key
            
            global _cipher_suite
            _secret_bytes = target_key.encode("utf-8")
            _key_hash = hashlib.sha256(_secret_bytes).digest()
            _fernet_key = base64.urlsafe_b64encode(_key_hash)
            _cipher_suite = Fernet(_fernet_key)
            print("[Info] Successfully bound JWT_SECRET and cipher suite.")
