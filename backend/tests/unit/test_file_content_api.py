"""
GET /api/repo/analysis/{job_id}/files/content 엔드포인트 단위 테스트

검증 항목:
  1. job_id 미존재 → 404 JOB_NOT_FOUND
  2. clone workspace 미준비 → 404 WORKSPACE_NOT_READY
  3. path traversal (..) 차단 → 403 FILE_PATH_FORBIDDEN
  4. 절대 경로 + resolve() 우회 시도 차단 → 403 FILE_PATH_FORBIDDEN
  5. 바이너리 확장자 차단 → 422 BINARY_FILE
  6. workspace 내 파일 미존재 → 404 WORKSPACE_NOT_READY
  7. 정상 파일 읽기 → 200, content/language/lines 반환
  8. 50,000자 초과 파일 → 200, truncated=True 반환
  9. 언어 감지: 확장자별 language 필드 정확성
 10. UTF-8 이외 인코딩 fallback (latin-1) → 200, 정상 반환
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

## 백엔드 app 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

_JOB_ID = UUID("00000000-0000-0000-0000-000000000001")
_JOB_ID_STR = str(_JOB_ID)


def _make_app(clone_base_dir: str) -> FastAPI:
    """테스트용 최소 FastAPI 앱 생성."""
    from app.common.exceptions import register_exception_handlers
    from app.infra.database import get_db
    from app.repo.router import router

    app = FastAPI()
    register_exception_handlers(app)

    async def _fake_db():
        yield MagicMock()

    app.dependency_overrides[get_db] = _fake_db
    app.include_router(router)

    ## get_settings를 전역으로 패치해서 CLONE_BASE_DIR 고정
    patcher = patch("app.repo.router.get_settings")
    mock_settings = patcher.start()
    mock_settings.return_value.CLONE_BASE_DIR = clone_base_dir

    return app, patcher


def _mock_job_status_ok(target: str = "app.repo.router.AnalysisService") -> MagicMock:
    """get_job_status 가 정상 응답을 반환하도록 mock."""
    mock_svc = MagicMock()
    mock_svc.get_job_status = AsyncMock(return_value=MagicMock())
    mock_svc.restore_workspace = AsyncMock()
    patcher = patch(target, return_value=mock_svc)
    return patcher


def _mock_job_not_found(target: str = "app.repo.router.AnalysisService") -> MagicMock:
    """get_job_status 가 JobNotFoundError를 raise하도록 mock."""
    from app.common.exceptions import JobNotFoundError

    mock_svc = MagicMock()
    mock_svc.get_job_status = AsyncMock(side_effect=JobNotFoundError())
    patcher = patch(target, return_value=mock_svc)
    return patcher


class TestFileContentJobNotFound(unittest.TestCase):
    """job_id가 존재하지 않을 때 404를 반환한다."""

    def test_returns_404_job_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_not_found():
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "src/main.py"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 404)
        body = resp.json()
        self.assertEqual(body["error"]["code"], "JOB_NOT_FOUND")


class TestFileContentWorkspaceNotReady(unittest.TestCase):
    """clone workspace 디렉토리가 없으면 404를 반환한다."""

    def test_returns_404_workspace_not_ready(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok():
                ## workspace 디렉토리를 생성하지 않은 상태
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "src/main.py"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 404)
        body = resp.json()
        self.assertEqual(body["error"]["code"], "WORKSPACE_NOT_READY")


class TestFileContentPathTraversal(unittest.TestCase):
    """path traversal 시도는 403으로 차단된다."""

    def _setup(self, tmpdir: str):
        workspace = Path(tmpdir) / _JOB_ID_STR / "repo"
        workspace.mkdir(parents=True)
        return workspace

    def _run(self, tmpdir: str, path: str) -> int:
        app, settings_patcher = _make_app(tmpdir)
        client = TestClient(app, raise_server_exceptions=False)

        with _mock_job_status_ok():
            resp = client.get(
                f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                params={"path": path},
            )

        settings_patcher.stop()
        return resp

    def test_double_dot_segment_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._setup(tmpdir)
            resp = self._run(tmpdir, "../../../etc/passwd")

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["error"]["code"], "FILE_PATH_FORBIDDEN")

    def test_encoded_traversal_segment_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            self._setup(tmpdir)
            ## URL 디코딩 후 ".." 포함
            resp = self._run(tmpdir, "src/..%2F..%2Fetc%2Fpasswd")

        ## 403 이거나 404 모두 허용 — workspace 외부 파일에 접근 불가해야 한다
        self.assertIn(resp.status_code, (403, 404))


class TestFileContentBinaryBlocked(unittest.TestCase):
    """바이너리 확장자 파일은 422를 반환한다."""

    def test_png_returns_422_binary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / _JOB_ID_STR / "repo"
            workspace.mkdir(parents=True)
            ## 실제 파일 존재 여부 무관하게 확장자만으로 차단
            (workspace / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n")

            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok():
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "logo.png"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["error"]["code"], "BINARY_FILE")

    def test_zip_returns_422_binary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / _JOB_ID_STR / "repo"
            workspace.mkdir(parents=True)
            (workspace / "archive.zip").write_bytes(b"PK\x03\x04")

            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok():
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "archive.zip"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["error"]["code"], "BINARY_FILE")


class TestFileContentFileNotFound(unittest.TestCase):
    """workspace 내에 파일이 없으면 404를 반환한다."""

    def test_missing_file_returns_404(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / _JOB_ID_STR / "repo"
            workspace.mkdir(parents=True)
            ## 파일 미생성

            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok():
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "nonexistent.py"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "WORKSPACE_NOT_READY")


class TestFileContentSuccess(unittest.TestCase):
    """정상 파일 읽기는 200과 content/language/lines를 반환한다."""

    def test_python_file_returns_200_with_language(self):
        source = "def hello():\n    return 'world'\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / _JOB_ID_STR / "repo" / "src"
            workspace.mkdir(parents=True)
            (workspace / "main.py").write_text(source, encoding="utf-8")

            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok():
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "src/main.py"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(data["path"], "src/main.py")
        self.assertEqual(data["content"], source)
        self.assertEqual(data["language"], "python")
        self.assertEqual(data["lines"], 2)
        self.assertFalse(data["truncated"])

    def test_typescript_file_language_detected(self):
        source = "export const greet = (name: string): string => `Hello, ${name}`;\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / _JOB_ID_STR / "repo"
            workspace.mkdir(parents=True)
            (workspace / "greet.ts").write_text(source, encoding="utf-8")

            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok():
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "greet.ts"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["language"], "typescript")

    def test_html_file_language_detected_without_dot_prefix(self):
        source = "<main>Hello</main>\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / _JOB_ID_STR / "repo"
            workspace.mkdir(parents=True)
            (workspace / "index.html").write_text(source, encoding="utf-8")

            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok():
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "index.html"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["language"], "html")

    def test_unknown_extension_language_is_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / _JOB_ID_STR / "repo"
            workspace.mkdir(parents=True)
            (workspace / "Makefile").write_text("build:\n\tpython main.py\n", encoding="utf-8")

            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok():
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "Makefile"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.json()["data"]["language"])


class TestFileContentTruncated(unittest.TestCase):
    """50,000자 초과 파일은 truncated=True로 잘린 내용을 반환한다."""

    def test_large_file_returns_truncated(self):
        ## 50,001자 파일 생성
        big_content = "x" * 50_001
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / _JOB_ID_STR / "repo"
            workspace.mkdir(parents=True)
            (workspace / "big.py").write_text(big_content, encoding="utf-8")

            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok():
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "big.py"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertTrue(data["truncated"])
        self.assertEqual(len(data["content"]), 50_000)

    def test_exact_limit_file_not_truncated(self):
        ## 정확히 50,000자는 잘리지 않아야 한다
        exact_content = "y" * 50_000
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / _JOB_ID_STR / "repo"
            workspace.mkdir(parents=True)
            (workspace / "exact.py").write_text(exact_content, encoding="utf-8")

            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok():
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "exact.py"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json()["data"]["truncated"])


class TestFileContentEncodingFallback(unittest.TestCase):
    """UTF-8이 아닌 파일도 latin-1 fallback으로 읽을 수 있다."""

    def test_latin1_file_readable(self):
        ## latin-1 전용 바이트로 구성된 파일
        raw_bytes = "Ärger mit Ü".encode("latin-1")
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / _JOB_ID_STR / "repo"
            workspace.mkdir(parents=True)
            (workspace / "latin.txt").write_bytes(raw_bytes)

            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok():
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "latin.txt"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 200)
        self.assertIsNotNone(resp.json()["data"]["content"])


class TestFileContentAccessControl(unittest.TestCase):
    """private/team 파일 조회가 job 소유자 기준 권한 검사를 거치는지 검증한다."""

    @staticmethod
    def _mock_job_status_access(owner_id: UUID):
        from app.common.exceptions import JobNotFoundError

        async def _fake_get_job_status(job_id, current_user_id=None):
            if current_user_id == owner_id:
                return MagicMock()
            raise JobNotFoundError()

        mock_svc = MagicMock()
        mock_svc.get_job_status = AsyncMock(side_effect=_fake_get_job_status)
        return patch("app.repo.router.AnalysisService", return_value=mock_svc)

    @staticmethod
    def _request_file(tmpdir: str, current_user: dict | None):
        from app.infra.auth import get_current_user_optional

        workspace = Path(tmpdir) / _JOB_ID_STR / "repo" / "src"
        workspace.mkdir(parents=True)
        (workspace / "main.py").write_text("print('hi')\n", encoding="utf-8")

        app, settings_patcher = _make_app(tmpdir)
        app.dependency_overrides[get_current_user_optional] = lambda: current_user
        client = TestClient(app, raise_server_exceptions=False)

        try:
            return client.get(
                f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                params={"path": "src/main.py"},
            )
        finally:
            settings_patcher.stop()

    def test_owner_token_can_read_file(self):
        owner_id = uuid4()

        with tempfile.TemporaryDirectory() as tmpdir:
            with self._mock_job_status_access(owner_id):
                resp = self._request_file(tmpdir, {"sub": str(owner_id)})

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["content"], "print('hi')\n")

    def test_non_owner_token_is_denied(self):
        owner_id = uuid4()
        other_id = uuid4()

        with tempfile.TemporaryDirectory() as tmpdir:
            with self._mock_job_status_access(owner_id):
                resp = self._request_file(tmpdir, {"sub": str(other_id)})

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "JOB_NOT_FOUND")

    def test_anonymous_user_is_denied(self):
        owner_id = uuid4()

        with tempfile.TemporaryDirectory() as tmpdir:
            with self._mock_job_status_access(owner_id):
                resp = self._request_file(tmpdir, None)

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "JOB_NOT_FOUND")



# ──────────────────────────────────────────────
# Issue #226: 로컬 FS 누락 시 DB content fallback
# ──────────────────────────────────────────────
class TestFileContentDbFallback(unittest.TestCase):
    """로컬 워크스페이스에서 못 읽을 때 DB content로 복구한다."""

    def test_fs_missing_db_fallback_returns_200(self):
        recovered = "def recovered():\n    return 42\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / _JOB_ID_STR / "repo"
            workspace.mkdir(parents=True)
            ## 파일 미생성 → 로컬 read 실패 → DB fallback 경로 진입

            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok(), patch(
                "app.repo.router._read_db_fallback_content",
                new=AsyncMock(return_value=recovered),
            ):
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "src/main.py"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertEqual(data["content"], recovered)
        self.assertEqual(data["language"], "python")
        self.assertFalse(data["truncated"])

    def test_workspace_dir_missing_uses_db_fallback(self):
        ## clone workspace 디렉토리 자체가 없어도 DB fallback이 동작한다.
        recovered = "console.log('recovered');\n"
        with tempfile.TemporaryDirectory() as tmpdir:
            ## workspace 디렉토리 미생성
            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok(), patch(
                "app.repo.router._read_db_fallback_content",
                new=AsyncMock(return_value=recovered),
            ):
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "app.js"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["data"]["content"], recovered)

    def test_fs_and_db_both_missing_returns_404(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / _JOB_ID_STR / "repo"
            workspace.mkdir(parents=True)

            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok(), patch(
                "app.repo.router._read_db_fallback_content",
                new=AsyncMock(return_value=None),
            ):
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "src/missing.py"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "WORKSPACE_NOT_READY")

    def test_db_fallback_truncates_large_content(self):
        big = "z" * 50_001
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / _JOB_ID_STR / "repo"
            workspace.mkdir(parents=True)

            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok(), patch(
                "app.repo.router._read_db_fallback_content",
                new=AsyncMock(return_value=big),
            ):
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "big.py"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 200)
        data = resp.json()["data"]
        self.assertTrue(data["truncated"])
        self.assertEqual(len(data["content"]), 50_000)

    def test_binary_blocked_before_fallback(self):
        ## 바이너리 확장자는 FS/DB와 무관하게 422로 차단된다.
        with tempfile.TemporaryDirectory() as tmpdir:
            app, settings_patcher = _make_app(tmpdir)
            client = TestClient(app, raise_server_exceptions=False)

            with _mock_job_status_ok(), patch(
                "app.repo.router._read_db_fallback_content",
                new=AsyncMock(return_value="should-not-be-used"),
            ):
                resp = client.get(
                    f"/api/repo/analysis/{_JOB_ID_STR}/files/content",
                    params={"path": "logo.png"},
                )

            settings_patcher.stop()

        self.assertEqual(resp.status_code, 422)
        self.assertEqual(resp.json()["error"]["code"], "BINARY_FILE")


class _FakeResult:
    """EmbedRepository.get_file_content 단위 테스트용 가짜 execute 결과."""

    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return self

    def first(self):
        return self._rows[0] if self._rows else None

    def all(self):
        return list(self._rows)


class _FakeSession:
    """execute 호출 순서대로 FILE 결과 → CHUNK 결과를 반환하는 가짜 세션."""

    def __init__(self, file_rows, chunk_rows):
        self._results = [_FakeResult(file_rows), _FakeResult(chunk_rows)]
        self._idx = 0

    async def execute(self, _stmt):
        result = self._results[self._idx]
        self._idx += 1
        return result


class TestEmbedRepositoryGetFileContent(unittest.TestCase):
    """EmbedRepository.get_file_content 복구 우선순위 검증."""

    def _run(self, file_rows, chunk_rows):
        import asyncio

        from app.embed.repository import EmbedRepository

        repo = EmbedRepository(_FakeSession(file_rows, chunk_rows))
        return asyncio.run(repo.get_file_content(_JOB_ID, "src/main.py"))

    def test_returns_file_node_content_when_present(self):
        result = self._run(["FILE-CONTENT"], ["chunk-a", "chunk-b"])
        self.assertEqual(result, "FILE-CONTENT")

    def test_returns_empty_string_when_file_content_is_empty(self):
        result = self._run([""], ["chunk-a", "chunk-b"])
        self.assertEqual(result, "")

    def test_reassembles_chunks_when_file_content_none(self):
        result = self._run([None], ["chunk-a", "chunk-b"])
        self.assertEqual(result, "chunk-a\n\nchunk-b")

    def test_returns_none_when_no_data(self):
        result = self._run([], [])
        self.assertIsNone(result)



if __name__ == "__main__":
    unittest.main()
