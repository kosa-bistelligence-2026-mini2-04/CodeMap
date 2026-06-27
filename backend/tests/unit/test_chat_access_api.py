import types
import unittest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

from app.chat.router import router as chat_router
from app.infra.auth import get_current_user
from app.infra.database import get_db

from ._helpers import FakeSession, client_with_router, user


REPO_ID = uuid.uuid4()
THREAD_ID = uuid.uuid4()
USER_ID = uuid.uuid4()


class FakeChatService:
    mode = "ok"

    def __init__(self, *_args, **_kwargs):
        pass

    async def prepare_run_context(self, repo_id, request, current_user_id=None):
        if self.mode == "forbidden":
            raise PermissionError("TEAM_ACCESS_DENIED")
        if self.mode == "missing":
            raise ValueError("Repository not found")
        return (
            types.SimpleNamespace(id=repo_id, repo_name="codemap"),
            "repo",
            "/tmp/codemap",
        )


class FakeChatRepository:
    def __init__(self, *_args, **_kwargs):
        pass

    async def list_threads(self, repo_id):
        return [
            types.SimpleNamespace(
                id=THREAD_ID,
                repo_id=repo_id,
                title="Thread",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ]

    async def list_messages(self, repo_id, thread_id):
        return [
            types.SimpleNamespace(
                id=uuid.uuid4(),
                role="assistant",
                content="answer",
                mode="repo",
                references=[],
                created_at=datetime.now(timezone.utc),
            )
        ]


def make_client():
    return client_with_router(
        chat_router,
        overrides={
            get_db: lambda: FakeSession(),
            get_current_user: lambda: user(USER_ID),
        },
    )


class ChatAccessApiTests(unittest.TestCase):
    def setUp(self):
        FakeChatService.mode = "ok"

    def test_create_run_forbidden_private_or_team_returns_403(self):
        FakeChatService.mode = "forbidden"
        client = make_client()

        with patch("app.chat.router.RepositoryChatService", FakeChatService):
            resp = client.post(f"/api/chat/{REPO_ID}/runs", json={"question": "hi"})

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.json()["detail"], "TEAM_ACCESS_DENIED")

    def test_create_run_authorized_returns_202(self):
        client = make_client()

        with patch("app.chat.router.RepositoryChatService", FakeChatService):
            resp = client.post(f"/api/chat/{REPO_ID}/runs", json={"question": "hi"})

        self.assertEqual(resp.status_code, 202)
        self.assertEqual(resp.json()["data"]["status"], "queued")

    def test_threads_forbidden_returns_403(self):
        FakeChatService.mode = "forbidden"
        client = make_client()

        with patch("app.chat.router.RepositoryChatService", FakeChatService):
            resp = client.get(f"/api/chat/{REPO_ID}/threads")

        self.assertEqual(resp.status_code, 403)

    def test_threads_authorized_lists_threads(self):
        client = make_client()

        with patch("app.chat.router.RepositoryChatService", FakeChatService):
            with patch("app.chat.router.ChatRepository", FakeChatRepository):
                resp = client.get(f"/api/chat/{REPO_ID}/threads")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["items"][0]["repoId"], str(REPO_ID))

    def test_thread_detail_authorized_lists_messages(self):
        client = make_client()

        with patch("app.chat.router.RepositoryChatService", FakeChatService):
            with patch("app.chat.router.ChatRepository", FakeChatRepository):
                resp = client.get(f"/api/chat/{REPO_ID}/threads/{THREAD_ID}")

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["items"][0]["content"], "answer")


if __name__ == "__main__":
    unittest.main()
