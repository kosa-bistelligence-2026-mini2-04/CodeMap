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
from app.infra.database import (
    close_checkpoint_pool,
    engine,
    open_checkpoint_pool,
    validate_required_schema,
)

# Import model classes to ensure they register on Base.metadata
from app.embed.models import CodeNode, Dependency
from app.gen.models import OnboardingDoc  # noqa: F401 — docs 테이블 Base 등록용
from app.infra.redis import init_redis, close_redis

from app.auth.router import router as auth_router
from app.list.router import router as list_router
from app.list.websocket import ws_router as list_ws_router
from app.repo.router import router as repo_router
from app.pipeline.websocket import ws_router as repo_ws_router
from app.chat.router import router as chat_router
from app.chat.run_registry import sweep_run_registry
from app.agent.router import router as agent_router
from app.parse.router import router as parse_router
from app.tool.router import router as tool_router
from app.gen.router import router as gen_router
from app.team.router import router as team_router
from app.team.router import invite_router as team_invite_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()
    await open_checkpoint_pool()

    run_registry_sweeper = asyncio.create_task(sweep_run_registry())
    # 애플리케이션 시작 시 DB extension 및 필수 테이블 존재 여부만 검증
    # DDL 실행은 database/init.sql의 명시적 초기화 단계에서만 수행한다.
    try:
        await validate_required_schema()
        yield
    finally:
        run_registry_sweeper.cancel()
        with suppress(asyncio.CancelledError):
            await run_registry_sweeper
        # 애플리케이션 종료 시 커넥션 풀 닫기
        await engine.dispose()
        await close_checkpoint_pool()
        await close_redis()

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

# MCP Tools API: Phase 2 실구현 전까지 단일 JSON body를 수신하되 501/failed만 반환한다.
app.include_router(tool_router)

# DOCS-GEN API: 온보딩 가이드북 생성 및 저장 (DOCS-GEN-API-005)
app.include_router(gen_router)

# Team workspace APIs
app.include_router(team_router)
app.include_router(team_invite_router)
