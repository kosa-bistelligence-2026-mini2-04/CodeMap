"""
G4: 팀 라우터 HTTP 통합 테스트 (권한/가드 분기)

team 라우터는 서비스 계층 없이 db를 직접 쓰므로, get_db를 프로그래머블
fake AsyncSession으로 override하고 get_current_user를 고정해 HTTP 계약을
검증한다. (실 DB 불필요 — 권한/가드 분기에 집중)
"""

import types
import unittest
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.team.router import router as team_router
from app.team.router import invite_router
from app.infra.database import get_db
from app.infra.auth import get_current_user


# ──────────────────────────────────────────────
# 프로그래머블 fake 세션
# ──────────────────────────────────────────────
class _Scalars:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeResult:
    def __init__(self, value=None, rows=None):
        self._value = value
        self._rows = rows

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        rows = self._rows if self._rows is not None else ([] if self._value is None else [self._value])
        return _Scalars(rows)

    def all(self):
        return self._rows or []


class FakeSession:
    def __init__(self, results):
        self._queue = list(results)
        self.commits = 0

    async def execute(self, *_args, **_kwargs):
        return self._queue.pop(0) if self._queue else FakeResult()

    async def commit(self):
        self.commits += 1

    async def refresh(self, *_args, **_kwargs):
        pass

    def add(self, *_args, **_kwargs):
        pass

    async def flush(self):
        pass


TEAM_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
OTHER_ID = uuid.uuid4()
INVITE_ID = uuid.uuid4()


def _member(role="member", status="active", user_id=None):
    return types.SimpleNamespace(
        id=uuid.uuid4(),
        team_id=TEAM_ID,
        user_id=user_id or USER_ID,
        role=role,
        status=status,
        created_at=None,
    )


def _client(results, *, sub=USER_ID, email="me@example.com"):
    app = FastAPI()
    app.include_router(team_router)
    app.include_router(invite_router)
    session = FakeSession(results)
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_current_user] = lambda: {"sub": str(sub), "email": email}
    return TestClient(app), session


class TeamPermissionTests(unittest.TestCase):
    def test_create_invite_requires_owner(self):
        ## _require_member: 1 select → 비-owner member
        client, _ = _client([FakeResult(value=_member(role="member"))])
        resp = client.post(f"/api/teams/{TEAM_ID}/invites", json={"email": "x@e.com"})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "TEAM_OWNER_REQUIRED")

    def test_remove_member_blocks_self(self):
        ## owner이지만 자기 자신 추방 시도 → 400
        client, _ = _client([FakeResult(value=_member(role="owner"))])
        resp = client.delete(f"/api/teams/{TEAM_ID}/members/{USER_ID}")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["detail"], "CANNOT_REMOVE_SELF")

    def test_remove_member_requires_owner(self):
        client, _ = _client([FakeResult(value=_member(role="member"))])
        resp = client.delete(f"/api/teams/{TEAM_ID}/members/{OTHER_ID}")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "TEAM_OWNER_REQUIRED")

    def test_leave_team_blocks_last_owner(self):
        ## _require_member(owner) → _count_active_owners(1명) → 409
        client, _ = _client([
            FakeResult(value=_member(role="owner")),
            FakeResult(rows=[_member(role="owner")]),
        ])
        resp = client.post(f"/api/teams/{TEAM_ID}/leave")
        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"], "LAST_OWNER_CANNOT_LEAVE")

    def test_accept_invite_email_must_match(self):
        ## 초대 이메일이 로그인 이메일과 다르면 존재 은닉(404)
        invite = types.SimpleNamespace(
            id=INVITE_ID, team_id=TEAM_ID, email="someone-else@example.com",
            status="pending", role="member", expires_at=None,
        )
        client, _ = _client([FakeResult(value=invite)], email="me@example.com")
        resp = client.post(f"/api/team-invites/{INVITE_ID}/accept")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "TEAM_INVITE_NOT_FOUND")

    def test_cancel_invite_requires_owner(self):
        ## 초대 로드(1) → _require_member(owner_only) 비-owner(2) → 403
        invite = types.SimpleNamespace(
            id=INVITE_ID, team_id=TEAM_ID, email="x@e.com",
            status="pending", role="member", expires_at=None,
        )
        client, _ = _client([
            FakeResult(value=invite),
            FakeResult(value=_member(role="member")),
        ])
        resp = client.post(f"/api/team-invites/{INVITE_ID}/cancel")
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "TEAM_OWNER_REQUIRED")

    def test_list_my_invites_empty_ok(self):
        client, _ = _client([FakeResult(rows=[])])
        resp = client.get("/api/team-invites")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["invites"], [])


if __name__ == "__main__":
    unittest.main()
