"""Symbol extraction for non-Python languages via tree-sitter.

Uses the modern ``tree_sitter`` (>=0.23) API with the official per-language grammar wheels
(``tree_sitter_python``, ``tree_sitter_go``, ...). Parsers are cached per language. Any
parse failure is the caller's cue to fall back to line windows, so a missing or broken
grammar never breaks indexing.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Callable, List, Set

from coderag.chunking.base import SymbolSpan

logger = logging.getLogger(__name__)


def _load(module: str, fn: str = "language") -> Callable:
    def loader():
        import importlib

        import tree_sitter as ts

        mod = importlib.import_module(module)
        return ts.Language(getattr(mod, fn)())

    return loader


# language -> callable returning a tree_sitter.Language
_LANGUAGE_LOADERS = {
    "javascript": _load("tree_sitter_javascript"),
    "typescript": _load("tree_sitter_typescript", "language_typescript"),
    "tsx": _load("tree_sitter_typescript", "language_tsx"),
    "go": _load("tree_sitter_go"),
    "rust": _load("tree_sitter_rust"),
    "java": _load("tree_sitter_java"),
}

# Node types worth indexing as their own chunk, per language.
DEF_NODE_TYPES = {
    "javascript": {
        "function_declaration",
        "generator_function_declaration",
        "method_definition",
        "class_declaration",
    },
    "typescript": {
        "function_declaration",
        "generator_function_declaration",
        "method_definition",
        "class_declaration",
        "interface_declaration",
        "type_alias_declaration",
        "enum_declaration",
    },
    "tsx": {
        "function_declaration",
        "generator_function_declaration",
        "method_definition",
        "class_declaration",
        "interface_declaration",
        "type_alias_declaration",
        "enum_declaration",
    },
    "go": {"function_declaration", "method_declaration", "type_declaration"},
    "rust": {
        "function_item",
        "impl_item",
        "struct_item",
        "enum_item",
        "trait_item",
        "mod_item",
    },
    "java": {
        "class_declaration",
        "interface_declaration",
        "enum_declaration",
        "method_declaration",
        "constructor_declaration",
    },
}

_NAME_FIELDS = ("name", "type")


@lru_cache(maxsize=16)
def _parser(language: str):
    import tree_sitter as ts

    return ts.Parser(_LANGUAGE_LOADERS[language]())


def _kind(node_type: str) -> str:
    if "class" in node_type or "struct" in node_type or "type" in node_type:
        return "class"
    if "method" in node_type or "constructor" in node_type:
        return "method"
    return "function"


def _name(node, source: bytes) -> str | None:
    for field in _NAME_FIELDS:
        child = node.child_by_field_name(field)
        if child is not None:
            return source[child.start_byte : child.end_byte].decode(
                "utf-8", errors="replace"
            )
    # Some constructs (e.g. Go `type X struct`) nest the name in a child node; do a
    # shallow breadth-first scan for the first identifier-like token.
    queue = list(node.children)
    seen = 0
    while queue and seen < 16:
        child = queue.pop(0)
        seen += 1
        if child.type.endswith("identifier"):
            return source[child.start_byte : child.end_byte].decode(
                "utf-8", errors="replace"
            )
        queue.extend(child.children)
    return None


def extract_spans(text: str, language: str) -> List[SymbolSpan]:
    if language not in _LANGUAGE_LOADERS:
        return []
    types: Set[str] = DEF_NODE_TYPES.get(language, set())
    source = text.encode("utf-8")
    tree = _parser(language).parse(source)

    spans: List[SymbolSpan] = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        if node.type in types:
            spans.append(
                SymbolSpan(
                    symbol=_name(node, source) or node.type,
                    kind=_kind(node.type),
                    start_line=node.start_point[0] + 1,
                    end_line=node.end_point[0] + 1,
                )
            )
        stack.extend(reversed(node.children))

    return spans
