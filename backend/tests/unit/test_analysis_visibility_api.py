import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import BackgroundTasks

from app.common.exceptions import CodeMapException
from app.infra.auth import get_current_user, get_current_user_optional
from app.list.models import AnalysisJobDetailModel, AnalysisJobListModel
from app.list.router import router as list_router
from app.list.service import (
    AnalysisJobDetailResult,
    AnalysisJobListResult,
    get_list_service,
)
from app.repo.router import router as repo_router

from ._helpers import client_with_router, user


USER_ID = uuid.uuid4()
TEAM_ID = uuid.uuid4()
JOB_ID = uuid.uuid4()
NOW = datetime.now(timezone.utc)


class FakeRepoService:
    def __init__(self, *_args, **_kwargs):
        pass

    async def register_analysis(self, request, background_tasks: BackgroundTasks, user_id=None):
        if request.teamId and request.visibility != "team":
            raise CodeMapException(400, "INVALID_VISIBILITY", "teamId가 지정되면 visibility는 team이어야 합니다.")
        if request.visibility == "team" and request.teamId == TEAM_ID:
            raise CodeMapException(403, "TEAM_ACCESS_DENIED", "팀 접근 권한이 없습니다.")
        return {
            "code": 201,
            "message": "created",
            "data": {
                "jobId": JOB_ID,
                "repoName": "codemap",
                "owner": "oosu",
                "branch": "main",
                "status": "IN_PROGRESS",
                "createdAt": NOW,
                "model": "auto",
            },
        }


class FakeListService:
    def __init__(self, *, missing_detail=False):
        self.calls = []
        self.missing_detail = missing_detail

    async def get_analysis_jobs(self, page, limit, current_user_id=None, scope="all", team_id=None):
        self.calls.append((scope, team_id, current_user_id))
        return AnalysisJobListResult(
            total_count=1,
            page=page,
            limit=limit,
            jobs=[
                AnalysisJobListModel(
                    job_id=JOB_ID,
                    repo_url="https://github.com/oosu/codemap",
                    branch="main",
                    status="completed",
                    progress=100,
                    failed_agent=None,
                    error_message=None,
                    visibility=scope if scope != "all" else "private",
                    team_id=team_id,
                    created_at=NOW,
                    updated_at=NOW,
                )
            ],
        )

    async def get_analysis_job_detail(self, job_id, current_user_id=None):
        if self.missing_detail:
            return AnalysisJobDetailResult(job=None)
        return AnalysisJobDetailResult(
            job=AnalysisJobDetailModel(
                job_id=job_id,
                repo_url="https://github.com/oosu/codemap",
                repo_name="codemap",
                owner="oosu",
                branch="main",
                status="completed",
                current_step=None,
                progress=100,
                message=None,
                visibility="private",
                team_id=None,
                created_at=NOW,
                updated_at=NOW,
            )
        )


def auth_client(*, list_service=None, optional_user=None, required_user=None):
    overrides = {
        get_current_user_optional: lambda: optional_user,
        get_current_user: lambda: required_user or user(USER_ID),
    }
    if list_service:
        overrides[get_list_service] = lambda: list_service
    return client_with_router(repo_router, list_router, overrides=overrides, exception_handlers=True)


class AnalysisVisibilityApiTests(unittest.TestCase):
    def test_register_analysis_requires_auth_for_private_history(self):
        client = auth_client(optional_user=None)

        resp = client.post("/api/repo/analysis", json={"repoUrl": "https://github.com/oosu/codemap"})

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "PRIVATE_REQUIRES_AUTH")

    def test_team_id_requires_team_visibility(self):
        client = auth_client(optional_user=user(USER_ID))

        with patch("app.repo.router.AnalysisService", FakeRepoService):
            resp = client.post(
                "/api/repo/analysis",
                json={
                    "repoUrl": "https://github.com/oosu/codemap",
                    "visibility": "private",
                    "teamId": str(TEAM_ID),
                },
            )

        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["error"]["code"], "INVALID_VISIBILITY")

    def test_team_visibility_rejects_non_member(self):
        client = auth_client(optional_user=user(USER_ID))

        with patch("app.repo.router.AnalysisService", FakeRepoService):
            resp = client.post(
                "/api/repo/analysis",
                json={
                    "repoUrl": "https://github.com/oosu/codemap",
                    "visibility": "team",
                    "teamId": str(TEAM_ID),
                },
            )

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["error"]["code"], "TEAM_ACCESS_DENIED")

    def test_list_scope_and_team_id_are_forwarded(self):
        service = FakeListService()
        client = auth_client(list_service=service, required_user=user(USER_ID))

        resp = client.get(f"/api/list/analysis?scope=team&teamId={TEAM_ID}")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(service.calls[0][0], "team")
        self.assertEqual(service.calls[0][1], TEAM_ID)

    def test_detail_hides_inaccessible_job_as_404(self):
        client = auth_client(list_service=FakeListService(missing_detail=True))

        resp = client.get(f"/api/list/analysis/{JOB_ID}")

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["error"]["code"], "JOB_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
