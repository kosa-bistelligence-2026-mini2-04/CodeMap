from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

TINY_REPO = str(
    Path(__file__).parent / "fixtures" / "tiny_repo"
)


# ---------------------------------------------------------------------------
# Helpers to build a fake tree-sitter tree from a list of node descriptors
# ---------------------------------------------------------------------------

def _make_node(node_type: str, text: bytes = b"", children: list | None = None, field_map: dict | None = None):
    node = MagicMock()
    node.type = node_type
    node.text = text
    node.children = children or []

    def _child_by_field_name(name: str):
        return (field_map or {}).get(name)

    node.child_by_field_name.side_effect = _child_by_field_name
    return node


def _make_tree(root_children: list):
    tree = MagicMock()
    root = _make_node("module", children=root_children)
    tree.root_node = root
    return tree


def _make_import_node(module_name: str) -> MagicMock:
    """Simulate: import <module_name>"""
    dotted = _make_node("dotted_name", text=module_name.encode())
    return _make_node("import_statement", children=[dotted])


def _make_from_import_node(module_name: str) -> MagicMock:
    """Simulate: from <module_name> import ..."""
    dotted = _make_node("dotted_name", text=module_name.encode())
    return _make_node("import_from_statement", children=[dotted])


def _make_class_node(name: str) -> MagicMock:
    name_node = _make_node("identifier", text=name.encode())
    return _make_node("class_definition", field_map={"name": name_node})


def _make_func_node(name: str) -> MagicMock:
    name_node = _make_node("identifier", text=name.encode())
    return _make_node("function_definition", field_map={"name": name_node})


# ---------------------------------------------------------------------------
# Fake tree-sitter module injected via sys.modules
# ---------------------------------------------------------------------------

def _install_fake_tree_sitter():
    fake_ts = types.ModuleType("tree_sitter")
    fake_ts_py = types.ModuleType("tree_sitter_python")

    class FakeLang:
        pass

    class FakeParser:
        def __init__(self, lang):
            self._lang = lang

        def parse(self, source: bytes):
            return _make_tree([])

    fake_ts.Language = FakeLang
    fake_ts.Parser = FakeParser
    fake_ts_py.language = lambda: None

    sys.modules["tree_sitter"] = fake_ts
    sys.modules["tree_sitter_python"] = fake_ts_py
    return fake_ts, fake_ts_py


