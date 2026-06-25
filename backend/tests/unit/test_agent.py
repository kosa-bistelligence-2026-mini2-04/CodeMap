"""
Unit tests for agent — Dispatcher Node 보안 로직 및 State 스키마 검증.

LLM 호출 없이 실행 가능한 결정론적 로직만 테스트합니다.
"""

from __future__ import annotations

import sys
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

# backend를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))


class TestCodeMapState(unittest.TestCase):
    """CodeMapState TypedDict 스키마 검증."""

    def test_state_instantiation(self):
        from app.agent.state import CodeMapState, WorkerResult, AccessPlanItem
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
        from app.agent.state import WorkerResult
        r = WorkerResult(
            id="ev_123",
            path="app/auth/service.py",
            lineStart=1,
            lineEnd=10,
            score=0.9,
            snippet="def login(): ...",
            metadata={"worker": "search"}
        )
        self.assertEqual(r["metadata"]["worker"], "search")
        self.assertEqual(r["path"], "app/auth/service.py")


class TestDispatcherNodeSecurity(unittest.TestCase):
    """Dispatcher Node 보안 로직 단위 테스트."""

    def _is_safe(self, path):
        from app.agent.nodes.dispatcher_node import _is_safe_path
        return _is_safe_path(path)

    def test_safe_paths(self):
        self.assertTrue(self._is_safe(None))            # search: path 없음
        self.assertTrue(self._is_safe("app/auth"))      # 정상 경로
        self.assertTrue(self._is_safe("backend/app/chat/service.py"))

    def test_path_traversal_blocked(self):
        self.assertFalse(self._is_safe("../../../etc/passwd"))
        self.assertFalse(self._is_safe("../../secret"))
        self.assertFalse(self._is_safe("app/../../../root"))
        self.assertFalse(self._is_safe(r"..\..\secret.py"))

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

    def test_dispatcher_node_returns_security_result(self):
        """dispatcher_node가 보안 검증된 dict를 반환하는지 검증."""
        from app.agent.nodes.dispatcher_node import dispatcher_node, fanout_to_workers

        state = {
            "user_query": "test",
            "repo_id": "r1",
            "clone_path": "/tmp",
            "run_id": "r1",
            "rewritten_query": "test",
            "access_plan": [
                {"tool": "search", "path": None, "query": "test", "scope": "chunk"},
                {"tool": "grep", "path": "app/", "query": "def login", "scope": "file"},
                {"tool": "read", "path": "../../../etc/passwd", "query": "", "scope": "file"},  # 차단
            ],
            "security_result": {"approved": [], "rejected": []},
            "worker_results": [],
            "events": [],
            "errors": [],
            "durations": {},
            "compact_context": {},
            "final_answer": None,
        }

        res = dispatcher_node(state)
        self.assertIn("security_result", res)
        self.assertEqual(len(res["security_result"]["approved"]), 2)
        self.assertEqual(len(res["security_result"]["rejected"]), 1)
        self.assertTrue(res["events"][0]["allowed"])
        
        # Add to state to test fanout
        state["security_result"] = res["security_result"]
        sends = fanout_to_workers(state)
        node_names = [s.node for s in sends]
        self.assertIn("search_worker", node_names)
        self.assertIn("grep_worker", node_names)
        self.assertNotIn("read_worker", node_names)  # 차단됨
        self.assertEqual(len(sends), 2)

    def test_dispatcher_marks_route_disallowed_when_every_plan_is_rejected(self):
        from app.agent.nodes.dispatcher_node import dispatcher_node

        state = {
            "user_query": "test",
            "repo_id": "r1",
            "clone_path": "/tmp",
            "run_id": "r1",
            "rewritten_query": "test",
            "access_plan": [
                {"tool": "read", "path": "../../../etc/passwd", "query": "", "scope": "file"},
            ],
            "security_result": {"approved": [], "rejected": []},
            "worker_results": [],
            "events": [],
            "errors": [],
            "durations": {},
            "compact_context": {},
            "final_answer": None,
        }

        res = dispatcher_node(state)

        self.assertEqual(res["security_result"]["approved"], [])
        self.assertFalse(res["events"][0]["allowed"])

    def test_fanout_blocks_unregistered_tools(self):
        """미등록 tool은 LangGraph Send 대상에서 제외됩니다."""
        from app.agent.nodes.dispatcher_node import _ALLOWED_WORKERS, fanout_to_workers

        self.assertEqual(_ALLOWED_WORKERS, frozenset({"search", "dir", "grep", "read"}))

        state = {
            "user_query": "test",
            "repo_id": "r1",
            "clone_path": "/tmp",
            "run_id": "r1",
            "rewritten_query": "test",
            "access_plan": [],
            "security_result": {
                "approved": [
                    {"tool": "search", "path": None, "query": "test", "scope": "chunk"},
                    {"tool": "unknown", "path": None, "query": "test", "scope": "chunk"},
                    {"tool": "read", "path": "app/main.py", "query": "", "scope": "file"},
                ],
                "rejected": [],
            },
            "worker_results": [],
            "events": [],
            "errors": [],
            "durations": {},
            "compact_context": {},
            "final_answer": None,
        }

        node_names = [send.node for send in fanout_to_workers(state)]

        self.assertEqual(node_names, ["search_worker", "read_worker"])


