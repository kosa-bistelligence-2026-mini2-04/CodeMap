"""
CodeMap API 애플리케이션 진입점

FastAPI 앱 인스턴스를 생성하고, 도메인별 라우터와 미들웨어,
예외 핸들러를 등록하는 메인 모듈이다.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.exceptions import register_exception_handlers
from app.core.database import engine, Base
from sqlalchemy import text

# Import model classes to ensure they register on Base.metadata
from app.embed.models import CodeNode, Dependency

from app.auth.router import router as auth_router
from app.list.router import router as list_router
from app.list.websocket import ws_router as list_ws_router
from app.repo.router import router as repo_router
from app.repo.websocket import ws_router as repo_ws_router
from app.chat.router import router as chat_router
from app.parse.router import router as parse_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시 DB vector extension 및 필수 RAG 테이블 존재 여부 검증
    async with engine.connect() as conn:
        # 1. pgvector extension 존재 여부 확인
        extension_check = await conn.execute(
            text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
        )
        if not extension_check.scalar():
            raise RuntimeError(
                "Database extension 'vector' is missing. "
                "Please execute the database initialization script (database/init.sql) as superuser first."
            )

        # 2. 필수 RAG 테이블(code_nodes, code_dependencies) 존재 여부 확인
        # (생성 권한이 없는 서비스 계정에서 DDL 에러가 나는 것을 방지하고, 런타임 구동을 안전하게 차단하기 위함)
        for table in ["code_nodes", "code_dependencies"]:
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
                    f"Please initialize your database schema first."
                )
    yield
    # 애플리케이션 종료 시 커넥션 풀 닫기
    await engine.dispose()

# ──────────────────────────────────────────────
# FastAPI 앱 인스턴스 생성
# ──────────────────────────────────────────────
app = FastAPI(
    title="CodeMap API",
    description="GitHub 저장소 코드 분석 및 문서 자동 생성 서비스 API",
    version="1.0.0",
    lifespan=lifespan,
)


# ──────────────────────────────────────────────
# CORS 미들웨어 설정 (프론트엔드 개발 서버 허용)
# ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 운영 환경에서 특정 도메인만 허용하도록 수정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# 전역 예외 핸들러 등록
# ──────────────────────────────────────────────
register_exception_handlers(app)


# ──────────────────────────────────────────────
# 루트 헬스체크 엔드포인트
# ──────────────────────────────────────────────
@app.get("/")
def read_root():
    """서버 상태 확인용 헬스체크 엔드포인트"""
    return {"message": "Welcome to the CodeMap API!"}


# ──────────────────────────────────────────────
# 도메인별 라우터 등록
# ──────────────────────────────────────────────

# Auth API (로그인/회원가입/토큰 갱신/로그아웃)
app.include_router(auth_router)

# Project Repository 분석 관련 REST API (API-001, 003, 005, 007)
app.include_router(repo_router)
app.include_router(list_router)
app.include_router(list_ws_router)

# Project Repository 분석 WebSocket 엔드포인트 (API-006)
app.include_router(repo_ws_router)

# Repository-scoped grounded chat and conversation history
app.include_router(chat_router)

# RAG-PARSE 분석 API (API-001 등)
app.include_router(parse_router)

# TODO: 추후 도메인별 라우터 추가 등록
# app.include_router(list_router, prefix="/api")
