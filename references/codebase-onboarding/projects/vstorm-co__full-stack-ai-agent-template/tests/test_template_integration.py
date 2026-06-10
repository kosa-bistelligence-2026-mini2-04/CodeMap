"""Integration tests for generated template code quality.

These tests generate actual projects and run linting/type checking on them.
They are slower but ensure the template produces valid, well-formatted code.
"""

import subprocess
from pathlib import Path

import pytest

from fastapi_gen.config import (
    AIFrameworkType,
    BackgroundTaskType,
    CIType,
    DatabaseType,
    FrontendType,
    LLMProviderType,
    LogfireFeatures,
    OAuthProvider,
    OrmType,
    ProjectConfig,
    RAGFeatures,
    VectorStoreType,
)
from fastapi_gen.generator import generate_project


@pytest.fixture
def generated_project_minimal(tmp_path: Path) -> Path:
    """Generate a minimal project for testing."""
    config = ProjectConfig(
        project_name="test_minimal",
        database=DatabaseType.SQLITE,
        enable_logfire=False,
        enable_docker=False,
        ci_type=CIType.NONE,
        background_tasks=BackgroundTaskType.NONE,
    )
    return generate_project(config, tmp_path)


@pytest.fixture
def generated_project_full(tmp_path: Path) -> Path:
    """Generate a full-featured project for testing."""
    config = ProjectConfig(
        project_name="test_full",
        project_description="A fully featured test project",
        author_name="Test Author",
        author_email="test@example.com",
        database=DatabaseType.POSTGRESQL,
        oauth_provider=OAuthProvider.GOOGLE,
        enable_session_management=True,
        enable_logfire=True,
        logfire_features=LogfireFeatures(
            fastapi=True,
            database=True,
            redis=True,
            celery=True,
            httpx=True,
        ),
        background_tasks=BackgroundTaskType.CELERY,
        enable_redis=True,
        enable_caching=True,
        enable_rate_limiting=True,
        enable_pagination=True,
        enable_sentry=True,
        enable_prometheus=True,
        enable_admin_panel=True,
        enable_websockets=True,
        enable_file_storage=True,
        enable_webhooks=True,
        enable_cors=True,
        enable_pytest=True,
        enable_precommit=True,
        enable_makefile=True,
        enable_docker=True,
        ci_type=CIType.GITHUB,
        enable_kubernetes=True,
        frontend=FrontendType.NEXTJS,
    )
    return generate_project(config, tmp_path)


class TestGeneratedTemplateRuff:
    """Test that generated code passes ruff linting."""

    @pytest.mark.slow
    def test_minimal_project_passes_ruff(self, generated_project_minimal: Path) -> None:
        """Test minimal project passes ruff check."""
        backend_path = generated_project_minimal / "backend"
        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(backend_path)],
            capture_output=True,
            text=True,
            cwd=generated_project_minimal,
        )
        assert result.returncode == 0, f"Ruff failed:\n{result.stdout}\n{result.stderr}"

    @pytest.mark.slow
    def test_full_project_passes_ruff(self, generated_project_full: Path) -> None:
        """Test full project passes ruff check."""
        backend_path = generated_project_full / "backend"
        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(backend_path)],
            capture_output=True,
            text=True,
            cwd=generated_project_full,
        )
        assert result.returncode == 0, f"Ruff failed:\n{result.stdout}\n{result.stderr}"


class TestGeneratedTemplateTy:
    """Test that generated code passes ty type checking."""

    @pytest.mark.slow
    def test_minimal_project_passes_ty(self, generated_project_minimal: Path) -> None:
        """Test minimal project passes ty check."""
        backend_path = generated_project_minimal / "backend"
        result = subprocess.run(
            ["uv", "run", "ty", "check"],
            capture_output=True,
            text=True,
            cwd=backend_path,
        )
        assert result.returncode == 0, f"ty failed:\n{result.stdout}\n{result.stderr}"

    @pytest.mark.slow
    def test_full_project_passes_ty(self, generated_project_full: Path) -> None:
        """Test full project passes ty check."""
        backend_path = generated_project_full / "backend"
        result = subprocess.run(
            ["uv", "run", "ty", "check"],
            capture_output=True,
            text=True,
            cwd=backend_path,
        )
        assert result.returncode == 0, f"ty failed:\n{result.stdout}\n{result.stderr}"


