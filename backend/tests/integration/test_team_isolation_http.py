import unittest
import asyncio
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.infra.database import get_db, Base
from app.infra.auth import get_current_user
from app.repo.models import AnalysisJob
from app.auth.models import User, Team, TeamMember, TeamInvite

engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestingSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


class TeamIsolationHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self.overrides_to_restore = {}
        # get_db override는 클래스 생명주기 안에서만 설정/복구하여 전역 상태 누수를 방지한다.
        self.overrides_to_restore[get_db] = app.dependency_overrides.get(get_db)
        app.dependency_overrides[get_db] = override_get_db
        # TestClient도 setUp에서 생성해 전역 결합을 줄인다.
        self.client = TestClient(app)

    async def asyncTearDown(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        # 원래 override가 없었으면 제거, 있었으면 복구한다.
        for k, v in self.overrides_to_restore.items():
            if v is None:
                app.dependency_overrides.pop(k, None)
            else:
                app.dependency_overrides[k] = v
        self.overrides_to_restore = {}

    def override_auth(self, user_id: str, email: str):
        if get_current_user not in self.overrides_to_restore:
            self.overrides_to_restore[get_current_user] = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = lambda: {"sub": user_id, "email": email}

    async def test_team_isolation_and_invites(self):
        owner_id = str(uuid4())
        owner_email = "owner@example.com"
        member_id = str(uuid4())
        member_email = "member@example.com"
        other_id = str(uuid4())
        other_email = "other@example.com"

        # 1. Owner creates team
        self.override_auth(owner_id, owner_email)
        resp = self.client.post("/api/teams", json={"name": "Test Team"})
        self.assertEqual(resp.status_code, 200)
        team_id = resp.json()["id"]

        # 2. Non-owner cannot invite
        self.override_auth(member_id, member_email)
        resp = self.client.post(f"/api/teams/{team_id}/invites", json={"email": "new@example.com"})
        self.assertEqual(resp.status_code, 403)

        # 3. Owner invites member
        self.override_auth(owner_id, owner_email)
        resp = self.client.post(f"/api/teams/{team_id}/invites", json={"email": member_email, "role": "member"})
        self.assertEqual(resp.status_code, 201)
        invite_id = resp.json()["inviteId"]

        # 4. Member checks invites
        self.override_auth(member_id, member_email)
        resp = self.client.get("/api/team-invites")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["invites"]), 1)

        # 5. Member accepts invite
        resp = self.client.post(f"/api/team-invites/{invite_id}/accept")
        self.assertEqual(resp.status_code, 200)

        # 6. Duplicate accept -> 409
        resp = self.client.post(f"/api/team-invites/{invite_id}/accept")
        self.assertEqual(resp.status_code, 409)

        # 7. Create jobs for team and private
        self.override_auth(owner_id, owner_email)
        from uuid import UUID
        async with TestingSessionLocal() as db:
            # Team job

            team_job = AnalysisJob(
                id=uuid4(),
                repo_url="https://github.com/team/repo",
                repo_name="repo",
                owner="team",
                branch="main",
                status="COMPLETED",
                user_id=UUID(owner_id),
                is_private=False,
                team_id=UUID(team_id),
            )
            # Private job
            private_job = AnalysisJob(
                id=uuid4(),
                repo_url="https://github.com/owner/repo",
                repo_name="repo",
                owner="owner",
                branch="main",
                status="COMPLETED",
                user_id=UUID(owner_id),
                is_private=True,
                team_id=None,
            )
            db.add(team_job)
            db.add(private_job)
            await db.commit()

        # 8. List jobs filtering by scope
        self.override_auth(member_id, member_email)
        resp = self.client.get(f"/api/list/analysis?scope=team&teamId={team_id}")
        self.assertEqual(resp.status_code, 200)
        # member should see team job, but not private job
        jobs = resp.json()["data"]["jobs"]
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]["visibility"], "team")

        # Other user shouldn't see team job
        self.override_auth(other_id, other_email)
        resp = self.client.get(f"/api/list/analysis?scope=team&teamId={team_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["data"]["jobs"]), 0)

if __name__ == "__main__":
    unittest.main()
