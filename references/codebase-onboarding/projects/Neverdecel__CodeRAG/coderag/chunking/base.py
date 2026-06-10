"""Core chunking utilities shared by every language strategy.

The key routine is :func:`build_chunks`: given a file's text and a flat list of symbol
spans (which may be nested, e.g. methods inside a class), it produces non-overlapping
chunks by *line ownership* — each line belongs to the smallest span that contains it, and
any line owned by no span is covered by sliding line-windows. This single algorithm serves
both the Python ``ast`` extractor and the tree-sitter extractor; they only differ in how
they discover spans.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from coderag.config import Config
from coderag.types import Chunk


@dataclass
class SymbolSpan:
    """A named code region discovered by a language extractor (1-based line range)."""

    symbol: str
    kind: str  # "function" | "class" | "method"
    start_line: int
    end_line: int


def _window(
    lines: Sequence[str],
    offset: int,
    language: str,
    config: Config,
    symbol: Optional[str] = None,
    kind: str = "window",
) -> List[Chunk]:
    """Slide windows over ``lines`` (a contiguous block starting at 1-based ``offset``)."""
    chunks: List[Chunk] = []
    step = max(1, config.window_lines - config.window_overlap)
    n = len(lines)
    i = 0
    while i < n:
        block = lines[i : i + config.window_lines]
        if "".join(block).strip():  # skip whitespace-only windows
            chunks.append(
                Chunk(
                    text="\n".join(block),
                    start_line=offset + i,
                    end_line=offset + i + len(block) - 1,
                    language=language,
                    symbol=symbol,
                    kind=kind,
                )
            )
        if i + config.window_lines >= n:
            break
        i += step
    return chunks


def _emit_span(
    lines: Sequence[str], span: SymbolSpan, language: str, config: Config
) -> List[Chunk]:
    """Emit one span as a chunk, splitting it into windows if it is oversized."""
    block = lines[span.start_line - 1 : span.end_line]
    if not "".join(block).strip():
        return []
    if len(block) <= config.max_chunk_lines:
        return [
            Chunk(
                text="\n".join(block),
                start_line=span.start_line,
                end_line=span.end_line,
                language=language,
                symbol=span.symbol,
                kind=span.kind,
            )
        ]
    return _window(
        block, span.start_line, language, config, symbol=span.symbol, kind=span.kind
    )


def build_chunks(
    text: str, language: str, spans: Sequence[SymbolSpan], config: Config
) -> List[Chunk]:
    """Build non-overlapping chunks from symbol spans + windowed gaps."""
    lines = text.split("\n")
    n = len(lines)
    if n == 0 or not text.strip():
        return []

    if not spans:
        return _window(lines, 1, language, config)

    # Each line (1-based) is owned by the SMALLEST containing span. Assign larger spans
    # first so smaller (nested) spans overwrite them.
    owner: List[Optional[int]] = [None] * (n + 1)
    order = sorted(
        range(len(spans)),
        key=lambda i: spans[i].end_line - spans[i].start_line,
        reverse=True,
    )
    for idx in order:
        s = spans[idx]
        for ln in range(max(1, s.start_line), min(n, s.end_line) + 1):
            owner[ln] = idx

    chunks: List[Chunk] = []
    ln = 1
    while ln <= n:
        cur = owner[ln]
        start = ln
        while ln + 1 <= n and owner[ln + 1] == cur:
            ln += 1
        end = ln
        if cur is None:
            block = lines[start - 1 : end]
            chunks.extend(_window(block, start, language, config))
        else:
            s = spans[cur]
            chunks.extend(
                _emit_span(
                    lines,
                    SymbolSpan(s.symbol, s.kind, start, end),
                    language,
                    config,
                )
            )
        ln += 1

    chunks.sort(key=lambda c: c.start_line)
    return chunks


def window_only(text: str, language: str, config: Config) -> List[Chunk]:
    """Chunk a file with no symbol parser — pure line windows."""
    return build_chunks(text, language, [], config)
