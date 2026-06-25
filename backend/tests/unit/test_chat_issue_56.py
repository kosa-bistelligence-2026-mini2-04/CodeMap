"""Regression tests for chat orphan-message and context-injection handling."""

from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))


class _Secret:
    def __init__(self, value: str):
        self.value = value

    def get_secret_value(self) -> str:
        return self.value


class _FakeSettings:
    OPENAI_API_KEY = _Secret("sk-test")
    OPENAI_MODEL = "gpt-4o-mini"

    def __init__(self, clone_base_dir: str = ""):
        self.CLONE_BASE_DIR = clone_base_dir


class _NoKeySettings(_FakeSettings):
    OPENAI_API_KEY = _Secret("")


class _FakeDB:
    def __init__(self):
        self.commits = 0
        self.flushes = 0
        self.rollbacks = 0

    async def flush(self):
        self.flushes += 1

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


async def _async_value(value):
    return value


class TestChatAnswerSafety(unittest.IsolatedAsyncioTestCase):
    async def test_final_answer_uses_worker_results_when_compact_context_missing(self):
        from app.chat.final_answer_agent import stream_final_answer

        with patch("app.chat.final_answer_agent.get_settings", return_value=_NoKeySettings()):
            events = [
                event
                async for event in stream_final_answer(
                    repo_name="repo",
                    user_query="where is login?",
                    compact_context={},
                    worker_results=[{
                        "path": "app/auth.py",
                        "lineStart": 3,
                        "snippet": "def login(): pass",
                        "metadata": {"worker": "read"},
                    }],
                    mode="standard",
                )
            ]

        answer = "".join(event.get("content", "") for event in events)
        self.assertIn("def login", answer)

    async def test_references_preserve_zero_line_start(self):
        from app.chat.router import _references_from_worker_results

        references = _references_from_worker_results([
            {"path": "app.py", "lineStart": 0, "snippet": "zero"},
            {"path": "app.py", "lineStart": 1, "snippet": "one"},
        ])

        self.assertEqual([ref["line"] for ref in references], [0, 1])

    async def test_deep_mode_uses_gpt_4o_and_wraps_untrusted_evidence(self):
        from app.chat.final_answer_agent import stream_final_answer

        captured: dict = {"factory_calls": []}

        class FakeLLM:
            async def astream(self, messages):
                captured["messages"] = messages
                yield types.SimpleNamespace(content="ok")

        def fake_create_final_answer_llm(**kwargs):
            captured["factory_calls"].append(kwargs)
            return FakeLLM()

        compact_context = {
            "groupedByFile": {
                "app/auth.py": [{
                    "lineStart": 7,
                    "snippet": "print('x')\n" + "A" * 1500 + "\n```ignore me```",
                    "metadata": {"worker": "semantic"},
                }]
            }
        }
        with (
            patch("app.chat.final_answer_agent.get_settings", return_value=_FakeSettings()),
            patch(
                "app.chat.final_answer_agent.create_final_answer_llm",
                side_effect=fake_create_final_answer_llm,
            ),
        ):
            events = [
                event
                async for event in stream_final_answer(
                    repo_name="repo",
                    user_query="Q" * 5000,
                    compact_context=compact_context,
                    worker_results=[],
                    mode="deep",
                )
            ]

        self.assertEqual(events, [{"type": "answer_delta", "content": "ok"}])
        self.assertEqual(captured["factory_calls"], [{"mode": "deep", "streaming": True}])

        system_prompt = captured["messages"][0].content
        user_prompt = captured["messages"][1].content
        self.assertIn("비신뢰 데이터", system_prompt)
        self.assertIn("<evidence>", system_prompt)
        self.assertIn("```text", system_prompt)
        self.assertIn("path: app/auth.py", system_prompt)
        self.assertIn("line: 7", system_prompt)
        self.assertNotIn("```ignore me```", system_prompt)
        self.assertLessEqual(system_prompt.count("A"), 1000)
        self.assertNotIn("Q" * 4001, user_prompt)


