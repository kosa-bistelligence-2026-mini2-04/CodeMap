"""Symbol extraction for Python using the standard library ``ast``.

Faster and more accurate than tree-sitter for Python, with zero extra dependencies.
Emits a span per function/method and per class (the class span's non-method lines — its
docstring and class-level attributes — become their own chunks via line ownership).
"""

from __future__ import annotations

import ast
from typing import List, cast

from coderag.chunking.base import SymbolSpan


def extract_spans(text: str) -> List[SymbolSpan]:
    tree = ast.parse(text)  # may raise SyntaxError -> caller falls back to windows
    spans: List[SymbolSpan] = []

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = f"{prefix}{child.name}"
                kind = "method" if prefix else "function"
                spans.append(SymbolSpan(name, kind, _start(child), _end(child)))
                # Nested functions are captured too.
                visit(child, f"{name}.")
            elif isinstance(child, ast.ClassDef):
                name = f"{prefix}{child.name}"
                spans.append(SymbolSpan(name, "class", _start(child), _end(child)))
                visit(child, f"{name}.")

    visit(tree, "")
    return spans


def _start(node: ast.AST) -> int:
    # Include decorators in the span so a decorated def reads as a unit.
    lines = [getattr(node, "lineno", 1)]
    for dec in getattr(node, "decorator_list", []) or []:
        lines.append(dec.lineno)
    return min(lines)


def _end(node: ast.AST) -> int:
    end = getattr(node, "end_lineno", None) or getattr(node, "lineno", 1)
    return cast(int, end)
