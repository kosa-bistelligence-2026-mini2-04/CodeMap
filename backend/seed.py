import asyncio
import uuid
import sys
import os

# Ensure backend directory is in the sys path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import select
from app.infra.database import async_session_factory
from app.auth.models import User
from app.auth.service import _hash_password
from app.repo.models import AnalysisJob
from app.repo.schemas import JobStatus, PipelineStage

async def seed_data():
    async with async_session_factory() as session:
        # Create users
        test_users = ["test1@codemap.com", "test2@codemap.com"]
        hashed_pw = _hash_password("test1234!")

        for email in test_users:
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            user = result.scalars().first()

            if not user:
                user = User(
                    id=uuid.uuid4(),
                    email=email,
                    hashed_password=hashed_pw
                )
                session.add(user)
                print(f"Created user {email}")
            else:
                # Update password just in case
                user.hashed_password = hashed_pw
                print(f"User {email} already exists. Updated password.")
            
            # Create dummy AnalysisJob records
            # Since AnalysisJob isn't strictly tied to a user_id by foreign key in the current schema (repo_url, repo_name, owner), 
            # we just insert some mock repos. (Wait, let's verify if AnalysisJob has a user_id. From repo/models.py, it doesn't seem to have a user_id foreign key. 
            # If it's globally shared or tracked differently, we just create the records.)
            
            # We'll create some repos
            mock_repos = [
                ("https://github.com/facebook/react", "react", "facebook"),
                ("https://github.com/vuejs/core", "core", "vuejs"),
                ("https://github.com/kosa-bistelligence-2026-mini2-04/CodeMap", "CodeMap", "kosa-bistelligence-2026-mini2-04")
            ]
            
            for url, name, owner in mock_repos:
                stmt = select(AnalysisJob).where(AnalysisJob.repo_url == url)
                result = await session.execute(stmt)
                job = result.scalars().first()
                if not job:
                    job = AnalysisJob(
                        id=uuid.uuid4(),
                        repo_url=url,
                        repo_name=name,
                        owner=owner,
                        branch="main",
                        status=JobStatus.COMPLETED.value,
                        stage=PipelineStage.REPORT.value,
                        progress=100,
                        message="분석 완료",
                        model_used="auto",
                        force_refresh=False,
                        report_json={"message": "Mock report for testing"}
                    )
                    session.add(job)
                    print(f"Created AnalysisJob for {url}")
                else:
                    # Update status to COMPLETED if not
                    job.status = JobStatus.COMPLETED.value
                    job.progress = 100
                    job.stage = PipelineStage.REPORT.value

        await session.commit()
        print("Database seeding completed.")

if __name__ == "__main__":
    asyncio.run(seed_data())
