# syntax=docker/dockerfile:1.7
# RepoInsight backend image — multi-stage build with uv
#
# Design notes (standard Astral-recommended pattern):
# - uv is brought in via `COPY --from=ghcr.io/astral-sh/uv` (no `pip install uv`)
#   This is the official Astral recommendation for Docker integration:
#   https://docs.astral.sh/uv/guides/integration/docker/
# - PyPI index is a build-arg (`PIP_INDEX_URL`) so mirrors can be selected
#   per-build without modifying the Dockerfile. Default = official PyPI.
#
# Override example (use Tsinghua mirror for faster builds in CN):
#   docker compose build \
#       --build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
#       backend

ARG PYTHON_VERSION=3.12.7
ARG UV_VERSION=0.5.11
ARG PIP_INDEX_URL=https://pypi.org/simple

############################
# Stage 1: builder
############################
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

# Bring in uv as a prebuilt binary from the official Astral image.
# This avoids pulling 15MB from PyPI through `pip install uv`, which is the
# single slowest and most network-dependent step on unreliable links.
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

# Propagate PyPI index URL to both uv and pip (some transitive wheels may
# still be fetched via pip's resolver).
ARG PIP_INDEX_URL
ENV UV_INDEX_URL=${PIP_INDEX_URL} \
    PIP_INDEX_URL=${PIP_INDEX_URL}

# System build dependencies: git for CommunityAssessor, build-essential for
# native C extensions (tree-sitter + tokenizers wheels that lack manylinux).
RUN apt-get update \
 && apt-get install --no-install-recommends -y \
        build-essential \
        git \
        curl \
        ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy dependency manifests first for better layer caching
COPY pyproject.toml ./
COPY uv.lock* ./

# Pre-create venv and install deps (no project source yet) so this layer
# caches cleanly when only app/ changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/root/.cache/pip \
    uv venv /opt/venv \
 && uv sync --frozen --no-install-project --no-dev || \
    uv sync --no-install-project --no-dev

# Now copy source and install the project itself
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/root/.cache/pip \
    uv sync --frozen --no-dev || uv sync --no-dev

############################
# Stage 2: runtime
############################
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV=/opt/venv \
    SEMANTIC_VALIDATOR_BACKEND=stub \
    PORT=8770 \
    HOST=0.0.0.0

# OCI image metadata — populated at build time via --build-arg
ARG APP_VERSION=0.1.0
ARG VCS_REF=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.title="repo-insight-backend"
LABEL org.opencontainers.image.description="Multi-agent Python repository analyzer — 4 agents, 3 mechanisms, OpenAI-compatible LLM layer"
LABEL org.opencontainers.image.version="${APP_VERSION}"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.authors="RepoInsight"
LABEL org.opencontainers.image.source="https://github.com/example/repo-insight"

# Runtime system deps: git for repo cloning/CommunityAssessor, curl for
# the HEALTHCHECK probe. No build tools — this is the slim runtime layer.
RUN apt-get update \
 && apt-get install --no-install-recommends -y \
        git \
        curl \
        ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 1001 app \
 && useradd  --system --uid 1001 --gid 1001 --home /home/app --create-home app

# Copy prebuilt virtualenv from builder
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copy application source
COPY --chown=app:app app ./app
COPY --chown=app:app pyproject.toml ./

# Pre-create writable data dir for SQLite + LLM cache
RUN mkdir -p /app/data /app/.cache \
 && chown -R app:app /app

USER app

EXPOSE 8770

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail --silent http://127.0.0.1:8770/api/health || exit 1

# No --reload in the runtime image: reload conflicts with long-running async pipelines
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8770", "--proxy-headers"]
