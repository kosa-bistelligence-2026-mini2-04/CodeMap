"""
CodeMap API 애플리케이션 진입점

FastAPI 앱 인스턴스를 생성하고, 도메인별 라우터와 미들웨어,
예외 핸들러를 등록하는 메인 모듈이다.
"""

import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager, suppress

from app.common.exceptions import register_exception_handlers
from app.infra.database import engine, Base
from sqlalchemy import text

# Import model classes to ensure they register on Base.metadata
from app.embed.models import CodeNode, Dependency
from app.gen.models import OnboardingDoc  # noqa: F401 — docs 테이블 Base 등록용

from app.auth.router import router as auth_router
from app.list.router import router as list_router
from app.list.websocket import ws_router as list_ws_router
from app.repo.router import router as repo_router
from app.pipeline.websocket import ws_router as repo_ws_router
from app.chat.router import router as chat_router
from app.chat.run_registry import sweep_run_registry
from app.agent.router import router as agent_router
from app.parse.router import router as parse_router, file_router as parse_file_router
from app.tool.router import router as tool_router
from app.gen.router import router as gen_router
from app.team.router import router as team_router
from app.team.router import invite_router as team_invite_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    run_registry_sweeper = asyncio.create_task(sweep_run_registry())
    # 애플리케이션 시작 시 DB vector extension 및 필수 RAG 테이블 존재 여부 검증
    try:
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
    finally:
        run_registry_sweeper.cancel()
        with suppress(asyncio.CancelledError):
            await run_registry_sweeper
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
    allow_origins=["*"],  # [보안] 운영 환경(Phase 2) 배포 시 환경변수를 통해 특정 도메인만 허용하도록 변경 필요
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

# Agent Run Management (상태조회/취소/근거 — LLM-CHAT-API-003~005)
app.include_router(agent_router)

# RAG-PARSE 분석 API (API-001 등)
app.include_router(parse_router)
app.include_router(parse_file_router)

# MCP Tools API: Phase 2 실구현 전까지 단일 JSON body를 수신하되 501/failed만 반환한다.
app.include_router(tool_router)

# DOCS-GEN API: 온보딩 가이드북 생성 및 저장 (DOCS-GEN-API-005)
app.include_router(gen_router)

# Team workspace APIs
app.include_router(team_router)
app.include_router(team_invite_router)
