import unittest
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.exceptions import register_exception_handlers
from app.list.models import AnalysisJobDetailModel, AnalysisJobListModel
from app.list.router import router as list_router
from app.list.service import AnalysisJobDetailResult, AnalysisJobListResult, get_list_service
from app.list.websocket import ws_router
import app.list.websocket as list_websocket


TEST_JOB_ID = UUID("8f2d5a3c-b1a9-4d2c-9a3e-7f8a9b0c1d2e")
TEST_CREATED_AT = datetime(2026, 6, 18, 2, 0, tzinfo=timezone.utc)
TEST_UPDATED_AT = datetime(2026, 6, 18, 2, 3, 30, tzinfo=timezone.utc)


class FakeListService:
    def __init__(self, *, fail: bool = False, missing_detail: bool = False):
        self.fail = fail
        self.missing_detail = missing_detail

    async def get_analysis_jobs(self, page: int, limit: int) -> AnalysisJobListResult:
        if self.fail:
            raise RuntimeError("database unavailable")
        return AnalysisJobListResult(
            total_count=1,
            page=page,
            limit=limit,
            jobs=[
                AnalysisJobListModel(
                    job_id=TEST_JOB_ID,
                    repo_url="https://github.com/example/codemap",
                    branch="main",
                    status="completed",
                    progress=100,
                    failed_agent=None,
                    error_message=None,
                    created_at=TEST_CREATED_AT,
                    updated_at=TEST_UPDATED_AT,
                )
            ],
        )

    async def get_analysis_job_detail(self, job_id: UUID) -> AnalysisJobDetailResult:
        if self.fail:
            raise RuntimeError("database unavailable")
        if self.missing_detail:
            return AnalysisJobDetailResult(job=None)
        return AnalysisJobDetailResult(
            job=AnalysisJobDetailModel(
                job_id=job_id,
                repo_url="https://github.com/example/codemap",
                repo_name="codemap",
                owner="example",
                branch="main",
                status="running",
                current_step="CODE_MAP",
                progress=45,
                message="코드 구조를 분석하는 중입니다.",
                created_at=TEST_CREATED_AT,
                updated_at=TEST_UPDATED_AT,
            )
        )


def create_rest_client(service: FakeListService) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(list_router)
    app.dependency_overrides[get_list_service] = lambda: service
    return TestClient(app)


class ProjectListApi001Tests(unittest.TestCase):
    def test_get_analysis_list_returns_project_history(self):
        client = create_rest_client(FakeListService())

        response = client.get(
            "/api/list/analysis?page=1&limit=10",
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["message"], "success")
        self.assertEqual(body["data"]["totalCount"], 1)
        self.assertEqual(body["data"]["page"], 1)
        self.assertEqual(body["data"]["limit"], 10)
        self.assertEqual(body["data"]["jobs"][0]["jobId"], str(TEST_JOB_ID))
        self.assertEqual(body["data"]["jobs"][0]["status"], "completed")

    def test_get_analysis_list_requires_authorization(self):
        client = create_rest_client(FakeListService())

        response = client.get("/api/list/analysis?page=1&limit=10")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_get_analysis_list_maps_service_failure_to_database_error(self):
        client = create_rest_client(FakeListService(fail=True))

        response = client.get(
            "/api/list/analysis?page=1&limit=10",
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "DATABASE_ERROR")


class ProjectListApi004Tests(unittest.TestCase):
    def test_get_analysis_detail_returns_job_metadata(self):
        client = create_rest_client(FakeListService())

        response = client.get(
            f"/api/list/analysis/{TEST_JOB_ID}",
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["data"]["jobId"], str(TEST_JOB_ID))
        self.assertEqual(body["data"]["repoName"], "codemap")
        self.assertEqual(body["data"]["status"], "running")
        self.assertEqual(body["data"]["currentStep"], "CODE_MAP")
        self.assertEqual(body["data"]["progress"], 45)

    def test_get_analysis_detail_rejects_invalid_uuid(self):
        client = create_rest_client(FakeListService())

        response = client.get(
            "/api/list/analysis/not-a-uuid",
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_JOB_ID")

    def test_get_analysis_detail_returns_not_found_for_missing_job(self):
        client = create_rest_client(FakeListService(missing_detail=True))

        response = client.get(
            "/api/list/analysis/00000000-0000-0000-0000-000000000000",
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "JOB_NOT_FOUND")

    def test_get_analysis_detail_maps_service_failure_to_database_error(self):
        client = create_rest_client(FakeListService(fail=True))

        response = client.get(
            f"/api/list/analysis/{TEST_JOB_ID}",
            headers={"Authorization": "Bearer test-token"},
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "DATABASE_ERROR")


@dataclass
class FakeAnalysisJob:
    id: UUID
    status: str
    progress: int
    stage: str | None
    message: str | None


class FakeAnalysisJobRepository:
    def __init__(self, session):
        self.session = session

    async def get_job_by_id(self, job_id: UUID):
        if job_id == TEST_JOB_ID:
            return FakeAnalysisJob(
                id=job_id,
                status="COMPLETED",
                progress=100,
                stage="REPORT",
                message=None,
            )
        return None


@asynccontextmanager
async def fake_session_factory():
    yield object()


def create_websocket_client() -> TestClient:
    app = FastAPI()
    app.include_router(ws_router)
    return TestClient(app)


class ProjectListApi003Tests(unittest.TestCase):
    def setUp(self):
        self.original_session_factory = list_websocket.async_session_factory
        self.original_repository = list_websocket.AnalysisJobRepository
        list_websocket.async_session_factory = fake_session_factory
        list_websocket.AnalysisJobRepository = FakeAnalysisJobRepository

    def tearDown(self):
        list_websocket.async_session_factory = self.original_session_factory
        list_websocket.AnalysisJobRepository = self.original_repository

    def test_websocket_rejects_invalid_job_id_format(self):
        client = create_websocket_client()

        with self.assertRaises(WebSocketDisconnect) as context:
            with client.websocket_connect("/ws/list/progress/not-a-uuid") as websocket:
                websocket.receive_text()

        self.assertEqual(context.exception.code, 4004)

    def test_websocket_rejects_missing_job_id(self):
        client = create_websocket_client()

        with self.assertRaises(WebSocketDisconnect) as context:
            with client.websocket_connect("/ws/list/progress/00000000-0000-0000-0000-000000000000") as websocket:
                websocket.receive_text()

        self.assertEqual(context.exception.code, 4004)

    def test_websocket_sends_current_snapshot_and_closes_completed_job(self):
        client = create_websocket_client()

        with client.websocket_connect(f"/ws/list/progress/{TEST_JOB_ID}") as websocket:
            message = websocket.receive_json()
            self.assertEqual(message["jobId"], str(TEST_JOB_ID))
            self.assertEqual(message["status"], "completed")
            self.assertEqual(message["progress"], 100)
            self.assertEqual(message["currentStep"], "REPORT")
            with self.assertRaises(WebSocketDisconnect) as context:
                websocket.receive_text()

        self.assertEqual(context.exception.code, 1000)


if __name__ == "__main__":
    unittest.main()
