"""Tool router contract tests."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))


class TestToolRouter(unittest.TestCase):
    _auth_headers = {"Authorization": "Bearer service-token"}

    def _client(self, clone_base_dir: str | None = None) -> TestClient:
        from app.infra.database import get_db
        from app.tool.router import router

        app = FastAPI()

        async def fake_db():
            yield object()

        app.dependency_overrides[get_db] = fake_db
        app.include_router(router)
        if clone_base_dir:
            patcher = patch("app.tool.service.get_settings")
            mocked = patcher.start()
            self.addCleanup(patcher.stop)
            mocked.return_value.CLONE_BASE_DIR = clone_base_dir
        return TestClient(app)

    def test_execute_tool_accepts_single_json_body_and_calls_vector_search(self):
        job_id = "00000000-0000-0000-0000-000000000101"
        run_id = "00000000-0000-0000-0000-000000000202"
        hit = {
            "file_path": "backend/app/auth/service.py",
            "content": "def login(): pass",
            "rrf_score": 0.5,
            "semantic_rank": 1,
            "bm25_rank": 2,
        }
        with patch("app.tool.service.hybrid_search", AsyncMock(return_value=[hit])):
            response = self._client().post(
                "/tools/execute",
                headers=self._auth_headers,
                json={
                    "tool_name": "vector_search",
                    "arguments": {"query": "login"},
                    "job_id": job_id,
                    "run_id": run_id,
                },
            )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "success")
        self.assertEqual(body["data"]["jobId"], job_id)
        self.assertEqual(body["data"]["results"][0]["path"], "backend/app/auth/service.py")

    def test_execute_tool_requires_tool_name_and_arguments(self):
        response = self._client().post(
            "/tools/execute",
            headers=self._auth_headers,
            json={"tool_name": "vector_search"},
        )

        self.assertEqual(response.status_code, 422)

    def test_execute_tool_reads_repository_file_from_job_clone_path(self):
        job_id = "00000000-0000-0000-0000-000000000303"
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / job_id / "repo"
            repo.mkdir(parents=True)
            (repo / "app.py").write_text("print('hello')\n", encoding="utf-8")

            response = self._client(tmp).post(
                "/tools/execute",
                headers=self._auth_headers,
                json={
                    "tool_name": "file_read",
                    "arguments": {"path": "app.py"},
                    "job_id": job_id,
                },
            )

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(body["status"], "success")
        self.assertIn("print('hello')", body["data"]["results"][0]["snippet"])

    def test_execute_tool_rejects_unsupported_tool_name(self):
        response = self._client().post(
            "/tools/execute",
            headers=self._auth_headers,
            json={
                "tool_name": "shell",
                "arguments": {"cmd": "pwd"},
                "job_id": "00000000-0000-0000-0000-000000000404",
            },
        )

        self.assertEqual(response.status_code, 400)

    def test_execute_tool_requires_service_token(self):
        response = self._client().post(
            "/tools/execute",
            json={
                "tool_name": "file_read",
                "arguments": {"path": "app.py"},
                "job_id": "00000000-0000-0000-0000-000000000505",
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_execute_tool_rejects_invalid_service_token(self):
        response = self._client().post(
            "/tools/execute",
            headers={"Authorization": "Bearer wrong-token"},
            json={
                "tool_name": "file_read",
                "arguments": {"path": "app.py"},
                "job_id": "00000000-0000-0000-0000-000000000606",
            },
        )

        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
