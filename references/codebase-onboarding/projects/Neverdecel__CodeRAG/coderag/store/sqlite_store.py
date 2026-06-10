"""SQLite-backed source of truth for files, chunks, vectors, and lexical search."""

from __future__ import annotations

import logging
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Sequence, Tuple

import numpy as np

from coderag.store.schema import DDL, SCHEMA_VERSION
from coderag.types import Chunk, IndexStats

logger = logging.getLogger(__name__)

# Strip FTS5 operators so a raw code query (e.g. ``foo::bar*``) can't raise a syntax error.
_FTS_TOKEN = re.compile(r"[A-Za-z0-9_]+")


def _sanitize_fts(query: str) -> str:
    """Turn an arbitrary query into a safe FTS5 MATCH expression (token OR token)."""
    tokens = _FTS_TOKEN.findall(query)
    if not tokens:
        return ""
    # Quote each token (defuses operators) and OR them for recall on identifiers.
    return " OR ".join(f'"{t}"' for t in tokens)


class SQLiteStore:
    """Thread-safe store. Reads are concurrent under WAL; writes serialize on a lock."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(self.db_path), check_same_thread=False, isolation_level=None
        )
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA synchronous=NORMAL")

    # --- lifecycle ---

    def bootstrap(self, embed_dim: int, embed_model: str) -> bool:
        """Create schema and reconcile provenance.

        Returns True if a full rebuild is required because the embedding model/dimension
        changed since the store was last written (in which case existing chunks/files are
        cleared so a reindex repopulates cleanly).
        """
        with self._lock:
            self._conn.executescript(DDL)
            self._set_meta("schema_version", str(SCHEMA_VERSION))
            prev_dim = self._get_meta("embed_dim")
            prev_model = self._get_meta("embed_model")
            rebuild = False
            if prev_dim is not None and (
                int(prev_dim) != embed_dim or prev_model != embed_model
            ):
                logger.warning(
                    "Embedding model changed (%s/%s -> %s/%s); clearing index for "
                    "rebuild.",
                    prev_model,
                    prev_dim,
                    embed_model,
                    embed_dim,
                )
                self._conn.execute("DELETE FROM chunks")
                self._conn.execute("DELETE FROM files")
                rebuild = True
            self._set_meta("embed_dim", str(embed_dim))
            self._set_meta("embed_model", embed_model)
            return rebuild

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # --- meta ---

    def _get_meta(self, key: str) -> Optional[str]:
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None

    def _set_meta(self, key: str, value: str) -> None:
        self._conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    # --- file records ---

    def get_file(self, path: str) -> Optional[sqlite3.Row]:
        return self._conn.execute(
            "SELECT * FROM files WHERE path = ?", (path,)
        ).fetchone()

    def all_file_paths(self) -> List[str]:
        rows = self._conn.execute("SELECT path FROM files").fetchall()
        return [r["path"] for r in rows]

    def upsert_file(
        self, path: str, language: str, content_hash: str, mtime: float
    ) -> int:
        with self._lock:
            now = time.time()
            self._conn.execute(
                "INSERT INTO files(path, language, content_hash, mtime, indexed_at) "
                "VALUES(?, ?, ?, ?, ?) "
                "ON CONFLICT(path) DO UPDATE SET "
                "  language=excluded.language, content_hash=excluded.content_hash, "
                "  mtime=excluded.mtime, indexed_at=excluded.indexed_at",
                (path, language, content_hash, mtime, now),
            )
            row = self._conn.execute(
                "SELECT id FROM files WHERE path = ?", (path,)
            ).fetchone()
            return int(row["id"])

    # --- chunk records ---

    def chunk_ids_for_file(self, file_id: int) -> List[int]:
        rows = self._conn.execute(
            "SELECT id FROM chunks WHERE file_id = ?", (file_id,)
        ).fetchall()
        return [int(r["id"]) for r in rows]

    def delete_file(self, path: str) -> List[int]:
        """Delete a file and its chunks. Returns the removed chunk ids (FAISS ids)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT id FROM files WHERE path = ?", (path,)
            ).fetchone()
            if row is None:
                return []
            file_id = int(row["id"])
            ids = self.chunk_ids_for_file(file_id)
            self._conn.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
            self._conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
            return ids

    def delete_chunks_for_file(self, file_id: int) -> List[int]:
        with self._lock:
            ids = self.chunk_ids_for_file(file_id)
            self._conn.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
            return ids

    def add_chunks(
        self,
        file_id: int,
        chunks: Sequence[Chunk],
        vectors: np.ndarray,
        embed_model: str,
    ) -> List[int]:
        """Insert chunks with their vectors. Returns the assigned chunk ids in order."""
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors length mismatch")
        ids: List[int] = []
        now = time.time()
        with self._lock:
            for chunk, vec in zip(chunks, vectors):
                blob = np.asarray(vec, dtype="float32").tobytes()
                cur = self._conn.execute(
                    "INSERT INTO chunks(file_id, symbol, kind, start_line, end_line, "
                    "language, text, vector, embed_model, created_at) "
                    "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        file_id,
                        chunk.symbol,
                        chunk.kind,
                        chunk.start_line,
                        chunk.end_line,
                        chunk.language,
                        chunk.text,
                        blob,
                        embed_model,
                        now,
                    ),
                )
                ids.append(int(cur.lastrowid or 0))
        return ids

    # --- retrieval support ---

    def fts_search(self, query: str, limit: int) -> List[Tuple[int, float]]:
        """Lexical search via FTS5 BM25. Returns ``(chunk_id, bm25)`` best-first."""
        match = _sanitize_fts(query)
        if not match:
            return []
        try:
            rows = self._conn.execute(
                "SELECT rowid, bm25(chunks_fts) AS score FROM chunks_fts "
                "WHERE chunks_fts MATCH ? ORDER BY score LIMIT ?",
                (match, limit),
            ).fetchall()
        except sqlite3.OperationalError as exc:  # pragma: no cover - defensive
            logger.warning("FTS query failed (%s); degrading to dense-only.", exc)
            return []
        return [(int(r["rowid"]), float(r["score"])) for r in rows]

    def hydrate(self, chunk_ids: Sequence[int]) -> Dict[int, sqlite3.Row]:
        """Fetch chunk + file rows for the given ids in one query."""
        if not chunk_ids:
            return {}
        placeholders = ",".join("?" for _ in chunk_ids)
        rows = self._conn.execute(
            "SELECT c.id, c.symbol, c.kind, c.start_line, c.end_line, c.language, "
            "       c.text, f.path AS path "
            "FROM chunks c JOIN files f ON f.id = c.file_id "
            f"WHERE c.id IN ({placeholders})",
            tuple(chunk_ids),
        ).fetchall()
        return {int(r["id"]): r for r in rows}

    def iter_vectors(
        self, batch: int = 1000
    ) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        """Yield ``(ids, vectors)`` batches for rebuilding the FAISS index."""
        cur = self._conn.execute("SELECT id, vector FROM chunks ORDER BY id")
        while True:
            rows = cur.fetchmany(batch)
            if not rows:
                break
            ids = np.array([int(r["id"]) for r in rows], dtype="int64")
            vecs = np.vstack(
                [np.frombuffer(r["vector"], dtype="float32") for r in rows]
            )
            yield ids, vecs

    # --- stats ---

    def stats(self) -> IndexStats:
        files = self._conn.execute("SELECT COUNT(*) AS n FROM files").fetchone()["n"]
        chunks = self._conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"]
        return IndexStats(total_files=int(files), total_chunks=int(chunks))

    def total_chunks(self) -> int:
        return int(
            self._conn.execute("SELECT COUNT(*) AS n FROM chunks").fetchone()["n"]
        )
