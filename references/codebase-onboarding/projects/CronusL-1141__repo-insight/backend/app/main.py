from __future__ import annotations

import logging
import logging.config
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.models.config import get_settings

logger = logging.getLogger(__name__)


class _DualAuditLogger:
    """Writes each LLM call to BOTH the in-memory ObservabilityCollector
    (for Prometheus /metrics) AND the persistent SQLite audit_log table
    (for long-term evidence). Errors in either sink are logged at WARNING
    level but never raised — a broken logger must never fail an LLM
    request."""

    def __init__(self, collector, sqlite_logger):
        self._collector = collector
        self._sqlite = sqlite_logger

    async def record(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cache_hit: bool = False,
        agent_name: str | None = None,
        key: str | None = None,
        error: str | None = None,
    ):
        try:
            self._collector.record_llm_call(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cache_hit=cache_hit,
            )
        except Exception as exc:
            logger.warning(
                "audit sink [observability] failed: %s: %s",
                exc.__class__.__name__, exc,
            )
        try:
            await self._sqlite.record(
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cache_hit=cache_hit,
                agent_name=agent_name,
                key=key,
                error=error,
            )
        except Exception as exc:
            logger.warning(
                "audit sink [sqlite] failed: %s: %s",
                exc.__class__.__name__, exc,
            )


def _configure_logging() -> None:
    """Install centralized dictConfig for uvicorn + app loggers.

    LOG_LEVEL env var controls verbosity (default INFO). Called from lifespan
    BEFORE any agent / llm / orchestrator module is imported so those modules
    pick up the handlers / formatters configured here.
    """
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "access": {
                "format": "%(asctime)s [ACCESS] %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stderr",
            },
            "access": {
                "class": "logging.StreamHandler",
                "formatter": "access",
                "stream": "ext://sys.stdout",
            },
        },
        "loggers": {
            "uvicorn":        {"level": log_level, "handlers": ["default"], "propagate": False},
            "uvicorn.error":  {"level": log_level, "handlers": ["default"], "propagate": False},
            "uvicorn.access": {"level": log_level, "handlers": ["access"],  "propagate": False},
            "app":            {"level": log_level, "handlers": ["default"], "propagate": False},
        },
        "root": {
            "level": log_level,
            "handlers": ["default"],
        },
    })


@asynccontextmanager
async def lifespan(app: FastAPI):
    _configure_logging()

    settings = get_settings()

    from app.agents.behavior_inferer import BehaviorInferer
    from app.agents.community_assessor import CommunityAssessor
    from app.agents.reporter import Reporter
    from app.agents.static_analyzer import StaticAnalyzer
    from app.api.progress_bus import ProgressBus
    from app.guardrail.validator import GuardrailValidator
    from app.llm.cache import LLMCache
    from app.llm.openai_provider import OpenAIProvider
    from app.orchestrator.conflict_resolver import ConflictResolver
    from app.orchestrator.planner import Planner
    from app.orchestrator.timeout_guard import TimeoutGuard
    from app.services.analysis_store import AnalysisStore
    from app.services.observability import ObservabilityCollector
    from app.services.repo_cloner import RepoCloner

    semantic_backend = os.environ.get("SEMANTIC_VALIDATOR_BACKEND", "stub")
    os.environ.setdefault("SEMANTIC_VALIDATOR_BACKEND", semantic_backend)

    from app.llm.audit import AuditLogger

    llm_cache = LLMCache(db_path=settings.sqlite_path)
    await llm_cache._ensure_schema()

    audit_db_path = settings.sqlite_path.replace(".db", "_llm_audit.db")
    persistent_audit_logger = AuditLogger(db_path=audit_db_path)
    await persistent_audit_logger._ensure_schema()

    observability = ObservabilityCollector()

    analysis_store = AnalysisStore(
        db_path=settings.sqlite_path.replace(".db", "_analyses.db")
    )
    await analysis_store._ensure_schema()

    openai_key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
    if openai_key:
        os.environ.setdefault("OPENAI_API_KEY", openai_key)

    audit_logger = _DualAuditLogger(observability, persistent_audit_logger)
    llm_provider = OpenAIProvider(model=settings.llm_model, audit_logger=audit_logger) if openai_key else None

    guardrail = GuardrailValidator()
    conflict_resolver = ConflictResolver(llm_provider=llm_provider)
    timeout_guard = TimeoutGuard(db_path=settings.sqlite_path.replace(".db", "_community_cache.db"))

    static_analyzer = StaticAnalyzer(llm_provider=llm_provider, cache=llm_cache)
    behavior_inferer = BehaviorInferer(llm_provider=llm_provider, cache=llm_cache)
    community_assessor = CommunityAssessor(llm_provider=llm_provider, cache=llm_cache)
    reporter = Reporter(
        conflict_resolver=conflict_resolver,
        llm_provider=llm_provider,
        cache=llm_cache,
        guardrail=guardrail,
    )

    repo_cloner = RepoCloner()
    progress_bus = ProgressBus()

    planner = Planner(
        static_analyzer=static_analyzer,
        behavior_inferer=behavior_inferer,
        community_assessor=community_assessor,
        reporter=reporter,
        repo_cloner=repo_cloner,
        guardrail=guardrail,
        timeout_guard=timeout_guard,
        progress_bus=progress_bus,
        observability=observability,
    )

    app.state.planner = planner
    app.state.progress_bus = progress_bus
    app.state.observability = observability
    app.state.analysis_store = analysis_store
    app.state.default_llm_model = settings.llm_model

    yield


def create_app() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title="RepoInsight API",
        description="Multi-agent Python repository analysis system",
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000", *settings.cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(router)

    # ------------------------------------------------------------------
    # Global exception handlers
    # ------------------------------------------------------------------
    # All error responses share the ErrorResponse / ErrorDetail shape
    # defined in app.models.api_schemas:
    #     {"error": {"code": str, "message": str, "detail": Any}}
    # ------------------------------------------------------------------

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=jsonable_encoder(
                {
                    "error": {
                        "code": "validation_error",
                        "message": "Request validation failed",
                        "detail": exc.errors(),
                    }
                }
            ),
        )

    @application.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": f"http_{exc.status_code}",
                    "message": exc.detail if isinstance(exc.detail, str) else "HTTP error",
                    "detail": exc.detail if not isinstance(exc.detail, str) else None,
                }
            },
        )

    @application.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "Unhandled exception on %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Internal server error",
                    "detail": str(exc)[:500],
                }
            },
        )

    return application


app = create_app()
