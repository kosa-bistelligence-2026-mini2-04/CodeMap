import types
import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from starlette.websockets import WebSocketDisconnect

from app.common.exceptions import JobNotFoundError, register_exception_handlers
from app.list.websocket import ws_router
from app.repo.router import router as repo_router
from app.repo.schemas import JobStatus, JobStatusData, JobStatusResponse
from app.pipeline.schemas import PipelineStage, ProgressEvent

from ._helpers import AsyncSessionFactory


JOB_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


def job(status="IN_PROGRESS"):
    return types.SimpleNamespace(
        id=JOB_ID,
        status=status,
        progress=42,
        stage="CODE_MAP",
        message="running",
        user_id=USER_ID,
        team_id=None,
        is_private=True,
    )


def app_with(*routers):
    app = FastAPI()
    register_exception_handlers(app)
    for router in routers:
        app.include_router(router)
    return app


class FakeJobRepo:
    current_job = job()

    def __init__(self, *_args, **_kwargs):
        pass

    async def get_job_by_id(self, job_id):
        return self.current_job


class FakeAnalysisService:
    mode = "ok"

    def __init__(self, *_args, **_kwargs):
        pass

    async def get_job_status(self, job_id, current_user_id=None):
        if self.mode == "hidden":
            raise JobNotFoundError()
        now = datetime.now(timezone.utc)
        return JobStatusResponse(
            data=JobStatusData(
                jobId=job_id,
                repoName="codemap",
                owner="oosu",
                branch="main",
                clonePath="/tmp/codemap",
                status=JobStatus.IN_PROGRESS,
                repoUrl="https://github.com/oosu/codemap",
                stage="CODE_MAP",
                progress=42,
                statusMessage="running",
                model="auto",
                report=None,
                createdAt=now,
                updatedAt=now,
            )
        )


class FakeEventManager:
    def get_last_event(self, *_args):
        return None

    async def subscribe(self, *_args):
        yield ProgressEvent(
            stage=PipelineStage.CODE_MAP,
            status=JobStatus.IN_PROGRESS,
            progress=42,
            message="running",
            timestamp=datetime.now(timezone.utc),
        )


class ProgressChannelAuthTests(unittest.TestCase):
    def test_ws_invalid_job_id_closes_4004(self):
        from fastapi.testclient import TestClient

        client = TestClient(app_with(ws_router))
        with self.assertRaises(WebSocketDisconnect) as ctx:
            with client.websocket_connect("/ws/list/progress/not-a-uuid") as ws:
                ws.receive_text()
        self.assertEqual(ctx.exception.code, 4004)

    def test_ws_forbidden_closes_4403(self):
        from fastapi.testclient import TestClient

        client = TestClient(app_with(ws_router))
        with patch("app.list.websocket._user_id_from_token", return_value=None):
            with patch("app.list.websocket.async_session_factory", return_value=AsyncSessionFactory(object())):
                with patch("app.list.websocket.AnalysisJobRepository", FakeJobRepo):
                    with patch("app.list.websocket.access.can_access_job", new=AsyncMock(return_value=False)):
                        with self.assertRaises(WebSocketDisconnect) as ctx:
                            with client.websocket_connect(f"/ws/list/progress/{JOB_ID}?token=bad") as ws:
                                ws.receive_text()
        self.assertEqual(ctx.exception.code, 4403)

    def test_ws_authorized_receives_current_status(self):
        from fastapi.testclient import TestClient

        client = TestClient(app_with(ws_router))
        with patch("app.list.websocket._user_id_from_token", return_value=USER_ID):
            with patch("app.list.websocket.async_session_factory", return_value=AsyncSessionFactory(object())):
                with patch("app.list.websocket.AnalysisJobRepository", FakeJobRepo):
                    with patch("app.list.websocket.access.can_access_job", new=AsyncMock(return_value=True)):
                        with client.websocket_connect(f"/ws/list/progress/{JOB_ID}?token=ok") as ws:
                            payload = ws.receive_json()
        self.assertEqual(payload["jobId"], str(JOB_ID))
        self.assertEqual(payload["status"], "running")

    def test_sse_forbidden_token_hides_job_as_404(self):
        from fastapi.testclient import TestClient

        FakeAnalysisService.mode = "hidden"
        client = TestClient(app_with(repo_router))
        with patch("app.repo.router._user_id_from_token", return_value=None):
            with patch("app.repo.router.async_session_factory", return_value=AsyncSessionFactory(object())):
                with patch("app.repo.router.AnalysisService", FakeAnalysisService):
                    resp = client.get(f"/api/repo/analysis/{JOB_ID}/events?token=bad")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "JOB_NOT_FOUND")

    def test_sse_authorized_starts_stream(self):
        from fastapi.testclient import TestClient

        FakeAnalysisService.mode = "ok"
        client = TestClient(app_with(repo_router))
        with patch("app.repo.router._user_id_from_token", return_value=USER_ID):
            with patch("app.repo.router.async_session_factory", return_value=AsyncSessionFactory(object())):
                with patch("app.repo.router.AnalysisService", FakeAnalysisService):
                    with patch("app.repo.router.event_manager", FakeEventManager()):
                        with client.stream("GET", f"/api/repo/analysis/{JOB_ID}/events?token=ok") as resp:
                            first = next(resp.iter_text())
        self.assertEqual(resp.status_code, 200)
        self.assertIn("CODE_MAP", first)


if __name__ == "__main__":
    unittest.main()
