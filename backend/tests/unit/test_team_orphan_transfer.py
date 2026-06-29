import unittest
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

from app.infra.database import Base
from app.auth.models import User, Team, TeamMember
from app.repo.models import AnalysisJob
from app.team.service import TeamService

engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

class TeamOrphanTransferTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.session = TestingSessionLocal()
        self.team_service = TeamService(self.session)

    async def asyncTearDown(self):
        await self.session.close()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def test_transfer_orphan_ownership(self):
        user_leaving_id = uuid.uuid4()
        user_member_old_id = uuid.uuid4()
        user_member_new_id = uuid.uuid4()
        user_other_team_id = uuid.uuid4()

        team1_id = uuid.uuid4()
        team2_id = uuid.uuid4() # Team where user is the only member

        now = datetime.now(timezone.utc)

        # Create users
        users = [
            User(id=user_leaving_id, email="leaving@test.com", hashed_password="pwd"),
            User(id=user_member_old_id, email="old@test.com", hashed_password="pwd"),
            User(id=user_member_new_id, email="new@test.com", hashed_password="pwd"),
            User(id=user_other_team_id, email="other@test.com", hashed_password="pwd"),
        ]
        self.session.add_all(users)

        # Create teams
        teams = [
            Team(id=team1_id, name="Team 1", created_by_user_id=user_leaving_id),
            Team(id=team2_id, name="Team 2", created_by_user_id=user_leaving_id),
        ]
        self.session.add_all(teams)

        # Create Team Members
        members = [
            # Team 1 members
            TeamMember(id=uuid.uuid4(), team_id=team1_id, user_id=user_leaving_id, role="owner", created_at=now),
            TeamMember(id=uuid.uuid4(), team_id=team1_id, user_id=user_member_old_id, role="member", created_at=now - timedelta(days=5)),
            TeamMember(id=uuid.uuid4(), team_id=team1_id, user_id=user_member_new_id, role="member", created_at=now - timedelta(days=2)),

            # Team 2 member (only the leaving user)
            TeamMember(id=uuid.uuid4(), team_id=team2_id, user_id=user_leaving_id, role="owner", created_at=now),
        ]
        self.session.add_all(members)

        # Create Analysis Jobs
        job_t1_id = uuid.uuid4()
        job_t2_id = uuid.uuid4()

        jobs = [
            AnalysisJob(id=job_t1_id, repo_url="url1", repo_name="repo", owner="t1", branch="main", status="COMPLETED", user_id=user_leaving_id, team_id=team1_id, is_private=False),
            AnalysisJob(id=job_t2_id, repo_url="url2", repo_name="repo", owner="t2", branch="main", status="COMPLETED", user_id=user_leaving_id, team_id=team2_id, is_private=False),
        ]
        self.session.add_all(jobs)
        await self.session.commit()

        # Act
        await self.team_service.transfer_orphan_ownership(user_leaving_id)

        # Assert
        # Team 1 job should be transferred to user_member_old_id
        job_t1 = await self.session.get(AnalysisJob, job_t1_id)
        self.assertEqual(job_t1.user_id, user_member_old_id)

        # Team 2 job should become orphaned (user_id = None) since there are no other members
        job_t2 = await self.session.get(AnalysisJob, job_t2_id)
        self.assertIsNone(job_t2.user_id)

if __name__ == "__main__":
    unittest.main()
