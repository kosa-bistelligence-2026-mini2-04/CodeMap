"""
팀 워크스페이스 격리 단위 테스트 (PR #194 자체 리뷰 N1 보강)

- app.common.access.can_access_job / user_has_team_access 의 판정 규칙
- AnalysisService._resolve_visibility 의 visibility/teamId 검증 (M2)
DB 없이 fake 세션/리포지토리로 순수 판정 로직을 검증한다.
"""

import types
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from app.common import access
from app.common.exceptions import CodeMapException
from app.repo.service import AnalysisService


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeSession:
    """execute() 호출 시 미리 지정한 멤버십 존재 여부를 돌려주는 가짜 세션."""

    def __init__(self, member_exists: bool):
        self._member_exists = member_exists
        self.executed = 0

    async def execute(self, *_args, **_kwargs):
        self.executed += 1
        return FakeResult(uuid4() if self._member_exists else None)


def _job(team_id=None, user_id=None, is_private=False):
    return types.SimpleNamespace(team_id=team_id, user_id=user_id, is_private=is_private)


class TestCanAccessJob(unittest.IsolatedAsyncioTestCase):
    async def test_team_job_allows_active_member(self):
        db = FakeSession(member_exists=True)
        job = _job(team_id=uuid4())
        self.assertTrue(await access.can_access_job(db, job, uuid4()))

    async def test_team_job_blocks_non_member(self):
        db = FakeSession(member_exists=False)
        job = _job(team_id=uuid4())
        self.assertFalse(await access.can_access_job(db, job, uuid4()))

    async def test_team_job_blocks_anonymous(self):
        db = FakeSession(member_exists=True)
        job = _job(team_id=uuid4())
        ## 익명 사용자는 멤버십 질의 없이 즉시 차단되어야 한다.
        self.assertFalse(await access.can_access_job(db, job, None))
        self.assertEqual(db.executed, 0)

    async def test_private_job_owner_only(self):
        db = FakeSession(member_exists=False)
        owner = uuid4()
        job = _job(user_id=owner)
        self.assertTrue(await access.can_access_job(db, job, owner))
        self.assertFalse(await access.can_access_job(db, job, uuid4()))
        self.assertFalse(await access.can_access_job(db, job, None))

    async def test_legacy_public_job_readable(self):
        db = FakeSession(member_exists=False)
        job = _job(is_private=False)
        self.assertTrue(await access.can_access_job(db, job, None))

    async def test_user_has_team_access_requires_ids(self):
        db = FakeSession(member_exists=True)
        self.assertFalse(await access.user_has_team_access(db, None, uuid4()))
        self.assertFalse(await access.user_has_team_access(db, uuid4(), None))


class TestResolveVisibility(unittest.IsolatedAsyncioTestCase):
    def _service(self, has_team_access: bool):
        service = AnalysisService.__new__(AnalysisService)
        service.repository = types.SimpleNamespace(
            user_has_team_access=AsyncMock(return_value=has_team_access)
        )
        return service

    async def test_private_requires_auth(self):
        service = self._service(True)
        with self.assertRaises(CodeMapException) as ctx:
            await service._resolve_visibility("private", None, None)
        self.assertEqual(ctx.exception.error_code, "PRIVATE_REQUIRES_AUTH")

    async def test_private_ok_with_user(self):
        service = self._service(True)
        team_id, is_private = await service._resolve_visibility("private", None, uuid4())
        self.assertIsNone(team_id)
        self.assertTrue(is_private)

    async def test_team_requires_team_id(self):
        service = self._service(True)
        with self.assertRaises(CodeMapException) as ctx:
            await service._resolve_visibility("team", None, uuid4())
        self.assertEqual(ctx.exception.error_code, "TEAM_ID_REQUIRED")

    async def test_team_denied_for_non_member(self):
        service = self._service(False)
        with self.assertRaises(CodeMapException) as ctx:
            await service._resolve_visibility("team", uuid4(), uuid4())
        self.assertEqual(ctx.exception.error_code, "TEAM_ACCESS_DENIED")

    async def test_team_ok_for_member(self):
        team = uuid4()
        service = self._service(True)
        team_id, is_private = await service._resolve_visibility("team", team, uuid4())
        self.assertEqual(team_id, team)
        self.assertFalse(is_private)


if __name__ == "__main__":
    unittest.main()
