"""Typed, injectable configuration for CodeRAG.

The whole app reads configuration from a single immutable :class:`Config` object that
is built once (usually via :meth:`Config.from_env`) and passed down explicitly. Nothing
deep in the call stack reaches for ``os.environ`` — that keeps the engine testable and
free of import-time side effects.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Tuple

from dotenv import load_dotenv

# Languages that ship with symbol-aware chunking in v1.0. Anything not listed (or that
# fails to parse) falls back to the line-window chunker.
DEFAULT_LANGUAGES: Tuple[str, ...] = (
    "python",
    "javascript",
    "typescript",
    "tsx",
    "go",
    "rust",
    "java",
)

# Directories/globs never worth indexing. Note we deliberately do NOT ignore ``tests`` —
# people search their tests too.
DEFAULT_IGNORE_GLOBS: Tuple[str, ...] = (
    ".git/*",
    ".hg/*",
    ".svn/*",
    "node_modules/*",
    ".venv/*",
    "venv/*",
    "env/*",
    "__pycache__/*",
    "*.egg-info/*",
    "build/*",
    "dist/*",
    ".mypy_cache/*",
    ".pytest_cache/*",
    ".coderag/*",
)


def _env_str(key: str, default: str) -> str:
    val = os.getenv(key)
    return val if val is not None and val.strip() else default


def _env_int(key: str, default: int) -> int:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_path(key: str, default: Path) -> Path:
    raw = os.getenv(key)
    if raw is None or not raw.strip():
        return default
    return Path(raw).expanduser()


@dataclass(frozen=True)
class Config:
    """Immutable configuration for an indexing/search session."""

    # --- Embedding provider ---
    provider: str = "fastembed"  # "fastembed" | "openai" | "fake"
    model: str = "BAAI/bge-small-en-v1.5"
    openai_model: str = "text-embedding-3-small"
    openai_api_key: str | None = None
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".cache" / "coderag")

    # --- Locations ---
    watched_dir: Path = field(default_factory=Path.cwd)
    store_dir: Path = field(default_factory=lambda: Path.cwd() / ".coderag")

    # --- What to index ---
    languages: Tuple[str, ...] = DEFAULT_LANGUAGES
    ignore_globs: Tuple[str, ...] = DEFAULT_IGNORE_GLOBS
    max_file_bytes: int = 1_000_000  # skip files larger than this
    max_chunk_lines: int = 200  # split oversized symbols into windows above this
    window_lines: int = 60  # fallback line-window size
    window_overlap: int = 10

    # --- Vector index ---
    index_type: str = "auto"  # "auto" | "flat" | "ivf"
    ivf_threshold: int = 50_000  # switch flat->ivf above this many vectors
    ivf_nlist: int = 0  # 0 => derived from corpus size
    ivf_nprobe: int = 16

    # --- Retrieval ---
    top_k: int = 8
    fetch_k: int = 50  # candidates pulled from each retriever before fusion
    rrf_k: int = 60
    dense_weight: float = 1.0
    lexical_weight: float = 1.0

    # --- Indexing throughput ---
    embed_batch_size: int = 64
    index_workers: int = 4

    # --- Optional LLM answer surface ---
    chat_model: str = "gpt-4o-mini"

    @property
    def db_path(self) -> Path:
        return self.store_dir / "coderag.db"

    @property
    def faiss_path(self) -> Path:
        return self.store_dir / "index.faiss"

    def with_overrides(self, **kwargs: object) -> "Config":
        """Return a copy with the given fields replaced (config stays immutable)."""
        return replace(self, **kwargs)  # type: ignore[arg-type]

    @classmethod
    def from_env(cls, **overrides: object) -> "Config":
        """Build a Config from environment / .env, applying explicit overrides last."""
        load_dotenv()
        base = cls(
            provider=_env_str("CODERAG_PROVIDER", cls.provider),
            model=_env_str("CODERAG_MODEL", cls.model),
            openai_model=_env_str("CODERAG_OPENAI_MODEL", cls.openai_model),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            cache_dir=_env_path(
                "CODERAG_CACHE_DIR", Path.home() / ".cache" / "coderag"
            ),
            watched_dir=_env_path("CODERAG_WATCHED_DIR", Path.cwd()),
            store_dir=_env_path("CODERAG_STORE_DIR", Path.cwd() / ".coderag"),
            index_type=_env_str("CODERAG_INDEX_TYPE", cls.index_type),
            ivf_threshold=_env_int("CODERAG_IVF_THRESHOLD", cls.ivf_threshold),
            top_k=_env_int("CODERAG_TOP_K", cls.top_k),
            fetch_k=_env_int("CODERAG_FETCH_K", cls.fetch_k),
            rrf_k=_env_int("CODERAG_RRF_K", cls.rrf_k),
            dense_weight=_env_float("CODERAG_DENSE_WEIGHT", cls.dense_weight),
            lexical_weight=_env_float("CODERAG_LEXICAL_WEIGHT", cls.lexical_weight),
            embed_batch_size=_env_int("CODERAG_EMBED_BATCH", cls.embed_batch_size),
            index_workers=_env_int("CODERAG_WORKERS", cls.index_workers),
            chat_model=_env_str("CODERAG_CHAT_MODEL", cls.chat_model),
        )
        if overrides:
            base = base.with_overrides(**overrides)
        return base
