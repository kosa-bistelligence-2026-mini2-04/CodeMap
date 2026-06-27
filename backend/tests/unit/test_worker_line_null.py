"""
Unit tests for G1-C: worker 라인 신뢰도 및 null 전파 검증.

- app.chat._reference_utils: line null 전파, lineLabel, 중복 제거
- app.agent.workers.grep_worker: grep 출력 파싱, 파일별 lineStart/lineEnd
LLM·DB·파일시스템 접근 없이 결정론적으로 실행됩니다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))


# ──────────────────────────────────────────────
# _reference_utils — null 전파 및 중복 제거
# ──────────────────────────────────────────────

class TestBuildReference(unittest.TestCase):
    """build_reference: line null → lineLabel 추가, known → lineLabel 없음."""

    def _build(self, path, line_start, snippet="x"):
        from app.chat._reference_utils import build_reference
        return build_reference(path, line_start, snippet)

    def test_null_line_gets_label(self):
        ref = self._build("app/foo.py", None)
        self.assertIsNone(ref["line"])
        self.assertEqual(ref["lineLabel"], "라인 미확인")

    def test_known_line_no_label(self):
        ref = self._build("app/foo.py", 42)
        self.assertEqual(ref["line"], 42)
        self.assertNotIn("lineLabel", ref)

    def test_snippet_truncated_to_max(self):
        ref = self._build("a.py", 1, "x" * 300, )
        self.assertLessEqual(len(ref["snippet"]), 240)

    def test_snippet_custom_max(self):
        from app.chat._reference_utils import build_reference
        ref = build_reference("a.py", 1, "x" * 300, max_snippet=200)
        self.assertEqual(len(ref["snippet"]), 200)


class TestReferencesFromWorkerResults(unittest.TestCase):
    """references_from_worker_results: null 전파, 중복 제거, path 필터."""

    def _fn(self, worker_results):
        from app.chat._reference_utils import references_from_worker_results
        return references_from_worker_results(worker_results)

    def test_null_line_passes_through(self):
        results = [{"path": "app/foo.py", "lineStart": None, "snippet": "hello"}]
        refs = self._fn(results)
        self.assertEqual(len(refs), 1)
        self.assertIsNone(refs[0]["line"])
        self.assertEqual(refs[0]["lineLabel"], "라인 미확인")

    def test_known_line_has_no_label(self):
        results = [{"path": "app/foo.py", "lineStart": 42, "snippet": "def foo():"}]
        refs = self._fn(results)
        self.assertEqual(refs[0]["line"], 42)
        self.assertNotIn("lineLabel", refs[0])

    def test_no_path_skipped(self):
        results = [{"path": None, "lineStart": None, "snippet": "x"}]
        refs = self._fn(results)
        self.assertEqual(refs, [])

    def test_dedup_by_file_and_line(self):
        results = [
            {"path": "a.py", "lineStart": 10, "snippet": "first"},
            {"path": "a.py", "lineStart": 10, "snippet": "second"},
        ]
        refs = self._fn(results)
        self.assertEqual(len(refs), 1)

    def test_dedup_null_lines_same_file(self):
        """같은 파일의 null 라인 결과도 중복 제거된다."""
        results = [
            {"path": "b.py", "lineStart": None, "snippet": "x"},
            {"path": "b.py", "lineStart": None, "snippet": "y"},
        ]
        refs = self._fn(results)
        self.assertEqual(len(refs), 1)

    def test_mixed_null_and_known_lines(self):
        """null 라인과 known 라인은 별도 항목으로 유지된다."""
        results = [
            {"path": "c.py", "lineStart": None, "snippet": "x"},
            {"path": "c.py", "lineStart": 5, "snippet": "y"},
        ]
        refs = self._fn(results)
        self.assertEqual(len(refs), 2)
        lines = {r["line"] for r in refs}
        self.assertIn(None, lines)
        self.assertIn(5, lines)

    def test_line_zero_is_not_treated_as_null(self):
        """lineStart=0 은 null이 아니므로 lineLabel이 붙지 않는다."""
        results = [{"path": "d.py", "lineStart": 0, "snippet": "x"}]
        refs = self._fn(results)
        self.assertEqual(refs[0]["line"], 0)
        self.assertNotIn("lineLabel", refs[0])


# ──────────────────────────────────────────────
# _parse_grep_results — 라인 번호 추출
# ──────────────────────────────────────────────

class TestParseGrepResults(unittest.TestCase):
    """grep_worker._parse_grep_results: 출력에서 파일별 lineStart/lineEnd 추출."""

    def _fn(self, content, rel_path=".", pattern="foo"):
        from app.agent.workers.grep_worker import _parse_grep_results
        return _parse_grep_results(content, rel_path, pattern)

    def test_single_file_single_line(self):
        content = "app/main.py:10: def main():"
        results = self._fn(content)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["path"], "app/main.py")
        self.assertEqual(results[0]["lineStart"], 10)
        self.assertEqual(results[0]["lineEnd"], 10)

    def test_single_file_multiple_lines(self):
        content = "app/auth.py:5: import os\napp/auth.py:20: def login():\napp/auth.py:35: pass"
        results = self._fn(content)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["lineStart"], 5)
        self.assertEqual(results[0]["lineEnd"], 35)

    def test_multiple_files(self):
        content = "a.py:1: x\nb.py:99: y"
        results = self._fn(content)
        paths = {r["path"] for r in results}
        self.assertIn("a.py", paths)
        self.assertIn("b.py", paths)
        a = next(r for r in results if r["path"] == "a.py")
        b = next(r for r in results if r["path"] == "b.py")
        self.assertEqual(a["lineStart"], 1)
        self.assertEqual(b["lineStart"], 99)

    def test_unparseable_falls_back_to_null(self):
        """파싱 불가 출력은 lineStart/lineEnd=None 단일 결과로 폴백."""
        content = "(결과 없음)"
        results = self._fn(content)
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0]["lineStart"])
        self.assertIsNone(results[0]["lineEnd"])

    def test_empty_content_handled(self):
        """빈 문자열은 파싱 불가이므로 null 폴백."""
        results = self._fn("")
        self.assertEqual(len(results), 1)
        self.assertIsNone(results[0]["lineStart"])

    def test_line_number_ordering(self):
        """lineStart=min, lineEnd=max — 순서 무관."""
        content = "f.py:30: c\nf.py:10: a\nf.py:20: b"
        results = self._fn(content)
        self.assertEqual(results[0]["lineStart"], 10)
        self.assertEqual(results[0]["lineEnd"], 30)


if __name__ == "__main__":
    unittest.main()