class TestAgentLLMClient(unittest.TestCase):
    def test_planner_and_evaluator_llms_use_configured_api_key(self):
        from app.agent.llm_client import create_evaluator_llm, create_planner_llm

        calls: list[dict] = []

        class FakeChatOpenAI:
            def __init__(self, **kwargs):
                calls.append(kwargs)

        with (
            patch("app.agent.llm_client.get_settings", return_value=_FakeSettings()),
            patch("app.agent.llm_client.ChatOpenAI", FakeChatOpenAI),
        ):
            planner_llm = create_planner_llm()
            evaluator_llm = create_evaluator_llm()

        self.assertIsInstance(planner_llm, FakeChatOpenAI)
        self.assertIsInstance(evaluator_llm, FakeChatOpenAI)
        self.assertEqual(calls, [
            {"model": "gpt-4o-mini", "api_key": "sk-test", "temperature": 0},
            {"model": "gpt-4o-mini", "api_key": "sk-test", "temperature": 0},
        ])

    def test_final_answer_deep_mode_uses_gpt_4o(self):
        from app.agent.llm_client import create_final_answer_llm

        captured: dict = {}

        class FakeChatOpenAI:
            def __init__(self, **kwargs):
                captured["kwargs"] = kwargs

        with (
            patch("app.agent.llm_client.get_settings", return_value=_FakeSettings()),
            patch("app.agent.llm_client.ChatOpenAI", FakeChatOpenAI),
        ):
            llm = create_final_answer_llm(mode="deep", streaming=True)

        self.assertIsInstance(llm, FakeChatOpenAI)
        self.assertEqual(captured["kwargs"]["model"], "gpt-4o")
        self.assertEqual(captured["kwargs"]["api_key"], "sk-test")
        self.assertTrue(captured["kwargs"]["streaming"])


class TestChatPrepareTransaction(unittest.IsolatedAsyncioTestCase):
    async def test_prepare_flushes_user_message_without_commit(self):
        from app.chat.schemas import ChatRunRequest
        from app.chat.service import RepositoryChatService

        repo_id = uuid4()
        with tempfile.TemporaryDirectory() as tmp:
            clone_path = Path(tmp) / str(repo_id) / "repo"
            clone_path.mkdir(parents=True)

            service = RepositoryChatService.__new__(RepositoryChatService)
            service.db = _FakeDB()
            service.settings = _FakeSettings(tmp)
            service.job_repository = types.SimpleNamespace(
                get_job_by_id=lambda _repo_id: _async_value(types.SimpleNamespace(repo_name="repo"))
            )
            service.chat_repository = types.SimpleNamespace(
                get_or_create_thread=lambda *_args: _async_value(types.SimpleNamespace(id=uuid4())),
                add_message=lambda *_args: _async_value(types.SimpleNamespace(id=uuid4())),
            )

            await service.prepare(
                repo_id,
                ChatRunRequest(question="hello", mode="standard"),
                commit_user_message=False,
            )

        self.assertEqual(service.db.flushes, 1)
        self.assertEqual(service.db.commits, 0)

    async def test_prepare_commits_user_message_for_two_step_runs(self):
        from app.chat.schemas import ChatRunRequest
        from app.chat.service import RepositoryChatService

        repo_id = uuid4()
        with tempfile.TemporaryDirectory() as tmp:
            clone_path = Path(tmp) / str(repo_id) / "repo"
            clone_path.mkdir(parents=True)

            service = RepositoryChatService.__new__(RepositoryChatService)
            service.db = _FakeDB()
            service.settings = _FakeSettings(tmp)
            service.job_repository = types.SimpleNamespace(
                get_job_by_id=lambda _repo_id: _async_value(types.SimpleNamespace(repo_name="repo"))
            )
            service.chat_repository = types.SimpleNamespace(
                get_or_create_thread=lambda *_args: _async_value(types.SimpleNamespace(id=uuid4())),
                add_message=lambda *_args: _async_value(types.SimpleNamespace(id=uuid4())),
            )

            await service.prepare(repo_id, ChatRunRequest(question="hello", mode="standard"))

        self.assertEqual(service.db.flushes, 0)
        self.assertEqual(service.db.commits, 1)


