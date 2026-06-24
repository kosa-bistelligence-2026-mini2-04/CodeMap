"""
Unit tests for agent_graph — Route Node 보안 로직 및 State 스키마 검증.

LLM 호출 없이 실행 가능한 결정론적 로직만 테스트합니다.
"""

from __future__ import annotations

import sys
import os
import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# backend를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))


class TestCodeMapState(unittest.TestCase):
    """CodeMapState TypedDict 스키마 검증."""

    def test_state_instantiation(self):
        from app.agent_graph.state import CodeMapState
        state: CodeMapState = {
            "run_id": "test-run",
            "events": [],
            "durations": {},
            "errors": [],
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
        self.assertEqual(state["run_id"], "test-run")

    def test_worker_result_structure(self):
        from app.agent_graph.state import WorkerResult
        r = WorkerResult(
            id="1234",
            worker="search",
            tool="search_repository",
            query="login",
            snippet="def login(): ...",
            path="app/auth/service.py",
        )
        self.assertEqual(r["worker"], "search")
        self.assertEqual(r["path"], "app/auth/service.py")


class TestRouteNodeSecurity(unittest.TestCase):
    """Route Node 보안 로직 단위 테스트."""

    def _is_safe(self, path):
        from app.agent_graph.nodes.route_node import _is_safe_path
        # 테스트를 위해 가상의 clone_root 경로를 사용
        return _is_safe_path(path, clone_root="/tmp/repo")

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

    def test_route_node_updates_security_result(self):
        from app.agent_graph.nodes.route_node import route_node
        state = {
            "access_plan": [
                {"tool": "search", "path": None, "query": "test", "scope": "chunk"},
                {"tool": "grep", "path": "app/", "query": "def login", "scope": "file"},
                {"tool": "read", "path": "../../../etc/passwd", "query": "", "scope": "file"},  # 차단
            ],
            "clone_path": "/tmp/repo"
        }
        res = route_node(state)
        sec = res["security_result"]
        self.assertEqual(len(sec["approved"]), 2)
        self.assertEqual(len(sec["rejected"]), 1)

    def test_route_to_workers_returns_sends(self):
        """route_to_workers가 Send 객체 리스트를 반환하는지 검증."""
        try:
            from langgraph.types import Send
            has_langgraph = True
        except ImportError:
            has_langgraph = False

        if not has_langgraph:
            self.skipTest("langgraph 미설치 환경 — Send 반환 테스트 생략")

        from app.agent_graph.graph import route_to_workers

        state = {
            "security_result": {
                "approved": [
                    {"tool": "search", "path": None, "query": "test", "scope": "chunk"},
                    {"tool": "grep", "path": "app/", "query": "def", "scope": "file"}
                ],
                "rejected": []
            }
        }

        sends = route_to_workers(state)
        node_names = [s.node for s in sends]
        self.assertIn("search_worker", node_names)
        self.assertIn("grep_worker", node_names)
        self.assertNotIn("read_worker", node_names)
        self.assertEqual(len(sends), 2)


class TestEvidenceAggregator(unittest.TestCase):
    """Evidence Aggregator 중복 제거 및 budget 제한 검증."""

    def test_deduplication(self):
        from app.agent_graph.nodes.evidence_aggregator import _deduplicate
        from app.agent_graph.state import WorkerResult

        r1 = WorkerResult(id="1", worker="search", tool="t", query="q",
                          snippet="same content", path="a.py")
        r2 = WorkerResult(id="2", worker="grep", tool="t", query="q",
                          snippet="same content", path="a.py")  # 중복 (내용과 파일 동일)
        r3 = WorkerResult(id="3", worker="read", tool="t", query="q",
                          snippet="different content", path="b.py")

        result = _deduplicate([r1, r2, r3])
        self.assertEqual(len(result), 2)  # r2는 중복 제거됨

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
                WorkerResult(id="1", worker="search", tool="t", query="q",
                             snippet="code snippet here", path=None),
                WorkerResult(id="2", worker="read", tool="t", query="q",
                             snippet="def login(): pass", path="auth.py"),
            ],
            "compact_context": {},
            "final_answer": None,
        }
        result = evidence_aggregator(state)
        ctx = result["compact_context"]
        self.assertIn("snippets", ctx)
        self.assertEqual(ctx["total_results"], 2)
        self.assertGreater(ctx["total_chars"], 0)


class TestWorkers(unittest.IsolatedAsyncioTestCase):
    """Worker fallback 동작 검증."""

    async def test_search_worker_falls_back_to_keyword_search(self):
        from app.agent_graph.workers.workers import search_worker

        state = {
            "_plan_item": {"tool": "search", "query": "login", "path": None, "scope": "chunk"},
            "rewritten_query": "login",
            "user_query": "login code",
            "repo_id": "not-a-uuid",
            "clone_path": "/tmp/repo",
        }

        with patch("app.repo.analyzer.search_repository") as search_repository:
            search_repository.return_value = [
                {"file": "app/auth.py", "content": "def login(): pass"}
            ]
            result = await search_worker(state)

        worker_result = result["worker_results"][0]
        self.assertEqual(worker_result["tool"], "search_repository")
        self.assertIn("app/auth.py", worker_result["snippet"])
        search_repository.assert_called_once_with("/tmp/repo", "login", 5)


class TestGraphExecution(unittest.IsolatedAsyncioTestCase):
    """실제 LangGraph의 ainvoke 테스트 (dummy supervisor 사용)."""

    async def test_graph_ainvoke_happy_path(self):
        try:
            import langgraph
            has_langgraph = True
        except ImportError:
            has_langgraph = False

        if not has_langgraph:
            self.skipTest("langgraph 미설치 환경 — ainvoke 테스트 생략")
            
        from app.agent_graph.graph import build_graph
        from app.agent_graph.state import CodeMapState
        
        # supervisor_node를 더미로 교체하기 위해 graph builder 새로 생성
        builder = build_graph()
        
        async def dummy_supervisor(state: CodeMapState):
            return {
                "access_plan": [
                    {"tool": "dir", "path": "", "query": "", "scope": "directory"}
                ],
                "rewritten_query": "test"
            }
            
        # 최신 LangGraph는 같은 이름의 노드 재등록을 허용하지 않는다.
        builder.nodes.pop("supervisor_agent", None)
        builder.add_node("supervisor_agent", dummy_supervisor)
        builder.set_entry_point("supervisor_agent")
        
        graph = builder.compile()
        
        initial_state = {
            "run_id": "test-run",
            "events": [],
            "durations": {},
            "errors": [],
            "user_query": "test query",
            "repo_id": "repo1",
            "clone_path": "/tmp",
            "rewritten_query": "",
            "access_plan": [],
            "security_result": {"approved": [], "rejected": []},
            "worker_results": [],
            "compact_context": {},
            "final_answer": None,
        }
        
        result = await graph.ainvoke(initial_state)
        self.assertIn("compact_context", result)
        self.assertIn("security_result", result)
        self.assertEqual(len(result["security_result"]["approved"]), 1)
        self.assertGreater(len(result["worker_results"]), 0)


if __name__ == "__main__":
    unittest.main()