class TestEvidenceAggregator(unittest.TestCase):
    """Evaluator 중복 제거 및 budget 제한 검증."""

    def test_deduplication(self):
        from app.agent.nodes.evaluator_node import _deduplicate
        from app.agent.state import WorkerResult

        r1 = WorkerResult(id="1", path="a.py", lineStart=1, lineEnd=2, score=None, snippet="same content", metadata={"worker":"search"})
        r2 = WorkerResult(id="2", path="a.py", lineStart=1, lineEnd=2, score=None, snippet="same content", metadata={"worker":"grep"})  # 중복
        r3 = WorkerResult(id="3", path="b.py", lineStart=1, lineEnd=2, score=None, snippet="different content", metadata={"worker":"read"})

        result = _deduplicate([r1, r2, r3])
        self.assertEqual(len(result), 2)  # r2는 중복 제거

    def test_aggregator_builds_compact_context(self):
        from app.agent.nodes.evaluator_node import evaluator_node
        from app.agent.state import WorkerResult

        state = {
            "user_query": "test",
            "repo_id": "r1",
            "clone_path": "/tmp",
            "run_id": "r1",
            "rewritten_query": "test",
            "access_plan": [],
            "security_result": {"approved": [], "rejected": []},
            "worker_results": [
                WorkerResult(id="1", path=None, lineStart=None, lineEnd=None, score=None, snippet="code snippet here", metadata={"worker":"search"}),
                WorkerResult(id="2", path="auth.py", lineStart=None, lineEnd=None, score=None, snippet="def login(): pass", metadata={"worker":"read"}),
            ],
            "events": [],
            "errors": [],
            "durations": {},
            "compact_context": {},
            "final_answer": None,
        }
        result = evaluator_node(state)
        ctx = result["compact_context"]
        self.assertIn("groupedByFile", ctx)
        self.assertEqual(ctx["selectedEvidenceCount"], 2)
        self.assertGreater(ctx["usedTokens"], 0)


