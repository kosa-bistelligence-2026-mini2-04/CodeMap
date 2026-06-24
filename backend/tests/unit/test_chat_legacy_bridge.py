"""Legacy chat bridge compatibility tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))


class TestChatLegacyRequest(unittest.TestCase):
    def test_legacy_request_maps_frontend_payload_to_run_request(self):
        from app.chat.schemas import ChatLegacyRequest

        thread_id = uuid4()
        legacy = ChatLegacyRequest(
            message="로그인 흐름 알려줘",
            mode="quick",
            threadId=thread_id,
        )

        run_request = legacy.to_run_request()

        self.assertEqual(run_request.question, "로그인 흐름 알려줘")
        self.assertEqual(run_request.mode, "lite")
        self.assertEqual(run_request.sessionId, thread_id)


class TestLegacyBridgeEvents(unittest.TestCase):
    def test_answer_delta_maps_to_existing_content_event(self):
        from app.chat.router import _legacy_graph_event_payload

        payload = _legacy_graph_event_payload({
            "type": "answer_delta",
            "content": "부분 응답",
        })

        self.assertEqual(payload, {"type": "content", "content": "부분 응답"})

    def test_worker_results_map_to_deduplicated_references(self):
        from app.chat.router import _references_from_worker_results

        references = _references_from_worker_results([
            {"path": "app/auth.py", "lineStart": 10, "snippet": "def login(): pass"},
            {"path": "app/auth.py", "lineStart": 10, "snippet": "duplicate"},
            {"path": None, "lineStart": None, "snippet": "search only"},
        ])

        self.assertEqual(len(references), 1)
        self.assertEqual(references[0]["file"], "app/auth.py")
        self.assertEqual(references[0]["line"], 10)


if __name__ == "__main__":
    unittest.main()
