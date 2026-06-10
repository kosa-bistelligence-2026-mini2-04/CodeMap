"""The public CodeRAG facade — the one object every surface (CLI, HTTP, UI) routes through.

Holds the wired-together engine: embedding provider, SQLite store, FAISS vector index,
indexer, and hybrid searcher. Collaborators are built lazily so constructing a ``CodeRAG``
is cheap and importing this module pulls in no heavy dependencies.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

from coderag.config import Config
from coderag.types import IndexStats, SearchHit

if TYPE_CHECKING:  # avoid import-time cost / cycles
    from coderag.embeddings import EmbeddingProvider
    from coderag.indexer import Indexer
    from coderag.retrieval.search import HybridSearcher
    from coderag.store.sqlite_store import SQLiteStore
    from coderag.store.vector_index import FaissVectorIndex

logger = logging.getLogger(__name__)


class CodeRAG:
    """High-level entry point for indexing and searching a codebase."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.config = config or Config.from_env()
        self._provider: Optional["EmbeddingProvider"] = None
        self._store: Optional["SQLiteStore"] = None
        self._vectors: Optional["FaissVectorIndex"] = None
        self._indexer: Optional["Indexer"] = None
        self._searcher: Optional["HybridSearcher"] = None

    # --- lazily constructed collaborators ---

    @property
    def provider(self) -> "EmbeddingProvider":
        if self._provider is None:
            from coderag.embeddings import get_provider

            self._provider = get_provider(self.config)
        return self._provider

    @property
    def store(self) -> "SQLiteStore":
        if self._store is None:
            from coderag.store.sqlite_store import SQLiteStore

            self.config.store_dir.mkdir(parents=True, exist_ok=True)
            self._store = SQLiteStore(self.config.db_path)
            self._store.bootstrap(self.provider.dim, self.provider.model_id)
        return self._store

    @property
    def vectors(self) -> "FaissVectorIndex":
        if self._vectors is None:
            from coderag.store.vector_index import FaissVectorIndex

            self._vectors = FaissVectorIndex.open(self.config, self.provider.dim)
            # FAISS is a rebuildable cache; reconcile with the source of truth on open.
            self._vectors.ensure_consistent(self.store)
        return self._vectors

    @property
    def indexer(self) -> "Indexer":
        if self._indexer is None:
            from coderag.indexer import Indexer

            self._indexer = Indexer(
                self.config, self.provider, self.store, self.vectors
            )
        return self._indexer

    @property
    def searcher(self) -> "HybridSearcher":
        if self._searcher is None:
            from coderag.retrieval.search import HybridSearcher

            self._searcher = HybridSearcher(
                self.config, self.provider, self.store, self.vectors
            )
        return self._searcher

    # --- public operations ---

    def index(
        self, path: Optional[Union[str, Path]] = None, *, full: bool = False
    ) -> IndexStats:
        """Incrementally index ``path`` (defaults to the configured watched dir).

        Only files whose content hash changed are re-embedded. Pass ``full=True`` to
        force a clean rebuild.
        """
        target = Path(path).expanduser() if path else self.config.watched_dir
        return self.indexer.index(target, full=full)

    def search(self, query: str, top_k: Optional[int] = None) -> List[SearchHit]:
        """Hybrid (dense + lexical) search over the indexed codebase."""
        return self.searcher.search(query, top_k or self.config.top_k)

    def get_file(
        self,
        path: Union[str, Path],
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
    ) -> str:
        """Return the contents of an indexed file, optionally a 1-based line range."""
        full = (self.config.watched_dir / Path(path)).resolve()
        root = self.config.watched_dir.resolve()
        if root not in full.parents and full != root:
            raise ValueError(f"Path escapes the indexed root: {path}")
        text = full.read_text(encoding="utf-8", errors="replace")
        if start_line is None and end_line is None:
            return text
        lines = text.splitlines()
        lo = max(0, (start_line or 1) - 1)
        hi = min(len(lines), end_line or len(lines))
        return "\n".join(lines[lo:hi])

    def delete_path(self, path: Union[str, Path]) -> int:
        """Forget a file that was removed from disk. Returns chunks removed."""
        root = self.config.watched_dir.resolve()
        try:
            rel = Path(path).resolve().relative_to(root).as_posix()
        except ValueError:
            return 0
        removed = self.store.delete_file(rel)
        if removed:
            self.vectors.remove(removed)
            self.vectors.save()
        return len(removed)

    def status(self) -> dict:
        """Index statistics and provenance."""
        stats = self.store.stats()
        return {
            "provider": self.config.provider,
            "model": self.provider.model_id,
            "embedding_dim": self.provider.dim,
            "index_type": self.vectors.kind,
            "store_dir": str(self.config.store_dir),
            "watched_dir": str(self.config.watched_dir),
            "total_files": stats.total_files,
            "total_chunks": stats.total_chunks,
            "vectors": self.vectors.ntotal,
        }

    def close(self) -> None:
        if self._store is not None:
            self._store.close()
            self._store = None