class TestWorkerEvents(unittest.IsolatedAsyncioTestCase):
    async def test_read_worker_emits_started_before_result(self):
        from app.agent.workers.read_worker import read_worker

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            (root / "app.py").write_text("print('hello')\n", encoding="utf-8")

            result = await read_worker({
                "user_query": "read app",
                "repo_id": "r1",
                "clone_path": str(root),
                "run_id": "run1",
                "rewritten_query": "read app",
                "access_plan": [],
                "security_result": {"approved": [], "rejected": []},
                "worker_results": [],
                "events": [],
                "errors": [],
                "durations": {},
                "compact_context": {},
                "final_answer": None,
                "_plan_item": {"tool": "read", "path": "app.py", "query": "", "scope": "file"},
            })

        self.assertEqual([event["type"] for event in result["events"]], ["worker_started", "worker_result"])
        self.assertEqual(result["events"][0]["worker"], "read")

    async def test_blocking_workers_run_tool_calls_in_threads(self):
        from app.agent.workers.dir_worker import dir_worker
        from app.agent.workers.grep_worker import grep_worker
        from app.agent.workers.read_worker import read_worker

        base_state = {
            "user_query": "test",
            "repo_id": "r1",
            "clone_path": "/tmp/repo",
            "run_id": "run1",
            "rewritten_query": "test",
            "access_plan": [],
            "security_result": {"approved": [], "rejected": []},
            "worker_results": [],
            "events": [],
            "errors": [],
            "durations": {},
            "compact_context": {},
            "final_answer": None,
        }

        with patch("app.agent.workers.dir_worker.asyncio.to_thread", AsyncMock(return_value="tree")) as to_thread:
            await dir_worker({**base_state, "_plan_item": {"tool": "dir", "path": "app", "query": "", "scope": "directory"}})
            self.assertEqual(to_thread.await_count, 1)

        with patch("app.agent.workers.grep_worker.asyncio.to_thread", AsyncMock(return_value="hit")) as to_thread:
            await grep_worker({**base_state, "_plan_item": {"tool": "grep", "path": "app", "query": "login", "scope": "file"}})
            self.assertEqual(to_thread.await_count, 1)

        with patch("app.agent.workers.read_worker.asyncio.to_thread", AsyncMock(return_value="content")) as to_thread:
            await read_worker({**base_state, "_plan_item": {"tool": "read", "path": "app.py", "query": "", "scope": "file"}})
            self.assertEqual(to_thread.await_count, 1)


class TestPlannerNode(unittest.IsolatedAsyncioTestCase):
    async def test_planner_parses_text_blocks_from_list_content(self):
        from app.agent.nodes.planner_node import planner_node

        class FakePlannerLLM:
            async def ainvoke(self, _messages):
                return MagicMock(content=[{
                    "type": "text",
                    "text": '{"rewritten_query":"auth flow","access_plan":[{"tool":"read","path":"app/auth.py","query":"auth","scope":"file"}]}',
                }])

        state = {
            "user_query": "auth?",
            "repo_id": "r1",
            "clone_path": "/tmp/repo",
            "run_id": "run1",
            "rewritten_query": "",
            "access_plan": [],
            "security_result": {"approved": [], "rejected": []},
            "worker_results": [],
            "events": [],
            "errors": [],
            "durations": {},
            "compact_context": {},
            "final_answer": None,
        }

        with patch("app.agent.nodes.planner_node.create_planner_llm", return_value=FakePlannerLLM()):
            result = await planner_node(state)

        self.assertEqual(result["rewritten_query"], "auth flow")
        self.assertEqual(result["access_plan"][0]["path"], "app/auth.py")


class TestRepositoryToolBoundaries(unittest.TestCase):
    """Repository-bounded tool helpers must not trust string-prefix path checks."""

    def test_file_read_blocks_prefix_sibling_path(self):
        from app.tool.file_read import read_repository_file

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            sibling = Path(tmp) / "repo-other"
            root.mkdir()
            sibling.mkdir()
            secret = sibling / "safe.py"
            secret.write_text("outside", encoding="utf-8")

            result = read_repository_file(str(root), "../repo-other/safe.py")

        self.assertEqual(result, "")

    def test_grep_scans_single_file_path(self):
        from app.tool.grep_scan import grep_repository_path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            file_path = root / "app.py"
            file_path.write_text("def login():\n    pass\n", encoding="utf-8")

            result = grep_repository_path(str(root), "app.py", "login")

        self.assertIn("app.py:1: def login():", result)

    def test_grep_rejects_empty_and_nested_quantifier_patterns(self):
        from app.tool.grep_scan import grep_repository_path

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "repo"
            root.mkdir()
            (root / "app.py").write_text("aaaaab\n", encoding="utf-8")

            self.assertEqual(grep_repository_path(str(root), "app.py", ""), "")
            self.assertEqual(grep_repository_path(str(root), "app.py", "(a+)+$"), "")


if __name__ == "__main__":
    unittest.main()