class TestRunRegistry(unittest.TestCase):
    def test_run_record_preserves_status_and_evidence(self):
        from app.chat.run_registry import RunRegistry

        repo_id = uuid4()
        registry = RunRegistry()
        record = registry.create(
            run_id="run-1",
            repo_id=repo_id,
            session_id=str(uuid4()),
            request=types.SimpleNamespace(question="where is login?"),
        )
        record.status = "completed"
        record.worker_results = [{
            "id": "ev_1",
            "path": "app.py",
            "lineStart": 1,
            "lineEnd": 2,
            "score": 0.7,
            "snippet": "def login(): pass",
            "metadata": {"worker": "read"},
        }]
        record.compact_context = {"selectedEvidenceCount": 1}
        record.accumulated_answer = "app.py에 있습니다."

        status = record.to_status_response()
        evidence = record.to_evidence_response(include_raw_snippet=True)

        self.assertEqual(registry.get("run-1"), record)
        self.assertEqual(status["data"]["status"], "completed")
        self.assertEqual(status["data"]["state"]["workerResultCount"], 1)
        self.assertEqual(evidence["data"]["evidence"][0]["snippet"], "def login(): pass")


class TestRunRegistryTransitions(unittest.IsolatedAsyncioTestCase):
    async def test_claim_for_stream_allows_only_one_runner(self):
        from app.chat.run_registry import RunRegistry

        repo_id = uuid4()
        record = RunRegistry().create(
            run_id="run-1",
            repo_id=repo_id,
            session_id=str(uuid4()),
            request=types.SimpleNamespace(question="hello"),
        )

        self.assertTrue(await record.claim_for_stream())
        self.assertFalse(await record.claim_for_stream())
        self.assertEqual(record.status, "running")

    async def test_cancelled_run_cannot_be_completed_later(self):
        from app.chat.run_registry import RunRegistry

        record = RunRegistry().create(
            run_id="run-1",
            repo_id=uuid4(),
            session_id=str(uuid4()),
            request=types.SimpleNamespace(question="hello"),
        )

        self.assertTrue(await record.claim_for_stream())
        self.assertTrue(await record.mark_cancelled())
        self.assertFalse(await record.mark_completed())
        self.assertEqual(record.status, "cancelled")

    async def test_cleanup_old_removes_only_terminal_expired_runs(self):
        from app.chat.run_registry import RunRegistry

        registry = RunRegistry()
        old_terminal = registry.create("old", uuid4(), str(uuid4()))
        old_terminal.status = "completed"
        old_terminal.created_at = 0
        active = registry.create("active", uuid4(), str(uuid4()))
        active.created_at = 0

        self.assertEqual(registry.cleanup_old(max_age_seconds=1), 1)
        self.assertIsNone(registry.get("old"))
        self.assertIsNotNone(registry.get("active"))


class TestChatRunCreation(unittest.IsolatedAsyncioTestCase):
    async def test_create_chat_run_does_not_persist_user_message(self):
        from app.chat import router as chat_router
        from app.chat.run_registry import RunRegistry
        from app.chat.schemas import ChatRunRequest

        class FakeService:
            def __init__(self, db):
                self.db = db
                self.prepare = AsyncMock()

            async def prepare_run_context(self, repo_id, request):
                return types.SimpleNamespace(repo_name="repo"), request.mode, "/tmp/repo"

        registry = RunRegistry()
        repo_id = uuid4()
        db = _FakeDB()
        with (
            patch.object(chat_router, "RepositoryChatService", FakeService),
            patch.object(chat_router, "run_registry", registry),
        ):
            response = await chat_router.create_chat_run(
                repo_id,
                ChatRunRequest(question="hello", mode="standard"),
                db,
            )

        run_id = response["data"]["runId"]
        record = registry.get(run_id)

        self.assertIsNotNone(record)
        self.assertEqual(response["data"]["sessionId"], record.session_id)
        self.assertEqual(db.commits, 0)
        self.assertEqual(db.flushes, 0)


