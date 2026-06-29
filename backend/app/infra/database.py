"""
데이터베이스 연결 및 세션 관리 모듈

SQLAlchemy 비동기 엔진과 세션 팩토리를 설정하고,
FastAPI 의존성 주입(Dependency Injection)용 get_db 함수를 제공한다.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.infra.config import get_settings

settings = get_settings()

import re

# PostgreSQL 비동기 드라이버(asyncpg) 사용을 위한 URL 변환
# psycopg2 등 다른 드라이버가 지정되었더라도 강제로 asyncpg로 교체하여 엔진 크래시 방지
db_url_str = (
    settings.DATABASE_URL.get_secret_value()
    if hasattr(settings.DATABASE_URL, "get_secret_value")
    else settings.DATABASE_URL
)
ASYNC_DATABASE_URL = re.sub(
    r"^postgresql(\+[a-zA-Z0-9_]+)?://",
    "postgresql+asyncpg://",
    db_url_str,
)

# psycopg 비동기 드라이버 사용을 위한 URL (langgraph-checkpoint-postgres)
PSYCOPG_URL = re.sub(
    r"^postgresql(\+[a-zA-Z0-9_]+)?://",
    "postgresql://",
    db_url_str,
)

# LangGraph checkpoint용 psycopg Connection Pool
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

checkpoint_pool = AsyncConnectionPool(
    conninfo=PSYCOPG_URL,
    max_size=10,
    kwargs={"autocommit": True, "prepare_threshold": 0},
    open=False,
)
_checkpoint_saver = None

REQUIRED_SCHEMA_TABLES = (
    "code_nodes",
    "code_dependencies",
    "checkpoint_migrations",
    "checkpoints",
    "checkpoint_blobs",
    "checkpoint_writes",
)


def get_checkpointer():
    global _checkpoint_saver
    if _checkpoint_saver is None:
        _checkpoint_saver = AsyncPostgresSaver(checkpoint_pool)
    return _checkpoint_saver


async def open_checkpoint_pool() -> None:
    """Open the LangGraph checkpoint pool without running DDL."""
    await checkpoint_pool.open()


async def close_checkpoint_pool() -> None:
    """Close the LangGraph checkpoint pool."""
    await checkpoint_pool.close()


async def validate_required_schema() -> None:
    """
    Validate that externally managed database schema is already initialized.

    Runtime startup must not execute DDL because production service accounts may
    only have DML privileges. Schema creation stays in database/init.sql.
    """
    async with engine.connect() as conn:
        extension_check = await conn.execute(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
                ")"
            )
        )
        if not extension_check.scalar():
            raise RuntimeError(
                "Database extension 'vector' is missing. "
                "Please execute the database initialization script "
                "(database/init.sql) as superuser first."
            )

        for table in REQUIRED_SCHEMA_TABLES:
            table_check = await conn.execute(
                text(
                    "SELECT EXISTS ("
                    "    SELECT 1 FROM information_schema.tables "
                    "    WHERE table_schema = 'public' AND table_name = :table"
                    ")"
                ),
                {"table": table},
            )
            if not table_check.scalar():
                raise RuntimeError(
                    f"Required database table '{table}' is missing. "
                    "Please initialize your database schema first."
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
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
