"""Shared data types used across chunking, storage, retrieval, and the public API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class Chunk:
    """A unit of indexed code — usually a function/class/method, or a line window."""

    text: str
    start_line: int  # 1-based, inclusive
    end_line: int  # 1-based, inclusive
    language: str
    symbol: Optional[str] = None  # qualified name, e.g. "ClassName.method"
    kind: str = "window"  # "function" | "class" | "method" | "window"

    @property
    def line_count(self) -> int:
        return self.end_line - self.start_line + 1


@dataclass
class SearchHit:
    """A retrieval result, hydrated from the store."""

    chunk_id: int
    path: str
    symbol: Optional[str]
    kind: str
    language: str
    start_line: int
    end_line: int
    text: str
    score: float  # fused (RRF) score — relative ranking signal
    similarity: float  # raw cosine similarity in [0, 1] for display

    @property
    def location(self) -> str:
        return f"{self.path}:{self.start_line}"

    def as_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "path": self.path,
            "symbol": self.symbol,
            "kind": self.kind,
            "language": self.language,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "text": self.text,
            "score": self.score,
            "similarity": self.similarity,
            "location": self.location,
        }


@dataclass
class IndexStats:
    """Summary of an indexing run or the current index state."""

    files_indexed: int = 0
    files_skipped: int = 0
    files_removed: int = 0
    chunks_added: int = 0
    chunks_removed: int = 0
    total_files: int = 0
    total_chunks: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "files_indexed": self.files_indexed,
            "files_skipped": self.files_skipped,
            "files_removed": self.files_removed,
            "chunks_added": self.chunks_added,
            "chunks_removed": self.chunks_removed,
            "total_files": self.total_files,
            "total_chunks": self.total_chunks,
        }
