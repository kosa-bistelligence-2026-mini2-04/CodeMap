from __future__ import annotations

import asyncio
import os
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RepoMapResult:
    candidate_core_modules: list[str] = field(default_factory=list)
    module_imports: dict[str, list[str]] = field(default_factory=dict)
    symbol_index: dict[str, list[str]] = field(default_factory=dict)
    parse_errors: list[str] = field(default_factory=list)


def _empty_result() -> RepoMapResult:
    return RepoMapResult()


class RepoMap:
    SKIP_DIRS = {"__pycache__", ".venv", "venv", "node_modules", ".git", "dist", "build"}
    SKIP_FILE_PREFIXES = ("test_",)
    TOP_N = 10

    async def build(self, repo_path: str) -> RepoMapResult:
        try:
            import tree_sitter  # noqa: F401
            import tree_sitter_python  # noqa: F401
        except ImportError:
            return _empty_result()

        return await asyncio.to_thread(self._build_sync, repo_path)

    def _build_sync(self, repo_path: str) -> RepoMapResult:
        py_files = self._collect_python_files(repo_path)
        module_imports: dict[str, list[str]] = {}
        symbol_index: dict[str, list[str]] = {}
        parse_errors: list[str] = []

        for f in py_files:
            try:
                tree = self._parse(f)
                module_imports[f] = self._extract_imports(tree)
                symbol_index[f] = self._extract_top_level_symbols(tree)
            except Exception as exc:
                parse_errors.append(f"{f}: {exc}")

        candidates = self._rank_by_centrality(module_imports)
        return RepoMapResult(
            candidate_core_modules=candidates[: self.TOP_N],
            module_imports=module_imports,
            symbol_index=symbol_index,
            parse_errors=parse_errors,
        )

    def _collect_python_files(self, repo_path: str) -> list[str]:
        result: list[str] = []
        for dirpath, dirnames, filenames in os.walk(repo_path):
            # Prune skip dirs in-place so os.walk doesn't descend into them
            dirnames[:] = [d for d in dirnames if d not in self.SKIP_DIRS]
            for fname in filenames:
                if not fname.endswith(".py"):
                    continue
                if any(fname.startswith(prefix) for prefix in self.SKIP_FILE_PREFIXES):
                    continue
                result.append(os.path.join(dirpath, fname))
        return result

    def _parse(self, path: str):
        parser = self._get_parser()
        source = Path(path).read_bytes()
        return parser.parse(source)

    def _get_parser(self):
        parser = getattr(self, "_parser_cache", None)
        if parser is not None:
            return parser
        import tree_sitter
        import tree_sitter_python

        py_lang = tree_sitter.Language(tree_sitter_python.language())
        parser = tree_sitter.Parser(py_lang)
        self._parser_cache = parser
        return parser

    def _extract_imports(self, tree) -> list[str]:
        imports: list[str] = []
        self._walk_imports(tree.root_node, imports)
        return imports

    def _walk_imports(self, node, imports: list[str]) -> None:
        if node.type == "import_statement":
            for child in node.children:
                if child.type in ("dotted_name", "aliased_import"):
                    name = self._dotted_name_text(child)
                    if name:
                        imports.append(name)
        elif node.type == "import_from_statement":
            module_name = self._extract_from_module(node)
            if module_name:
                imports.append(module_name)
        for child in node.children:
            self._walk_imports(child, imports)

    def _dotted_name_text(self, node) -> str:
        if node.type == "dotted_name":
            return node.text.decode("utf-8", errors="replace")
        if node.type == "aliased_import":
            for child in node.children:
                if child.type == "dotted_name":
                    return child.text.decode("utf-8", errors="replace")
        return ""

    def _extract_from_module(self, node) -> str:
        # import_from_statement: 'from' dotted_name 'import' ...
        for child in node.children:
            if child.type == "dotted_name":
                return child.text.decode("utf-8", errors="replace")
            if child.type == "relative_import":
                # relative imports like `from . import x` — extract dotted_name if present
                for subchild in child.children:
                    if subchild.type == "dotted_name":
                        return subchild.text.decode("utf-8", errors="replace")
        return ""

    def _extract_top_level_symbols(self, tree) -> list[str]:
        symbols: list[str] = []
        root = tree.root_node
        for child in root.children:
            if child.type in ("class_definition", "function_definition"):
                name_node = child.child_by_field_name("name")
                if name_node:
                    kind = "class" if child.type == "class_definition" else "def"
                    symbols.append(f"{kind} {name_node.text.decode('utf-8', errors='replace')}")
            elif child.type == "decorated_definition":
                # decorated top-level def/class
                for subchild in child.children:
                    if subchild.type in ("class_definition", "function_definition"):
                        name_node = subchild.child_by_field_name("name")
                        if name_node:
                            kind = "class" if subchild.type == "class_definition" else "def"
                            symbols.append(
                                f"{kind} {name_node.text.decode('utf-8', errors='replace')}"
                            )
        return symbols

    def _rank_by_centrality(self, module_imports: dict[str, list[str]]) -> list[str]:
        import_count: Counter[str] = Counter()
        for _file, imps in module_imports.items():
            for imp in imps:
                import_count[imp] += 1
        return [m for m, _ in import_count.most_common()]


__all__ = ["RepoMap", "RepoMapResult"]
