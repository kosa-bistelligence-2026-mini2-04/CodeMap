# AGENTS.md

This file provides guidance for AI coding agents (Codex, Copilot, Cursor, Zed, OpenCode).

## Project Overview

**{{ cookiecutter.project_name }}** - FastAPI application generated with [Full-Stack AI Agent Template](https://github.com/vstorm-co/full-stack-ai-agent-template).

**Stack:** FastAPI + Pydantic v2
{%- if cookiecutter.use_postgresql %}, PostgreSQL{%- endif %}
{%- if cookiecutter.use_mongodb %}, MongoDB{%- endif %}
{%- if cookiecutter.use_sqlite %}, SQLite{%- endif %}
, JWT + API Key auth
{%- if cookiecutter.enable_redis %}, Redis{%- endif %}
, {{ cookiecutter.ai_framework }} ({{ cookiecutter.llm_provider }})
{%- if cookiecutter.enable_rag %}, RAG ({{ cookiecutter.vector_store }}){%- endif %}
{%- if cookiecutter.use_frontend %}, Next.js 15 (i18n){%- endif %}

## Commands

```bash
# Run server
cd backend && uv run uvicorn app.main:app --reload

# Tests & lint
pytest
ruff check . --fix && ruff format .
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}

# Migrations
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "Description"
{%- endif %}
{%- if cookiecutter.enable_rag %}

# RAG
uv run {{ cookiecutter.project_slug }} rag-ingest /path/to/file.pdf --collection docs
uv run {{ cookiecutter.project_slug }} rag-search "query" --collection docs

# Sync Sources
uv run {{ cookiecutter.project_slug }} cmd rag-sources
uv run {{ cookiecutter.project_slug }} cmd rag-source-add
uv run {{ cookiecutter.project_slug }} cmd rag-source-sync
{%- endif %}
```

## Project Structure

```
backend/app/
├── api/routes/v1/    # Endpoints
├── services/         # Business logic
├── repositories/     # Data access
├── schemas/          # Pydantic models
├── db/models/        # DB models
├── agents/           # AI agents
{%- if cookiecutter.enable_rag %}
├── rag/              # RAG (embeddings, vector store, ingestion)
│   └── connectors/   # Sync source connectors
{%- endif %}
└── commands/         # CLI commands
```

## Key Conventions

- `db.flush()` in repositories, not `commit()`
- Services raise `NotFoundError`, `AlreadyExistsError`
- Separate `Create`, `Update`, `Response` schemas
- Commands auto-discovered from `app/commands/`
{%- if cookiecutter.enable_rag %}
- Document ingestion via CLI and API upload
- Sync sources: configurable connectors with scheduled sync
{%- endif %}

## More Info

- `docs/architecture.md` - Architecture details
- `docs/adding_features.md` - How to add features
- `docs/testing.md` - Testing guide
- `docs/patterns.md` - Code patterns
