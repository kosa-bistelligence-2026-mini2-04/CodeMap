"""
Unit tests for agent_graph — Route Node 보안 로직 및 State 스키마 검증.

LLM 호출 없이 실행 가능한 결정론적 로직만 테스트합니다.
"""

from __future__ import annotations

import sys
import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# backend를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))


class TestCodeMapState(unittest.TestCase):
    """CodeMapState TypedDict 스키마 검증."""

    def test_state_instantiation(self):
        from app.agent_graph.state import CodeMapState, WorkerResult, AccessPlanItem
        state: CodeMapState = {
            "user_query": "로그인 코드 어디에 있어?",
            "repo_id": "test-repo",
            "clone_path": "/tmp/repo",
            "rewritten_query": "login authentication",
            "access_plan": [],
            "security_result": {"approved": [], "rejected": []},
            "worker_results": [],
            "compact_context": {},
            "final_answer": None,
        }
        self.assertEqual(state["user_query"], "로그인 코드 어디에 있어?")
        self.assertIsNone(state["final_answer"])

    def test_worker_result_structure(self):
        from app.agent_graph.state import WorkerResult
        r = WorkerResult(
            worker="search",
            tool="search_repository",
            query="login",
            content="def login(): ...",
            file_path="app/auth/service.py",
        )
        self.assertEqual(r["worker"], "search")
        self.assertEqual(r["file_path"], "app/auth/service.py")


class TestRouteNodeSecurity(unittest.TestCase):
    """Route Node 보안 로직 단위 테스트."""

    def _is_safe(self, path):
        from app.agent_graph.nodes.route_node import _is_safe_path
        return _is_safe_path(path)

    def test_safe_paths(self):
        self.assertTrue(self._is_safe(None))            # search: path 없음
        self.assertTrue(self._is_safe("app/auth"))      # 정상 경로
        self.assertTrue(self._is_safe("backend/app/chat/service.py"))

    def test_path_traversal_blocked(self):
        self.assertFalse(self._is_safe("../../../etc/passwd"))
        self.assertFalse(self._is_safe("../../secret"))
        self.assertFalse(self._is_safe("app/../../../root"))

    def test_absolute_path_blocked(self):
        self.assertFalse(self._is_safe("/etc/passwd"))
        self.assertFalse(self._is_safe("/root/.ssh/id_rsa"))

    def test_sensitive_files_blocked(self):
        self.assertFalse(self._is_safe(".env"))
        self.assertFalse(self._is_safe(".env.production"))
        self.assertFalse(self._is_safe("keys/id_rsa"))
        self.assertFalse(self._is_safe("config/secret.key"))
        self.assertFalse(self._is_safe("credentials.json"))
        # 대소문자 우회 시도
        self.assertFalse(self._is_safe(".ENV"))
        self.assertFalse(self._is_safe("Id_Rsa"))

    def test_route_node_returns_sends(self):
        """route_node가 Send 객체 리스트를 반환하는지 검증."""
        try:
            from langgraph.types import Send
            has_langgraph = True
        except ImportError:
            has_langgraph = False

        from app.agent_graph.nodes.route_node import route_node

        state = {
            "user_query": "test",
            "repo_id": "r1",
            "clone_path": "/tmp",
            "rewritten_query": "test",
            "access_plan": [
                {"tool": "search", "path": None, "query": "test", "scope": "chunk"},
                {"tool": "grep", "path": "app/", "query": "def login", "scope": "file"},
                {"tool": "read", "path": "../../../etc/passwd", "query": "", "scope": "file"},  # 차단
            ],
            "security_result": {"approved": [], "rejected": []},
            "worker_results": [],
            "compact_context": {},
            "final_answer": None,
        }

        if not has_langgraph:
            self.skipTest("langgraph 미설치 환경 — Send 반환 테스트 생략")

        sends = route_node(state)
        node_names = [s.node for s in sends]
        self.assertIn("search_worker", node_names)
        self.assertIn("grep_worker", node_names)
        self.assertNotIn("read_worker", node_names)  # 차단됨
        self.assertEqual(len(sends), 2)


class TestEvidenceAggregator(unittest.TestCase):
    """Evidence Aggregator 중복 제거 및 budget 제한 검증."""

    def test_deduplication(self):
        from app.agent_graph.nodes.evidence_aggregator import _deduplicate
        from app.agent_graph.state import WorkerResult

        r1 = WorkerResult(worker="search", tool="t", query="q",
                          content="same content", file_path="a.py")
        r2 = WorkerResult(worker="grep", tool="t", query="q",
                          content="same content", file_path="a.py")  # 중복
        r3 = WorkerResult(worker="read", tool="t", query="q",
                          content="different content", file_path="b.py")

        result = _deduplicate([r1, r2, r3])
        self.assertEqual(len(result), 2)  # r2는 중복 제거

    def test_aggregator_builds_compact_context(self):
        from app.agent_graph.nodes.evidence_aggregator import evidence_aggregator
        from app.agent_graph.state import WorkerResult

        state = {
            "user_query": "test",
            "repo_id": "r1",
            "clone_path": "/tmp",
            "rewritten_query": "test",
            "access_plan": [],
            "security_result": {"approved": [], "rejected": []},
            "worker_results": [
                WorkerResult(worker="search", tool="t", query="q",
                             content="code snippet here", file_path=None),
                WorkerResult(worker="read", tool="t", query="q",
                             content="def login(): pass", file_path="auth.py"),
            ],
            "compact_context": {},
            "final_answer": None,
        }
        result = evidence_aggregator(state)
        ctx = result["compact_context"]
        self.assertIn("snippets", ctx)
        self.assertEqual(ctx["total_results"], 2)
        self.assertGreater(ctx["total_chars"], 0)


if __name__ == "__main__":
    unittest.main()
