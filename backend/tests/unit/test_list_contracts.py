import unittest
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.common.exceptions import register_exception_handlers
from app.infra.auth import get_current_user
from app.list.models import AnalysisJobDetailModel, AnalysisJobListModel, AnalysisJobStatusUpdateModel
from app.list.router import router as list_router
from app.list.service import (
    AnalysisJobDetailResult,
    AnalysisJobListResult,
    AnalysisJobStatusUpdateResult,
    ListService,
    get_list_service,
)
from app.list.websocket import ws_router
import app.list.websocket as list_websocket


TEST_JOB_ID = UUID("8f2d5a3c-b1a9-4d2c-9a3e-7f8a9b0c1d2e")
TEST_CREATED_AT = datetime(2026, 6, 18, 2, 0, tzinfo=timezone.utc)
TEST_UPDATED_AT = datetime(2026, 6, 18, 2, 3, 30, tzinfo=timezone.utc)


class FakeListService:
    def __init__(self, *, fail: bool = False, missing_detail: bool = False, missing_status: bool = False):
        self.fail = fail
        self.missing_detail = missing_detail
        self.missing_status = missing_status
        self.status_update_args = None

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

    async def update_analysis_job_status(
        self,
        job_id: UUID,
        status: str,
        current_step: str | None,
        progress: int,
        message: str | None,
        error_message: str | None,
    ) -> AnalysisJobStatusUpdateResult:
        if self.fail:
            raise RuntimeError("database unavailable")
        self.status_update_args = {
            "job_id": job_id,
            "status": status,
            "current_step": current_step,
            "progress": progress,
            "message": message,
            "error_message": error_message,
        }
        if self.missing_status:
            return AnalysisJobStatusUpdateResult(job=None)
        return AnalysisJobStatusUpdateResult(
            job=AnalysisJobStatusUpdateModel(
                job_id=job_id,
                status=status,
                current_step=current_step,
                progress=progress,
                updated_at=TEST_UPDATED_AT,
            )
        )


from fastapi import FastAPI, Request
from app.common.exceptions import UnauthorizedError

def mock_get_current_user(request: Request):
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer ") or not auth[7:].strip():
        raise UnauthorizedError()
    return {"sub": "test-uuid", "email": "test@example.com"}

def create_rest_client(service: FakeListService) -> TestClient:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(list_router)
    app.dependency_overrides[get_list_service] = lambda: service
    app.dependency_overrides[get_current_user] = mock_get_current_user
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


class ProjectListApi006Tests(unittest.TestCase):
    def test_patch_analysis_status_returns_updated_job_status(self):
        service = FakeListService()
        client = create_rest_client(service)

        response = client.patch(
            f"/api/list/analysis/{TEST_JOB_ID}/status",
            headers={"Authorization": "Bearer service-token"},
            json={
                "status": "failed",
                "currentStep": "CODE_MAP",
                "progress": 45,
                "message": "analysis failed",
                "errorMessage": "File limit exceeded during parse stage.",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["code"], 200)
        self.assertEqual(body["message"], "success")
        self.assertEqual(body["data"]["jobId"], str(TEST_JOB_ID))
        self.assertEqual(body["data"]["status"], "failed")
        self.assertEqual(body["data"]["currentStep"], "CODE_MAP")
        self.assertEqual(body["data"]["progress"], 45)
        self.assertEqual(service.status_update_args["job_id"], TEST_JOB_ID)
        self.assertEqual(service.status_update_args["error_message"], "File limit exceeded during parse stage.")

    def test_patch_analysis_status_rejects_invalid_job_id(self):
        client = create_rest_client(FakeListService())

        response = client.patch(
            "/api/list/analysis/not-a-uuid/status",
            headers={"Authorization": "Bearer service-token"},
            json={"status": "running", "progress": 45},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_JOB_ID")

    def test_patch_analysis_status_requires_authorization(self):
        client = create_rest_client(FakeListService())

        response = client.patch(
            f"/api/list/analysis/{TEST_JOB_ID}/status",
            json={"status": "running", "progress": 45},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_patch_analysis_status_rejects_wrong_service_token(self):
        client = create_rest_client(FakeListService())

        response = client.patch(
            f"/api/list/analysis/{TEST_JOB_ID}/status",
            headers={"Authorization": "Bearer anything"},
            json={"status": "running", "progress": 45},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_patch_analysis_status_rejects_unknown_status(self):
        client = create_rest_client(FakeListService())

        response = client.patch(
            f"/api/list/analysis/{TEST_JOB_ID}/status",
            headers={"Authorization": "Bearer service-token"},
            json={"status": "paused", "progress": 45},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_STATUS")

    def test_patch_analysis_status_rejects_out_of_range_progress(self):
        client = create_rest_client(FakeListService())

        response = client.patch(
            f"/api/list/analysis/{TEST_JOB_ID}/status",
            headers={"Authorization": "Bearer service-token"},
            json={"status": "running", "progress": 101},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "INVALID_PROGRESS")

    def test_patch_analysis_status_returns_not_found_for_missing_job(self):
        client = create_rest_client(FakeListService(missing_status=True))

        response = client.patch(
            f"/api/list/analysis/{TEST_JOB_ID}/status",
            headers={"Authorization": "Bearer service-token"},
            json={"status": "running", "progress": 45},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "JOB_NOT_FOUND")

    def test_patch_analysis_status_maps_service_failure_to_database_error(self):
        client = create_rest_client(FakeListService(fail=True))

        response = client.patch(
            f"/api/list/analysis/{TEST_JOB_ID}/status",
            headers={"Authorization": "Bearer service-token"},
            json={"status": "running", "progress": 45},
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"]["code"], "DATABASE_ERROR")


class FakeStatusRepository:
    def __init__(self):
        self.update_args = None

    async def update_analysis_job_status(
        self,
        job_id: UUID,
        status: str,
        current_step: str | None,
        progress: int,
        message: str | None,
    ):
        self.update_args = {
            "job_id": job_id,
            "status": status,
            "current_step": current_step,
            "progress": progress,
            "message": message,
        }
        return AnalysisJobStatusUpdateModel(
            job_id=job_id,
            status=status,
            current_step=current_step,
            progress=progress,
            updated_at=TEST_UPDATED_AT,
        )


class ProjectListStatusServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_update_status_maps_api_status_to_database_status(self):
        service = ListService(db=None)
        repository = FakeStatusRepository()
        service.repository = repository

        result = await service.update_analysis_job_status(
            job_id=TEST_JOB_ID,
            status="queued",
            current_step="CLONE",
            progress=0,
            message="cloned",
            error_message=None,
        )

        self.assertEqual(repository.update_args["status"], "CLONED")
        self.assertEqual(result.job.status, "CLONED")

    async def test_update_failed_status_stores_error_message_first(self):
        service = ListService(db=None)
        repository = FakeStatusRepository()
        service.repository = repository

        await service.update_analysis_job_status(
            job_id=TEST_JOB_ID,
            status="failed",
            current_step="CODE_MAP",
            progress=45,
            message="user-facing message",
            error_message="File limit exceeded during parse stage.",
        )

        self.assertEqual(repository.update_args["status"], "FAILED")
        self.assertEqual(repository.update_args["message"], "File limit exceeded during parse stage.")


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
