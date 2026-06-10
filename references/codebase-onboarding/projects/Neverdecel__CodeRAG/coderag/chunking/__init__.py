"""Chunking: turn a source file into symbol-aware, non-overlapping chunks.

Dispatch order:
- Python -> stdlib ``ast`` symbol spans.
- JS/TS/TSX/Go/Rust/Java -> tree-sitter symbol spans.
- anything else, or any parse failure -> line-window fallback.

A parse error never breaks indexing; it degrades gracefully to windows.
"""

from __future__ import annotations

import logging
from typing import List

from coderag.chunking import base, languages
from coderag.config import Config
from coderag.types import Chunk

logger = logging.getLogger(__name__)


def chunk_file(text: str, language: str, config: Config) -> List[Chunk]:
    if not text.strip():
        return []

    spans = []
    try:
        if language == languages.PYTHON:
            from coderag.chunking import python_ast

            spans = python_ast.extract_spans(text)
        elif language in languages.TREE_SITTER_LANGUAGES:
            from coderag.chunking import treesitter

            spans = treesitter.extract_spans(text, language)
    except Exception as exc:  # SyntaxError, tree-sitter issues, etc.
        logger.debug(
            "Symbol extraction failed for %s (%s); using windows.", language, exc
        )
        spans = []

    return base.build_chunks(text, language, spans, config)


__all__ = ["chunk_file", "languages"]