class TestGeneratedTemplateAgentsFolder:
    """Test that agents folder is always created since AI agent is always enabled."""

    @pytest.mark.slow
    def test_agents_folder_created_in_minimal(self, generated_project_minimal: Path) -> None:
        """Test that agents folder exists in minimal project (AI agent is always enabled)."""
        agents_path = generated_project_minimal / "backend" / "app" / "agents"
        assert agents_path.exists(), "agents/ folder should exist since AI agent is always enabled"

    @pytest.mark.slow
    def test_agents_folder_created_when_enabled(self, generated_project_full: Path) -> None:
        """Test that agents folder exists when AI agent is enabled."""
        agents_path = generated_project_full / "backend" / "app" / "agents"
        assert agents_path.exists(), "agents/ folder should exist when AI is enabled"
        assert (agents_path / "__init__.py").exists()
        assert (agents_path / "assistant.py").exists()


class TestGeneratedTemplateSyntax:
    """Test that generated Python files have valid syntax."""

    @pytest.mark.slow
    def test_minimal_project_valid_python_syntax(self, generated_project_minimal: Path) -> None:
        """Test all Python files in minimal project have valid syntax."""
        backend_path = generated_project_minimal / "backend"
        python_files = list(backend_path.rglob("*.py"))

        for py_file in python_files:
            result = subprocess.run(
                ["python3", "-m", "py_compile", str(py_file)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Syntax error in {py_file}:\n{result.stderr}"

    @pytest.mark.slow
    def test_full_project_valid_python_syntax(self, generated_project_full: Path) -> None:
        """Test all Python files in full project have valid syntax."""
        backend_path = generated_project_full / "backend"
        python_files = list(backend_path.rglob("*.py"))

        for py_file in python_files:
            result = subprocess.run(
                ["python3", "-m", "py_compile", str(py_file)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Syntax error in {py_file}:\n{result.stderr}"


# ---------------------------------------------------------------------------
# Configuration matrix
# ---------------------------------------------------------------------------
#
# These tests generate projects across the meaningful axes of the template
# (AI framework, database, ORM, integrations) and run ruff + ty against each.
# Without this matrix, framework-specific bugs (e.g. an undefined `file_ids`
# in the DeepAgents WebSocket handler) only surface when a user picks that
# combination. Keep the list small but representative — one entry per branch
# of significant Jinja conditionals.

MATRIX_CONFIGS: dict[str, dict] = {
    # --- AI frameworks ----------------------------------------------------
    "langchain_pg_celery": dict(
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.LANGCHAIN,
        enable_redis=True,
        background_tasks=BackgroundTaskType.CELERY,
        enable_langsmith=True,
    ),
    "langgraph_pg": dict(
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.LANGGRAPH,
        enable_redis=True,
        background_tasks=BackgroundTaskType.NONE,
    ),
    # CrewAI 1.13.x pins pydantic<2.12 + opentelemetry<1.35 which conflicts with
    # both pydantic 2.12+ and logfire 4.30+. Until CrewAI catches up, the matrix
    # test runs the framework in isolation (no logfire, pinned older pydantic).
    # See ProjectConfig validator that blocks crewai+logfire.
    # NOTE: we only run ruff/syntax checks on this config — full ty + pip resolve
    # against Python 3.14 fails because pydantic<2.12 needs older pyo3 (no 3.14
    # support yet). Track upstream: crewai/crewai#3xxx
    "crewai_pg": dict(
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.CREWAI,
        enable_redis=True,
        background_tasks=BackgroundTaskType.NONE,
        enable_logfire=False,
    ),
    "deepagents_pg": dict(
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.DEEPAGENTS,
        enable_redis=True,
        background_tasks=BackgroundTaskType.NONE,
    ),
    "deepagents_sqlite": dict(
        database=DatabaseType.SQLITE,
        ai_framework=AIFrameworkType.DEEPAGENTS,
        background_tasks=BackgroundTaskType.NONE,
    ),
    "pydantic_deep_pg": dict(
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.PYDANTIC_DEEP,
        enable_redis=True,
        background_tasks=BackgroundTaskType.NONE,
    ),
    # --- LLM providers ----------------------------------------------------
    "openrouter": dict(
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.PYDANTIC_AI,
        llm_provider=LLMProviderType.OPENROUTER,
        background_tasks=BackgroundTaskType.NONE,
    ),
    "anthropic": dict(
        database=DatabaseType.POSTGRESQL,
        ai_framework=AIFrameworkType.PYDANTIC_AI,
        llm_provider=LLMProviderType.ANTHROPIC,
        background_tasks=BackgroundTaskType.NONE,
    ),
    # --- Databases / ORM --------------------------------------------------
    "mongo": dict(
        database=DatabaseType.MONGODB,
        background_tasks=BackgroundTaskType.NONE,
    ),
    "sqlmodel_pg": dict(
        database=DatabaseType.POSTGRESQL,
        orm_type=OrmType.SQLMODEL,
        background_tasks=BackgroundTaskType.NONE,
    ),
    # --- Optional integrations -------------------------------------------
    "channels_pg": dict(
        database=DatabaseType.POSTGRESQL,
        background_tasks=BackgroundTaskType.NONE,
        use_telegram=True,
        use_slack=True,
    ),
    "rag_pgvector": dict(
        database=DatabaseType.POSTGRESQL,
        background_tasks=BackgroundTaskType.NONE,
        rag_features=RAGFeatures(
            enable_rag=True,
            vector_store=VectorStoreType.PGVECTOR,
        ),
    ),
    "rag_qdrant_mongo": dict(
        database=DatabaseType.MONGODB,
        background_tasks=BackgroundTaskType.NONE,
        rag_features=RAGFeatures(
            enable_rag=True,
            vector_store=VectorStoreType.QDRANT,
        ),
    ),
    "frontend_oauth_pg": dict(
        database=DatabaseType.POSTGRESQL,
        background_tasks=BackgroundTaskType.NONE,
        frontend=FrontendType.NEXTJS,
        oauth_provider=OAuthProvider.GOOGLE,
    ),
}


@pytest.fixture(params=sorted(MATRIX_CONFIGS), scope="module")
def matrix_project(tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest) -> Path:
    """Generate a project for a single matrix entry, shared across checks."""
    name: str = request.param
    out_dir = tmp_path_factory.mktemp(f"matrix_{name}")
    config = ProjectConfig(project_name=f"matrix_{name}", **MATRIX_CONFIGS[name])
    return generate_project(config, out_dir)


class TestGeneratedTemplateMatrix:
    """Regression matrix across AI frameworks, databases, and integrations.

    Locks in working configurations so framework-specific bugs (e.g. raw
    queries in a single agent path) cannot slip through CI.
    """

    @pytest.mark.slow
    def test_passes_ruff(self, matrix_project: Path) -> None:
        backend_path = matrix_project / "backend"
        result = subprocess.run(
            ["uv", "run", "ruff", "check", str(backend_path)],
            capture_output=True,
            text=True,
            cwd=matrix_project,
        )
        assert result.returncode == 0, f"Ruff failed:\n{result.stdout}\n{result.stderr}"

    @pytest.mark.slow
    def test_passes_ty(self, matrix_project: Path, request: pytest.FixtureRequest) -> None:
        # CrewAI's pinned pydantic<2.12 forces a build of pydantic-core from source
        # which needs an older PyO3 that doesn't support Python 3.14 yet. Skip ty
        # (which depends on `uv sync`) — ruff still runs.
        if "crewai" in request.node.callspec.id:
            pytest.skip("CrewAI dependency tree broken on Python 3.14 (pydantic-core/pyo3)")

        backend_path = matrix_project / "backend"
        result = subprocess.run(
            ["uv", "run", "ty", "check"],
            capture_output=True,
            text=True,
            cwd=backend_path,
        )
        assert result.returncode == 0, f"ty failed:\n{result.stdout}\n{result.stderr}"
