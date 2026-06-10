# RepoInsight Backend

FastAPI backend for the RepoInsight multi-agent repository analysis system.

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/) package manager

## Setup

```bash
# Install dependencies
uv sync

# Copy and configure environment variables
cp ../.env.example ../.env
# Edit .env and set OPENAI_API_KEY
```

## Start

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000  
Interactive docs: http://localhost:8000/docs

## Run Tests

```bash
uv run pytest
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/analyze | Submit a repository for analysis |
| GET | /api/report/{job_id} | Retrieve completed HTML report |
| GET | /api/health | Health check |
| WS | /ws/progress/{job_id} | Real-time analysis progress |

## Architecture

```
app/
├── main.py              # FastAPI entry point
├── agents/              # 4 analysis agents (stub)
├── orchestrator/        # Planner + conflict resolver + timeout guard
├── guardrail/           # Dual-layer hallucination filter
├── llm/                 # LLM provider abstraction
├── api/                 # Route handlers
├── models/              # Pydantic schemas
└── services/            # Repo cloning + audit DB
```
