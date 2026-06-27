import types
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient


class Scalars:
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
        return Scalars(rows)

    def all(self):
        return self._rows or []


class FakeSession:
    def __init__(self, results=None):
        self._queue = list(results or [])
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, *_args, **_kwargs):
        return self._queue.pop(0) if self._queue else FakeResult()

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1

    async def refresh(self, *_args, **_kwargs):
        pass

    async def flush(self):
        pass

    def add(self, obj, *_args, **_kwargs):
        if getattr(obj, "id", None) is None:
            obj.id = uuid.uuid4()
        if (
            obj.__class__.__name__ == "TeamInvite"
            and getattr(obj, "expires_at", None) is None
        ):
            obj.expires_at = (
                datetime.now(timezone.utc) + timedelta(days=7)
            )


class AsyncSessionFactory:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *_exc):
        return False


def user(sub=None, email="me@example.com"):
    return {"sub": str(sub or uuid.uuid4()), "email": email}


def member(team_id, user_id, *, role="member", status="active"):
    return types.SimpleNamespace(
        id=uuid.uuid4(),
        team_id=team_id,
        user_id=user_id,
        role=role,
        status=status,
        created_at=None,
    )


def client_with_router(*routers, overrides=None, exception_handlers=False):
    app = FastAPI()
    if exception_handlers:
        from app.common.exceptions import register_exception_handlers

        register_exception_handlers(app)
    for router in routers:
        app.include_router(router)
    for dep, value in (overrides or {}).items():
        app.dependency_overrides[dep] = value
    return TestClient(app)
