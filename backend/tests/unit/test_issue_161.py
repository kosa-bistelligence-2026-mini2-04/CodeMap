"""
이슈 #161 회귀 테스트

1. _references_from_worker_results: lineStart=None 일 때 더 이상 1로 fallback하지 않음
2. GET /api/repo/analysis/{job_id}/files/content 헬퍼 함수 동작 검증
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


## ─────────────────────────────────────────────
## 테스트 클래스 1: _references_from_worker_results 수정 검증
## ─────────────────────────────────────────────

class TestReferencesFromWorkerResults(unittest.TestCase):
    """_references_from_worker_results의 None lineStart 처리를 검증한다."""

    def setUp(self):
        from app.chat.router import _references_from_worker_results
        self.fn = _references_from_worker_results

    def test_none_line_start_preserved_as_none(self):
        """lineStart가 None이면 ref에서도 None을 유지한다 (1로 fallback 금지)."""
        results = [{"path": "src/foo.py", "lineStart": None, "lineEnd": None, "snippet": "x"}]
        refs = self.fn(results)
        self.assertEqual(len(refs), 1)
        self.assertIsNone(refs[0]["lineStart"])
        self.assertIsNone(refs[0]["lineEnd"])

    def test_valid_line_numbers_passed_through(self):
        """lineStart/lineEnd가 정수이면 그대로 반환한다."""
        results = [{"path": "src/bar.py", "lineStart": 42, "lineEnd": 55, "snippet": "y"}]
        refs = self.fn(results)
        self.assertEqual(refs[0]["lineStart"], 42)
        self.assertEqual(refs[0]["lineEnd"], 55)

    def test_no_legacy_line_field(self):
        """예전 'line' 단일 필드가 아닌 lineStart/lineEnd 필드를 사용한다."""
        results = [{"path": "a.py", "lineStart": 10, "lineEnd": 20, "snippet": ""}]
        refs = self.fn(results)
        self.assertNotIn("line", refs[0])
        self.assertEqual(refs[0]["lineStart"], 10)

    def test_dedup_same_file_none_line(self):
        """같은 파일에 lineStart=None인 항목이 두 개면 하나만 반환한다."""
        results = [
            {"path": "dup.py", "lineStart": None, "lineEnd": None, "snippet": "a"},
            {"path": "dup.py", "lineStart": None, "lineEnd": None, "snippet": "b"},
        ]
        refs = self.fn(results)
        self.assertEqual(len(refs), 1)

    def test_snippet_truncated_to_240(self):
        """snippet은 240자로 잘린다."""
        results = [{"path": "x.py", "lineStart": None, "lineEnd": None, "snippet": "A" * 300}]
        refs = self.fn(results)
        self.assertEqual(len(refs[0]["snippet"]), 240)

    def test_missing_path_skipped(self):
        """path가 없는 항목은 결과에서 제외된다."""
        results = [
            {"path": None, "lineStart": 1, "lineEnd": 2, "snippet": ""},
            {"path": "ok.py", "lineStart": 1, "lineEnd": 2, "snippet": "ok"},
        ]
        refs = self.fn(results)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0]["file"], "ok.py")

    def test_dedup_different_lines_same_file(self):
        """같은 파일이라도 lineStart가 다르면 별개 항목으로 유지한다."""
        results = [
            {"path": "x.py", "lineStart": 1, "lineEnd": 5, "snippet": "a"},
            {"path": "x.py", "lineStart": 10, "lineEnd": 20, "snippet": "b"},
        ]
        refs = self.fn(results)
        self.assertEqual(len(refs), 2)


## ─────────────────────────────────────────────
## 테스트 클래스 2: _detect_language 헬퍼 검증
## ─────────────────────────────────────────────

class TestDetectLanguage(unittest.TestCase):
    """_detect_language 헬퍼를 검증한다."""

    def setUp(self):
        from app.repo.router import _detect_language
        self.fn = _detect_language

    def test_detect_python(self):
        self.assertEqual(self.fn("src/main.py"), "python")

    def test_detect_typescript(self):
        self.assertEqual(self.fn("src/app.ts"), "typescript")

    def test_detect_tsx(self):
        self.assertEqual(self.fn("components/Button.tsx"), "tsx")

    def test_detect_javascript(self):
        self.assertEqual(self.fn("index.js"), "javascript")

    def test_detect_unknown_returns_none(self):
        self.assertIsNone(self.fn("somefile.xyz"))

    def test_detect_dockerfile(self):
        self.assertEqual(self.fn("Dockerfile"), "dockerfile")

    def test_case_insensitive_extension(self):
        self.assertEqual(self.fn("README.MD"), "markdown")


## ─────────────────────────────────────────────
## 테스트 클래스 3: _read_file_safe 헬퍼 검증
## ─────────────────────────────────────────────

class TestReadFileSafe(unittest.TestCase):
    """_read_file_safe 헬퍼를 검증한다."""

    def setUp(self):
        from app.repo.router import _read_file_safe
        from app.common.exceptions import FilePathForbiddenError
        self.fn = _read_file_safe
        self.ForbiddenError = FilePathForbiddenError

    def test_read_utf8_file(self):
        """UTF-8 파일을 정상적으로 읽는다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            (root / "a.txt").write_text("hello\nworld\n", encoding="utf-8")
            content, truncated = self.fn(root, "a.txt")
            self.assertEqual(content, "hello\nworld\n")
            self.assertFalse(truncated)

    def test_traversal_raises(self):
        """'../' 경로는 FilePathForbiddenError를 발생시킨다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            outer = Path(tmp) / "secret.txt"
            outer.write_text("secret", encoding="utf-8")
            with self.assertRaises(self.ForbiddenError):
                self.fn(root, "../secret.txt")

    def test_large_file_truncated(self):
        """50,000자 초과 파일은 잘려서 truncated=True를 반환한다."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            (root / "big.txt").write_text("x" * 60_000, encoding="utf-8")
            content, truncated = self.fn(root, "big.txt")
            self.assertTrue(truncated)
            self.assertEqual(len(content), 50_000)


