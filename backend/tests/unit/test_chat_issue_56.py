"""Regression tests for chat orphan-message and context-injection handling."""

from __future__ import annotations

import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
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


class _FakeDB:
    def __init__(self):
        self.commits = 0
        self.flushes = 0

    async def flush(self):
        self.flushes += 1

    async def commit(self):
        self.commits += 1


async def _async_value(value):
    return value


class TestChatAnswerSafety(unittest.IsolatedAsyncioTestCase):
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


if __name__ == "__main__":
    unittest.main()
