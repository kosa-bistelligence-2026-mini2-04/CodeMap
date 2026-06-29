import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))


class _FakeSettings:
    class _Secret:
        def __init__(self, value: str):
            self.value = value
        def get_secret_value(self) -> str:
            return self.value

    OPENAI_API_KEY = _Secret("sk-test")
    OPENAI_MODEL = "gpt-4o-mini"


class TestFinalAnswerEvidenceGating(unittest.IsolatedAsyncioTestCase):
    async def test_evidence_rule_is_excluded_when_evidence_exists(self):
        from app.chat.final_answer_agent import stream_final_answer

        captured: dict = {}

        class FakeLLM:
            async def astream(self, messages):
                captured["messages"] = messages
                yield types.SimpleNamespace(content="ok")

        def fake_create_final_answer_llm(**kwargs):
            return FakeLLM()

        compact_context = {
            "groupedByFile": {
                "app/auth.py": [{
                    "lineStart": 1,
                    "snippet": "def login(): pass",
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
                    user_query="where is login?",
                    compact_context=compact_context,
                    worker_results=[],
                )
            ]

        self.assertEqual(events, [{"type": "answer_delta", "content": "ok"}])
        system_prompt = captured["messages"][0].content
        self.assertNotIn("현재 저장소에서 질문과 관련된 코드를 찾지 못했습니다", system_prompt)

    async def test_evidence_rule_is_included_when_evidence_is_empty(self):
        from app.chat.final_answer_agent import stream_final_answer

        captured: dict = {}

        class FakeLLM:
            async def astream(self, messages):
                captured["messages"] = messages
                yield types.SimpleNamespace(content="ok")

        def fake_create_final_answer_llm(**kwargs):
            return FakeLLM()

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
                    user_query="what is foo?",
                    compact_context={"groupedByFile": {}},
                    worker_results=[],
                )
            ]

        self.assertEqual(events, [{"type": "answer_delta", "content": "ok"}])
        system_prompt = captured["messages"][0].content
        self.assertIn("현재 저장소에서 질문과 관련된 코드를 찾지 못했습니다", system_prompt)

    async def test_no_evidence_rule_is_included_when_evaluator_marks_irrelevant_evidence(self):
        from app.chat.final_answer_agent import stream_final_answer

        captured: dict = {}

        class FakeLLM:
            async def astream(self, messages):
                captured["messages"] = messages
                yield types.SimpleNamespace(content="ok")

        def fake_create_final_answer_llm(**kwargs):
            return FakeLLM()

        compact_context = {
            "groupedByFile": {
                "app/account.py": [{
                    "lineStart": 10,
                    "snippet": "def delete_account(): pass",
                    "metadata": {"worker": "semantic"},
                }]
            },
            "evaluatorDecision": {
                "sufficient": False,
                "missingInfo": ["로그인 처리 흐름"],
                "nextPlanHint": "login auth",
                "reason": "질문과 직접 관련 없는 근거입니다.",
                "confidence": 0.35,
            },
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
                    user_query="where is login?",
                    compact_context=compact_context,
                    worker_results=[],
                )
            ]

        self.assertEqual(events, [{"type": "answer_delta", "content": "ok"}])
        system_prompt = captured["messages"][0].content
        self.assertIn("현재 저장소에서 질문과 관련된 코드를 찾지 못했습니다", system_prompt)

if __name__ == "__main__":
    unittest.main()
