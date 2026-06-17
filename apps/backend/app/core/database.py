"""
데이터베이스 연결 및 세션 관리 모듈

SQLAlchemy 비동기 엔진과 세션 팩토리를 설정하고,
FastAPI 의존성 주입(Dependency Injection)용 get_db 함수를 제공한다.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

# PostgreSQL 비동기 드라이버(asyncpg) 사용을 위한 URL 변환
ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# 비동기 SQLAlchemy 엔진 생성
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.DEBUG,  # SQL 로그 출력 여부
    pool_size=10,
    max_overflow=20,
)

# 비동기 세션 팩토리 설정
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """모든 SQLAlchemy 모델의 기반 클래스"""
    pass


async def get_db() -> AsyncSession:
    """
    FastAPI 의존성 주입용 DB 세션 제공 함수

    요청 처리 동안 하나의 세션을 유지하고, 완료 후 자동으로 닫는다.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