## ─────────────────────────────────────────────
## 테스트 클래스 4: get_file_content 엔드포인트 검증
## ─────────────────────────────────────────────

class TestGetFileContentEndpoint(unittest.IsolatedAsyncioTestCase):
    """get_file_content 엔드포인트를 검증한다."""

    async def _call(self, tmp_dir: str, rel_path: str, job_id: str = "00000000-0000-0000-0000-000000000001"):
        from app.repo.router import get_file_content
        from app.infra.config import get_settings as real_get_settings
        from unittest.mock import AsyncMock, patch
        from uuid import UUID

        class _FakeSettings:
            CLONE_BASE_DIR = tmp_dir
            OPENAI_API_KEY = None
            OPENAI_MODEL = "gpt-4o-mini"

        mock_service = AsyncMock()
        mock_job_resp = AsyncMock()
        mock_job_resp.data.jobId = job_id
        mock_service.get_job_status = AsyncMock(return_value=mock_job_resp)

        with patch("app.repo.router.get_settings", return_value=_FakeSettings()), \
             patch("app.repo.router.AnalysisService", return_value=mock_service):
            return await get_file_content(
                job_id=UUID(job_id),
                path=rel_path,
                db=None,
            )

    async def test_returns_file_content(self):
        """정상 텍스트 파일이면 내용을 반환한다."""
        job_id = "00000000-0000-0000-0000-000000000001"
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / job_id / "repo"
            repo_dir.mkdir(parents=True)
            (repo_dir / "hello.py").write_text("print('hello')\n", encoding="utf-8")

            result = await self._call(tmp, "hello.py", job_id)
            self.assertIn("print", result.data.content)
            self.assertEqual(result.data.path, "hello.py")
            self.assertFalse(result.data.truncated)

    async def test_language_detection_python(self):
        """파이썬 파일은 language=python으로 감지한다."""
        job_id = "00000000-0000-0000-0000-000000000002"
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / job_id / "repo"
            repo_dir.mkdir(parents=True)
            (repo_dir / "main.py").write_text("x = 1\n", encoding="utf-8")

            result = await self._call(tmp, "main.py", job_id)
            self.assertEqual(result.data.language, "python")

    async def test_workspace_not_ready(self):
        """clone 디렉토리가 없으면 WorkspaceNotReadyError가 발생한다."""
        from app.common.exceptions import WorkspaceNotReadyError
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(WorkspaceNotReadyError):
                await self._call(tmp, "foo.py")

    async def test_path_traversal_blocked(self):
        """'..' 세그먼트가 포함된 경로는 FilePathForbiddenError를 발생시킨다."""
        from app.common.exceptions import FilePathForbiddenError
        job_id = "00000000-0000-0000-0000-000000000003"
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / job_id / "repo"
            repo_dir.mkdir(parents=True)
            with self.assertRaises(FilePathForbiddenError):
                await self._call(tmp, "../../../etc/passwd", job_id)

    async def test_binary_file_blocked(self):
        """바이너리 확장자(.png)는 BinaryFileError를 발생시킨다."""
        from app.common.exceptions import BinaryFileError
        job_id = "00000000-0000-0000-0000-000000000004"
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / job_id / "repo"
            repo_dir.mkdir(parents=True)
            (repo_dir / "img.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            with self.assertRaises(BinaryFileError):
                await self._call(tmp, "img.png", job_id)

    async def test_file_not_found(self):
        """존재하지 않는 파일은 WorkspaceNotReadyError를 발생시킨다."""
        from app.common.exceptions import WorkspaceNotReadyError
        job_id = "00000000-0000-0000-0000-000000000005"
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / job_id / "repo"
            repo_dir.mkdir(parents=True)
            with self.assertRaises(WorkspaceNotReadyError):
                await self._call(tmp, "ghost.ts", job_id)

    async def test_truncation_at_50000_chars(self):
        """50,000자 초과 파일은 잘려서 truncated=True로 반환한다."""
        job_id = "00000000-0000-0000-0000-000000000006"
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / job_id / "repo"
            repo_dir.mkdir(parents=True)
            (repo_dir / "big.txt").write_text("x" * 60_000, encoding="utf-8")
            result = await self._call(tmp, "big.txt", job_id)
            self.assertTrue(result.data.truncated)
            self.assertEqual(len(result.data.content), 50_000)

    async def test_leading_slash_stripped(self):
        """/로 시작하는 경로는 정규화 후 정상 처리한다."""
        job_id = "00000000-0000-0000-0000-000000000007"
        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = Path(tmp) / job_id / "repo"
            repo_dir.mkdir(parents=True)
            (repo_dir / "ok.ts").write_text("const x = 1;\n", encoding="utf-8")
            result = await self._call(tmp, "/ok.ts", job_id)
            self.assertEqual(result.data.path, "ok.ts")


if __name__ == "__main__":
    unittest.main()
