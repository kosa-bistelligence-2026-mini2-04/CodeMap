"""Incremental indexing orchestration.

Ties chunking -> embedding -> SQLite -> FAISS together with content-hash change detection.
The critical correctness property (which the old ``monitor.py`` got wrong): a changed file's
*old* chunks are removed from both the store and the vector index **before** the new ones are
added, so re-saving a file never accumulates duplicate or stale vectors.
"""

from __future__ import annotations

import fnmatch
import hashlib
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional, Tuple

import numpy as np

from coderag.chunking import chunk_file
from coderag.chunking.languages import detect_language
from coderag.config import Config
from coderag.embeddings import EmbeddingProvider
from coderag.store.sqlite_store import SQLiteStore
from coderag.store.vector_index import FaissVectorIndex
from coderag.types import IndexStats

logger = logging.getLogger(__name__)


@dataclass
class _Work:
    rel: str
    language: str
    text: str
    content_hash: str
    mtime: float


class Indexer:
    def __init__(
        self,
        config: Config,
        provider: EmbeddingProvider,
        store: SQLiteStore,
        vectors: FaissVectorIndex,
    ) -> None:
        self.config = config
        self.provider = provider
        self.store = store
        self.vectors = vectors
        self._ignore_dirs = {
            g[:-2]
            for g in config.ignore_globs
            if g.endswith("/*") and "/" not in g[:-2]
        }

    # --- public ---

    def index(
        self,
        target: Optional[Path] = None,
        *,
        full: bool = False,
        progress: bool = False,
    ) -> IndexStats:
        root = self.config.watched_dir.resolve()
        target = (target or self.config.watched_dir).resolve()
        prune = target == root  # only a full-root pass removes vanished files

        stats = IndexStats()
        if full:
            self._reset()

        # 1. Discover candidates and detect what actually changed (cheap hash check).
        walked: set[str] = set()
        work: List[_Work] = []
        for abs_path, rel, language in self._walk(target, root):
            walked.add(rel)
            item = self._maybe_work(abs_path, rel, language)
            if item is None:
                stats.files_skipped += 1
            else:
                work.append(item)

        # 2. (Re)index changed files: remove old chunks, embed, add new ones.
        iterator: Iterator[_Work] = iter(work)
        if progress and work:
            try:
                from tqdm import tqdm

                iterator = tqdm(work, desc="Indexing", unit="file")
            except Exception:  # pragma: no cover
                pass
        for item in iterator:
            added, removed = self._index_file(item)
            stats.chunks_added += added
            stats.chunks_removed += removed
            stats.files_indexed += 1

        # 3. Prune files that disappeared from disk (full-root passes only).
        if prune:
            for rel in set(self.store.all_file_paths()) - walked:
                removed_ids = self.store.delete_file(rel)
                self.vectors.remove(removed_ids)
                stats.files_removed += 1
                stats.chunks_removed += len(removed_ids)

        # 4. Persist FAISS (rebuilding to IVF if we crossed the scale threshold).
        if not self.vectors.maybe_upgrade(self.store):
            self.vectors.save()

        final = self.store.stats()
        stats.total_files = final.total_files
        stats.total_chunks = final.total_chunks
        return stats

    # --- internals ---

    def _reset(self) -> None:
        for rel in list(self.store.all_file_paths()):
            self.store.delete_file(rel)
        self.vectors.rebuild_from_store(self.store)  # -> empty

    def _maybe_work(self, abs_path: Path, rel: str, language: str) -> Optional[_Work]:
        try:
            data = abs_path.read_bytes()
        except OSError as exc:
            logger.warning("Cannot read %s: %s", abs_path, exc)
            return None
        if len(data) > self.config.max_file_bytes or not data.strip():
            return None
        content_hash = hashlib.sha256(data).hexdigest()
        existing = self.store.get_file(rel)
        if existing is not None and existing["content_hash"] == content_hash:
            return None  # unchanged -> no embedding cost
        text = data.decode("utf-8", errors="replace")
        return _Work(rel, language, text, content_hash, abs_path.stat().st_mtime)

    def _index_file(self, item: _Work) -> Tuple[int, int]:
        removed = 0
        existing = self.store.get_file(item.rel)
        if existing is not None:
            old_ids = self.store.delete_chunks_for_file(int(existing["id"]))
            self.vectors.remove(old_ids)
            removed = len(old_ids)

        file_id = self.store.upsert_file(
            item.rel, item.language, item.content_hash, item.mtime
        )

        chunks = chunk_file(item.text, item.language, self.config)
        if not chunks:
            return 0, removed

        vectors = self.provider.embed_documents([c.text for c in chunks])
        new_ids = self.store.add_chunks(
            file_id, chunks, vectors, self.provider.model_id
        )
        self.vectors.add(np.array(new_ids, dtype="int64"), vectors)
        return len(new_ids), removed

    def _walk(self, target: Path, root: Path) -> Iterator[Tuple[Path, str, str]]:
        if target.is_file():
            rel = self._rel(target, root)
            language = detect_language(target)
            if rel and language and not self._ignored(rel):
                yield target, rel, language
            return

        for dirpath, dirnames, filenames in os.walk(target):
            # prune ignored directories in place for speed
            dirnames[:] = [d for d in dirnames if d not in self._ignore_dirs]
            for name in filenames:
                abs_path = Path(dirpath) / name
                rel = self._rel(abs_path, root)
                if not rel or self._ignored(rel):
                    continue
                language = detect_language(name)
                if language:
                    yield abs_path, rel, language

    @staticmethod
    def _rel(abs_path: Path, root: Path) -> Optional[str]:
        try:
            return abs_path.resolve().relative_to(root).as_posix()
        except ValueError:
            return None

    def _ignored(self, rel: str) -> bool:
        parts = rel.split("/")
        if self._ignore_dirs.intersection(parts):
            return True
        return any(fnmatch.fnmatch(rel, g) for g in self.config.ignore_globs)