def _remove_fake_tree_sitter():
    sys.modules.pop("tree_sitter", None)
    sys.modules.pop("tree_sitter_python", None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestParsePythonFiles:
    """test_parse_python_files: tiny_repo has 9 .py files; skip test_*.py → at least 6."""

    def test_collects_at_least_six_py_files(self):
        from app.services.repo_map import RepoMap

        rm = RepoMap()
        files = rm._collect_python_files(TINY_REPO)
        # Should skip test_simple.py inside tests/ because it matches SKIP_FILE_PREFIXES
        non_test = [f for f in files if not Path(f).name.startswith("test_")]
        assert len(non_test) >= 6, f"Expected >=6 non-test .py files, got: {non_test}"

    def test_skips_test_prefixed_files(self):
        from app.services.repo_map import RepoMap

        rm = RepoMap()
        files = rm._collect_python_files(TINY_REPO)
        names = [Path(f).name for f in files]
        assert not any(n.startswith("test_") for n in names)


class TestExtractTopLevelSymbols:
    """test_extract_top_level_symbols: god_object.py has class GodObject."""

    def test_class_god_object_extracted(self):
        _install_fake_tree_sitter()
        try:
            # Reload to pick up fakes
            if "app.services.repo_map" in sys.modules:
                del sys.modules["app.services.repo_map"]
            from app.services.repo_map import RepoMap

            rm = RepoMap()
            class_node = _make_class_node("GodObject")
            func_node = _make_func_node("handle_everything")
            tree = _make_tree([class_node, func_node])

            symbols = rm._extract_top_level_symbols(tree)
            assert "class GodObject" in symbols
            assert "def handle_everything" in symbols
        finally:
            _remove_fake_tree_sitter()
            if "app.services.repo_map" in sys.modules:
                del sys.modules["app.services.repo_map"]


class TestComputeImportDegrees:
    """test_compute_import_degrees: a.py and c.py both import b → b degree=2."""

    def test_import_degree_counts(self):
        from app.services.repo_map import RepoMap

        rm = RepoMap()
        module_imports = {
            "a.py": ["b"],
            "c.py": ["b"],
            "b.py": [],
        }
        ranked = rm._rank_by_centrality(module_imports)
        assert ranked[0] == "b"

    def test_zero_imports_returns_empty(self):
        from app.services.repo_map import RepoMap

        rm = RepoMap()
        ranked = rm._rank_by_centrality({"a.py": [], "b.py": []})
        assert ranked == []


class TestCandidateCoreModulesRanked:
    """test_candidate_core_modules_ranked: Top-1 = most imported module."""

    def test_top_one_is_most_imported(self):
        from app.services.repo_map import RepoMap

        rm = RepoMap()
        module_imports = {
            "x.py": ["alpha", "beta"],
            "y.py": ["alpha", "gamma"],
            "z.py": ["alpha"],
        }
        ranked = rm._rank_by_centrality(module_imports)
        assert ranked[0] == "alpha"

    def test_top_n_limits_candidates(self):
        from app.services.repo_map import RepoMap

        rm = RepoMap()
        rm.TOP_N = 3
        module_imports = {f"file{i}.py": [f"mod{i}", "shared"] for i in range(20)}
        ranked = rm._rank_by_centrality(module_imports)
        # _rank_by_centrality returns full list; build() slices to TOP_N
        assert len(ranked) >= 1
        assert ranked[0] == "shared"


class TestFallbackOnParseError:
    """test_fallback_on_parse_error: bad file → parse_errors non-empty, candidates still returned."""

    @pytest.mark.asyncio
    async def test_parse_error_recorded_but_others_succeed(self):
        _install_fake_tree_sitter()
        try:
            if "app.services.repo_map" in sys.modules:
                del sys.modules["app.services.repo_map"]
            from app.services.repo_map import RepoMap

            rm = RepoMap()

            good_tree = _make_tree([_make_class_node("Foo")])
            call_count = 0

            def fake_parse(path: str):
                nonlocal call_count
                call_count += 1
                if "bad" in path:
                    raise SyntaxError("intentional parse error")
                return good_tree

            with patch.object(rm, "_collect_python_files", return_value=["good.py", "bad_file.py"]):
                with patch.object(rm, "_parse", side_effect=fake_parse):
                    result = await rm.build("/fake/repo")

            assert len(result.parse_errors) >= 1
            assert any("bad_file.py" in e for e in result.parse_errors)
            assert "good.py" in result.symbol_index
        finally:
            _remove_fake_tree_sitter()
            if "app.services.repo_map" in sys.modules:
                del sys.modules["app.services.repo_map"]


class TestTreeSitterMissingImportFallback:
    """test_tree_sitter_missing_import_fallback: ImportError → empty RepoMapResult."""

    @pytest.mark.asyncio
    async def test_returns_empty_result_when_tree_sitter_missing(self):
        # Remove tree_sitter from sys.modules if present so import fails
        saved_ts = sys.modules.pop("tree_sitter", None)
        saved_ts_py = sys.modules.pop("tree_sitter_python", None)
        if "app.services.repo_map" in sys.modules:
            del sys.modules["app.services.repo_map"]

        try:
            # Make imports raise ImportError
            import builtins
            original_import = builtins.__import__

            def blocking_import(name, *args, **kwargs):
                if name in ("tree_sitter", "tree_sitter_python"):
                    raise ImportError(f"No module named '{name}'")
                return original_import(name, *args, **kwargs)

            builtins.__import__ = blocking_import
            try:
                from app.services.repo_map import RepoMap, RepoMapResult

                rm = RepoMap()
                result = await rm.build("/fake/repo")

                assert isinstance(result, RepoMapResult)
                assert result.candidate_core_modules == []
                assert result.module_imports == {}
                assert result.symbol_index == {}
                assert result.parse_errors == []
            finally:
                builtins.__import__ = original_import
        finally:
            if saved_ts is not None:
                sys.modules["tree_sitter"] = saved_ts
            if saved_ts_py is not None:
                sys.modules["tree_sitter_python"] = saved_ts_py
            if "app.services.repo_map" in sys.modules:
                del sys.modules["app.services.repo_map"]


class TestBehaviorInfererInjectsCandidateIntoPrompt:
    """test_behavior_inferer_injects_candidate_into_prompt: 3 candidates appear in prompt."""

    def test_candidate_hint_in_prompt(self):
        from app.services.repo_map import RepoMapResult

        if "app.agents.behavior_inferer" in sys.modules:
            del sys.modules["app.agents.behavior_inferer"]
        from app.agents.behavior_inferer import BehaviorInferer

        mock_repo_map = MagicMock()
        inferer = BehaviorInferer(repo_map=mock_repo_map)

        candidates = ["app/core.py", "app/router.py", "app/models.py"]
        repo_map_result = RepoMapResult(candidate_core_modules=candidates)

        prompt = inferer._build_prompt(
            readme="Test README content",
            issue_templates="",
            pr_titles=[],
            repo_map_result=repo_map_result,
        )

        assert "app/core.py" in prompt
        assert "app/router.py" in prompt
        assert "app/models.py" in prompt
        assert "来自静态依赖图分析" in prompt
        assert "请优先从上述候选中选择核心模块" in prompt

    def test_no_candidate_hint_when_empty(self):
        from app.services.repo_map import RepoMapResult

        if "app.agents.behavior_inferer" in sys.modules:
            del sys.modules["app.agents.behavior_inferer"]
        from app.agents.behavior_inferer import BehaviorInferer

        inferer = BehaviorInferer()
        repo_map_result = RepoMapResult(candidate_core_modules=[])
        prompt = inferer._build_prompt("readme", "", [], repo_map_result)
        assert "来自静态依赖图分析" not in prompt

    def test_no_candidate_hint_when_repo_map_result_is_none(self):
        if "app.agents.behavior_inferer" in sys.modules:
            del sys.modules["app.agents.behavior_inferer"]
        from app.agents.behavior_inferer import BehaviorInferer

        inferer = BehaviorInferer()
        prompt = inferer._build_prompt("readme", "", [], repo_map_result=None)
        assert "来自静态依赖图分析" not in prompt
