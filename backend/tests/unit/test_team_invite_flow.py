import types
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from app.infra.auth import get_current_user
from app.infra.database import get_db
from app.team.router import invite_router, router as team_router

from ._helpers import FakeResult, FakeSession, client_with_router, member, user


TEAM_ID = uuid.uuid4()
OWNER_ID = uuid.uuid4()
MEMBER_ID = uuid.uuid4()
INVITE_ID = uuid.uuid4()


def invite(*, email="member@example.com", status="pending", expires_at=None):
    return types.SimpleNamespace(
        id=INVITE_ID,
        team_id=TEAM_ID,
        email=email,
        invited_by_user_id=OWNER_ID,
        role="member",
        status=status,
        expires_at=expires_at or datetime.now(timezone.utc) + timedelta(days=1),
        created_at=datetime.now(timezone.utc),
    )


def team():
    return types.SimpleNamespace(id=TEAM_ID, name="Core Team")


def inviter():
    return types.SimpleNamespace(id=OWNER_ID, email="owner@example.com")


def make_client(results, *, current=None):
    session = FakeSession(results)
    client = client_with_router(
        team_router,
        invite_router,
        overrides={
            get_db: lambda: session,
            get_current_user: lambda: current or user(OWNER_ID, "owner@example.com"),
        },
    )
    return client, session


class TeamInviteFlowTests(unittest.TestCase):
    def test_owner_can_create_pending_invite(self):
        client, _ = make_client([
            FakeResult(value=member(TEAM_ID, OWNER_ID, role="owner")),
            FakeResult(value=None),
            FakeResult(value=None),
        ])

        resp = client.post(f"/api/teams/{TEAM_ID}/invites", json={"email": "New@Example.com"})

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["email"], "new@example.com")
        self.assertEqual(resp.json()["status"], "pending")

    def test_create_invite_owner_only(self):
        client, _ = make_client([FakeResult(value=member(TEAM_ID, MEMBER_ID))])

        resp = client.post(f"/api/teams/{TEAM_ID}/invites", json={"email": "x@example.com"})

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "TEAM_OWNER_REQUIRED")

    def test_list_my_invites_filters_pending_email_and_expiry(self):
        pending = invite(email="me@example.com")
        expired = invite(email="me@example.com", expires_at=datetime.now(timezone.utc) - timedelta(days=1))
        client, _ = make_client([
            FakeResult(rows=[(pending, team(), inviter()), (expired, team(), inviter())])
        ], current=user(MEMBER_ID, "me@example.com"))

        resp = client.get("/api/team-invites")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()["invites"]), 1)
        self.assertEqual(resp.json()["invites"][0]["invitedByEmail"], "owner@example.com")

    def test_accept_invite_email_mismatch_is_hidden(self):
        client, _ = make_client(
            [FakeResult(value=invite(email="other@example.com"))],
            current=user(MEMBER_ID, "me@example.com"),
        )

        resp = client.post(f"/api/team-invites/{INVITE_ID}/accept")

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.json()["detail"], "TEAM_INVITE_NOT_FOUND")

    def test_accept_expired_invite_returns_409(self):
        expired = invite(email="me@example.com", expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        client, _ = make_client([FakeResult(value=expired)], current=user(MEMBER_ID, "me@example.com"))

        resp = client.post(f"/api/team-invites/{INVITE_ID}/accept")

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"], "TEAM_INVITE_EXPIRED")
        self.assertEqual(expired.status, "expired")

    def test_decline_non_pending_invite_returns_409(self):
        client, _ = make_client(
            [FakeResult(value=invite(email="me@example.com", status="accepted"))],
            current=user(MEMBER_ID, "me@example.com"),
        )

        resp = client.post(f"/api/team-invites/{INVITE_ID}/decline")

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"], "TEAM_INVITE_ALREADY_USED")

    def test_cancelled_invite_cannot_be_accepted(self):
        client, _ = make_client(
            [FakeResult(value=invite(email="me@example.com", status="cancelled"))],
            current=user(MEMBER_ID, "me@example.com"),
        )

        resp = client.post(f"/api/team-invites/{INVITE_ID}/accept")

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.json()["detail"], "TEAM_INVITE_ALREADY_USED")


if __name__ == "__main__":
    unittest.main()