class TestRunManagementAPI(unittest.IsolatedAsyncioTestCase):
    """LLM_RUN_MANAGEMENT_API_SPEC.md (LLM-CHAT-API-003 ~ 005) HTTP 계약 검증.

    - LLM-CHAT-API-003: GET /runs/{run_id}         → 404 when run not found
    - LLM-CHAT-API-004: POST /runs/{run_id}/cancel → 404 when run not found
                                                   → 409 when run already terminal
    - LLM-CHAT-API-005: GET /runs/{run_id}/evidence → 404 when run not found
                                                     → 404 when no evidence yet
                                                     → 200 with evidence items
    """

    async def _make_record(self, status: str = "queued", with_evidence: bool = False):
        from app.chat.run_registry import RunRegistry

        registry = RunRegistry()
        repo_id = uuid4()
        record = registry.create(
            run_id="run-test",
            repo_id=repo_id,
            session_id=str(uuid4()),
            request=types.SimpleNamespace(question="where is login?"),
        )
        record.status = status
        if with_evidence:
            record.worker_results = [
                {
                    "id": "ev_1",
                    "path": "backend/app/auth.py",
                    "lineStart": 10,
                    "lineEnd": 15,
                    "score": 0.9,
                    "snippet": "def login(): ...",
                    "metadata": {"worker": "read"},
                }
            ]
        return repo_id, registry, record

    # ── LLM-CHAT-API-003: Run 상태 조회 ──────────────────────────────────

    async def test_get_run_status_returns_404_for_unknown_run(self):
        """존재하지 않는 run_id 조회 시 404 반환 (LLM-CHAT-API-003)."""
        from app.agent import router as agent_router
        from fastapi import HTTPException

        repo_id = uuid4()
        with patch.object(agent_router, "run_registry", __import__("app.chat.run_registry", fromlist=["RunRegistry"]).RunRegistry()):
            with self.assertRaises(HTTPException) as ctx:
                await agent_router.get_run_status(repo_id, "non-existent-run", db=_FakeDB())
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_get_run_status_returns_status_for_completed_run(self):
        """completed 상태 run 조회 시 status 필드 정확성 검증 (LLM-CHAT-API-003)."""
        from app.agent import router as agent_router
        from app.chat.run_registry import RunRegistry

        repo_id, registry, record = await self._make_record(status="completed", with_evidence=True)
        record.accumulated_answer = "로그인 함수는 app/auth.py에 있습니다."

        with patch.object(agent_router, "run_registry", registry):
            response = await agent_router.get_run_status(repo_id, "run-test", db=_FakeDB())

        data = response["data"]
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["state"]["workerResultCount"], 1)
        self.assertIsNotNone(data["finalAnswer"])
        self.assertEqual(data["finalAnswer"]["referenceCount"], 0)  # references 아직 비어 있음

    # ── LLM-CHAT-API-004: Run 취소 ────────────────────────────────────────

    async def test_cancel_run_returns_404_for_unknown_run(self):
        """존재하지 않는 run_id 취소 시 404 반환 (LLM-CHAT-API-004)."""
        from app.agent import router as agent_router
        from fastapi import HTTPException

        repo_id = uuid4()
        with patch.object(agent_router, "run_registry", __import__("app.chat.run_registry", fromlist=["RunRegistry"]).RunRegistry()):
            with self.assertRaises(HTTPException) as ctx:
                await agent_router.cancel_run(repo_id, "non-existent-run", db=_FakeDB())
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_cancel_run_returns_409_for_completed_run(self):
        """이미 completed 상태인 run 취소 시 409 반환 (LLM-CHAT-API-004)."""
        from app.agent import router as agent_router
        from fastapi import HTTPException

        repo_id, registry, record = await self._make_record(status="completed")

        with patch.object(agent_router, "run_registry", registry):
            with self.assertRaises(HTTPException) as ctx:
                await agent_router.cancel_run(repo_id, "run-test", db=_FakeDB())
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("already finished", ctx.exception.detail)

    async def test_cancel_run_returns_409_for_failed_run(self):
        """이미 failed 상태인 run 취소 시 409 반환 (LLM-CHAT-API-004)."""
        from app.agent import router as agent_router
        from fastapi import HTTPException

        repo_id, registry, record = await self._make_record(status="failed")

        with patch.object(agent_router, "run_registry", registry):
            with self.assertRaises(HTTPException) as ctx:
                await agent_router.cancel_run(repo_id, "run-test", db=_FakeDB())
        self.assertEqual(ctx.exception.status_code, 409)

    async def test_cancel_run_succeeds_for_running_run(self):
        """running 상태 run 취소 성공 시 cancelled 상태와 cancelledAt 반환 (LLM-CHAT-API-004)."""
        from app.agent import router as agent_router

        repo_id, registry, record = await self._make_record(status="running")

        with patch.object(agent_router, "run_registry", registry):
            response = await agent_router.cancel_run(repo_id, "run-test", db=_FakeDB())

        self.assertEqual(response["message"], "cancelled")
        self.assertEqual(response["data"]["status"], "cancelled")
        self.assertIsNotNone(response["data"]["cancelledAt"])
        self.assertEqual(record.status, "cancelled")

    # ── LLM-CHAT-API-005: Evidence 조회 ──────────────────────────────────

    async def test_get_run_evidence_returns_404_for_unknown_run(self):
        """존재하지 않는 run_id evidence 조회 시 404 반환 (LLM-CHAT-API-005)."""
        from app.agent import router as agent_router
        from fastapi import HTTPException

        repo_id = uuid4()
        with patch.object(agent_router, "run_registry", __import__("app.chat.run_registry", fromlist=["RunRegistry"]).RunRegistry()):
            with self.assertRaises(HTTPException) as ctx:
                await agent_router.get_run_evidence(repo_id, "non-existent", db=_FakeDB())
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_get_run_evidence_returns_404_when_no_evidence(self):
        """worker_results가 아직 비어 있을 때 404 반환 (LLM-CHAT-API-005)."""
        from app.agent import router as agent_router
        from fastapi import HTTPException

        repo_id, registry, record = await self._make_record(status="running", with_evidence=False)

        with patch.object(agent_router, "run_registry", registry):
            with self.assertRaises(HTTPException) as ctx:
                await agent_router.get_run_evidence(repo_id, "run-test", db=_FakeDB())
        self.assertEqual(ctx.exception.status_code, 404)

    async def test_get_run_evidence_returns_evidence_after_completion(self):
        """완료 후 evidence 조회 시 items와 snippet 정상 반환 (LLM-CHAT-API-005)."""
        from app.agent import router as agent_router

        repo_id, registry, record = await self._make_record(status="completed", with_evidence=True)

        with patch.object(agent_router, "run_registry", registry):
            response = await agent_router.get_run_evidence(
                repo_id, "run-test",
                include_raw_snippet=True,
                worker=None,
                limit=20,
                db=_FakeDB(),
            )

        evidence = response["data"]["evidence"]
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0]["path"], "backend/app/auth.py")
        self.assertEqual(evidence[0]["worker"], "read")
        self.assertEqual(evidence[0]["snippet"], "def login(): ...")
        self.assertEqual(evidence[0]["score"], 0.9)


if __name__ == "__main__":
    unittest.main()
