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
from uuid import UUID
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
            "session_id": "session-1",
            "memory_context": {"messages": []},
            "rewritten_query": "login authentication",
            "access_plan": [],
            "security_result": {"approved": [], "rejected": []},
            "worker_results": [],
            "compact_context": {},
            "evaluator_decision": None,
            "replan_count": 0,
            "max_replans": 1,
            "replan_hint": None,
            "final_answer": None,
        }
        self.assertEqual(state["user_query"], "로그인 코드 어디에 있어?")
        self.assertEqual(state["session_id"], "session-1")
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
            "evaluator_decision": None,
            "replan_count": 0,
            "max_replans": 1,
            "replan_hint": None,
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

    def test_dispatcher_skips_duplicate_searches_within_plan(self):
        """동일 plan 안의 중복 (tool,target) 항목은 1회로 접힌다(#149)."""
        from app.agent.nodes.dispatcher_node import dispatcher_node

        state = {
            "clone_path": "/tmp",
            "access_plan": [
                {"tool": "search", "path": None, "query": "login flow", "scope": "chunk"},
                {"tool": "search", "path": None, "query": "login flow", "scope": "chunk"},  # 중복
                {"tool": "read", "path": "app/main.py", "query": "", "scope": "file"},
                {"tool": "read", "path": "app/main.py", "query": "", "scope": "file"},       # 중복
            ],
            "worker_results": [],
        }

        res = dispatcher_node(state)

        self.assertEqual(len(res["security_result"]["approved"]), 2)  # search 1 + read 1
        self.assertEqual(res["events"][0]["dedupedCount"], 2)

    def test_dispatcher_skips_already_executed_searches(self):
        """이전 반복의 worker_results와 동일한 path/query는 재계획에서 스킵된다(#149)."""
        from app.agent.nodes.dispatcher_node import dispatcher_node

        state = {
            "clone_path": "/tmp",
            "access_plan": [
                {"tool": "search", "path": None, "query": "login flow", "scope": "chunk"},  # 이미 실행됨
                {"tool": "read", "path": "app/new.py", "query": "", "scope": "file"},        # 신규
            ],
            # search/grep은 metadata.query=query, dir/read는 metadata.query=path 로 저장됨
            "worker_results": [
                {"id": "ev1", "path": "app/auth.py", "lineStart": 1, "lineEnd": 2,
                 "score": 0.9, "snippet": "...", "metadata": {"worker": "search", "query": "login flow"}},
            ],
        }

        res = dispatcher_node(state)

        approved = res["security_result"]["approved"]
        self.assertEqual(len(approved), 1)
        self.assertEqual(approved[0]["path"], "app/new.py")
        self.assertEqual(res["events"][0]["dedupedCount"], 1)

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
            "evaluator_decision": None,
            "replan_count": 0,
            "max_replans": 1,
            "replan_hint": None,
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
            "evaluator_decision": None,
            "replan_count": 0,
            "max_replans": 1,
            "replan_hint": None,
            "final_answer": None,
        }
        result = evaluator_node(state)
        ctx = result["compact_context"]
        self.assertIn("groupedByFile", ctx)
        self.assertEqual(ctx["selectedEvidenceCount"], 2)
        self.assertGreater(ctx["usedTokens"], 0)
        self.assertTrue(result["evaluator_decision"]["sufficient"])
        self.assertEqual(result["events"][1]["type"], "evaluator_decision")
        self.assertIn("evaluatorDecision", ctx)

    def test_evaluator_emits_replan_event_when_evidence_is_missing(self):
        from app.agent.nodes.evaluator_node import evaluator_node

        state = {
            "user_query": "stream 이벤트 처리 위치",
            "repo_id": "r1",
            "clone_path": "/tmp",
            "run_id": "r1",
            "rewritten_query": "stream 이벤트 처리 위치",
            "access_plan": [],
            "security_result": {"approved": [], "rejected": []},
            "worker_results": [],
            "events": [],
            "errors": [],
            "durations": {},
            "compact_context": {},
            "evaluator_decision": None,
            "replan_count": 0,
            "max_replans": 1,
            "replan_hint": None,
            "final_answer": None,
        }

        result = evaluator_node(state)

        self.assertFalse(result["evaluator_decision"]["sufficient"])
        self.assertEqual(result["events"][1]["type"], "evaluator_decision")
        self.assertEqual(result["events"][2]["type"], "replan_started")
        self.assertIn("nextPlanHint", result["events"][2])


class TestReplanRouting(unittest.TestCase):
    def test_route_after_evaluator_replans_until_limit(self):
        from app.agent.graph import route_after_evaluator

        route = route_after_evaluator({
            "evaluator_decision": {"sufficient": False},
            "replan_count": 0,
            "max_replans": 1,
            "replan_hint": "search again",
        })

        self.assertEqual(route, "planner_node")

    def test_route_after_evaluator_stops_at_limit(self):
        from app.agent.graph import route_after_evaluator
        from langgraph.graph import END

        route = route_after_evaluator({
            "evaluator_decision": {"sufficient": False},
            "replan_count": 1,
            "max_replans": 1,
            "replan_hint": None,
        })

        self.assertEqual(route, END)

    def test_route_after_evaluator_allows_multiple_replans_until_configured_limit(self):
        from app.agent.graph import route_after_evaluator
        from langgraph.graph import END

        self.assertEqual(route_after_evaluator({
            "evaluator_decision": {"sufficient": False},
            "replan_count": 1,
            "max_replans": 2,
            "replan_hint": "read service.py",
        }), "planner_node")
        self.assertEqual(route_after_evaluator({
            "evaluator_decision": {"sufficient": False},
            "replan_count": 2,
            "max_replans": 2,
            "replan_hint": "read router.py",
        }), "planner_node")
        self.assertEqual(route_after_evaluator({
            "evaluator_decision": {"sufficient": False},
            "replan_count": 2,
            "max_replans": 2,
            "replan_hint": None,
        }), END)


class TestAgentServiceReplanConfig(unittest.TestCase):
    def test_bounded_max_replans_uses_safe_default_and_cap(self):
        from app.agent.service import _bounded_max_replans

        self.assertEqual(_bounded_max_replans(None), 2)
        self.assertEqual(_bounded_max_replans("bad"), 2)
        self.assertEqual(_bounded_max_replans(-1), 0)
        self.assertEqual(_bounded_max_replans(2), 2)
        self.assertEqual(_bounded_max_replans(99), 3)


class TestPlannerNode(unittest.IsolatedAsyncioTestCase):
    def _base_state(self):
        return {
            "user_query": "stream 이벤트 처리 위치",
            "repo_id": "r1",
            "clone_path": "/tmp",
            "run_id": "run1",
            "session_id": "session-1",
            "target_file": None,
            "memory_context": {"messages": []},
            "rewritten_query": "",
            "access_plan": [],
            "security_result": {"approved": [], "rejected": []},
            "worker_results": [],
            "events": [],
            "errors": [],
            "durations": {},
            "compact_context": {},
            "evaluator_decision": None,
            "replan_count": 0,
            "max_replans": 1,
            "replan_hint": None,
            "final_answer": None,
        }

    async def test_planner_falls_back_when_llm_cannot_be_created(self):
        from app.agent.nodes.planner_node import planner_node

        state = self._base_state()

        with patch("app.agent.nodes.planner_node.create_planner_llm", side_effect=RuntimeError("missing key")):
            result = await planner_node(state)

        self.assertEqual(result["rewritten_query"], "stream 이벤트 처리 위치")
        self.assertEqual(result["access_plan"][0]["tool"], "search")
        self.assertEqual(result["events"][0]["type"], "planner_plan")

    async def test_planner_fallback_reads_target_file_first(self):
        from app.agent.nodes.planner_node import planner_node

        state = self._base_state()
        state["target_file"] = "frontend/src/features/chat/components/ChatInterface.tsx"

        with patch("app.agent.nodes.planner_node.create_planner_llm", side_effect=RuntimeError("missing key")):
            result = await planner_node(state)

        self.assertEqual(result["access_plan"][0], {
            "tool": "read",
            "path": "frontend/src/features/chat/components/ChatInterface.tsx",
            "query": "frontend/src/features/chat/components/ChatInterface.tsx",
            "scope": "file",
        })
        self.assertEqual(result["access_plan"][1]["tool"], "search")
        self.assertIn("read", result["events"][0]["selectedWorkers"])
        self.assertIn(
            "frontend/src/features/chat/components/ChatInterface.tsx",
            result["events"][0]["allowedPaths"],
        )

    async def test_planner_prepends_target_file_when_llm_omits_it(self):
        from app.agent.nodes.planner_node import planner_node

        class FakePlannerLLM:
            async def ainvoke(self, _messages):
                content = (
                    '{"rewritten_query":"chat context",'
                    '"access_plan":[{"tool":"search","path":null,'
                    '"query":"chat context","scope":"chunk"}]}'
                )
                return MagicMock(content=content)

        state = self._base_state()
        state["target_file"] = "backend/app/chat/router.py"

        with patch("app.agent.nodes.planner_node.create_planner_llm", return_value=FakePlannerLLM()):
            result = await planner_node(state)

        self.assertEqual(result["access_plan"][0]["tool"], "read")
        self.assertEqual(result["access_plan"][0]["path"], "backend/app/chat/router.py")
        self.assertEqual(result["access_plan"][1]["tool"], "search")

    async def test_planner_does_not_duplicate_existing_target_read(self):
        from app.agent.nodes.planner_node import planner_node

        class FakePlannerLLM:
            async def ainvoke(self, _messages):
                content = (
                    '{"rewritten_query":"chat context",'
                    '"access_plan":['
                    '{"tool":"read","path":"backend/app/chat/router.py","query":"router","scope":"file"},'
                    '{"tool":"search","path":null,"query":"chat context","scope":"chunk"}'
                    ']}'
                )
                return MagicMock(content=content)

        state = self._base_state()
        state["target_file"] = "backend/app/chat/router.py"

        with patch("app.agent.nodes.planner_node.create_planner_llm", return_value=FakePlannerLLM()):
            result = await planner_node(state)

        target_reads = [
            item
            for item in result["access_plan"]
            if item["tool"] == "read" and item["path"] == "backend/app/chat/router.py"
        ]
        self.assertEqual(len(target_reads), 1)
        self.assertEqual(result["access_plan"][0]["query"], "backend/app/chat/router.py")

    async def test_planner_prompt_includes_session_memory_context(self):
        from app.agent.nodes.planner_node import planner_node

        captured_messages = []

        class FakePlannerLLM:
            async def ainvoke(self, messages):
                captured_messages.extend(messages)
                return MagicMock(content='{"rewritten_query":"auth follow up","access_plan":[{"tool":"search","path":null,"query":"auth follow up","scope":"chunk"}]}')

        state = {
            "user_query": "그럼 토큰 갱신은?",
            "repo_id": "r1",
            "clone_path": "/tmp",
            "run_id": "run1",
            "session_id": "session-1",
            "memory_context": {
                "messages": [
                    {"role": "user", "content": "로그인 코드는 어디야?", "mode": "standard", "referenceCount": 0},
                    {"role": "assistant", "content": "auth/router.py를 보세요", "mode": "standard", "referenceCount": 1},
                ],
                "messageCount": 2,
            },
            "rewritten_query": "",
            "access_plan": [],
            "security_result": {"approved": [], "rejected": []},
            "worker_results": [],
            "events": [],
            "errors": [],
            "durations": {},
            "compact_context": {},
            "evaluator_decision": None,
            "replan_count": 0,
            "max_replans": 1,
            "replan_hint": None,
            "final_answer": None,
        }

        with patch("app.agent.nodes.planner_node.create_planner_llm", return_value=FakePlannerLLM()):
            await planner_node(state)

        self.assertIn("로그인 코드는 어디야?", captured_messages[1].content)
        self.assertIn("auth/router.py", captured_messages[1].content)


    def test_build_planner_messages_includes_replan_feedback_and_prior_evidence(self):
        from app.agent.nodes.planner_node import build_planner_messages

        state = self._base_state()
        state["replan_count"] = 1
        state["replan_hint"] = "backend/app/chat/router.py에서 SSE 이벤트 처리 확인"
        state["evaluator_decision"] = {
            "sufficient": False,
            "missingInfo": ["SSE stream 이벤트 처리 위치"],
            "nextPlanHint": "backend/app/chat/router.py read",
            "reason": "경로 근거가 부족함",
            "confidence": 0.4,
        }
        state["access_plan"] = [
            {"tool": "search", "path": None, "query": "stream 이벤트", "scope": "chunk"},
        ]
        state["worker_results"] = [{
            "id": "ev_1",
            "path": "frontend/src/features/chat/api/chatApi.ts",
            "lineStart": 1,
            "lineEnd": 20,
            "score": None,
            "snippet": "raw snippet should not be copied into planner prompt",
            "metadata": {"worker": "search", "tool": "keyword_search", "query": "stream 이벤트"},
        }]

        messages = build_planner_messages(state)
        payload = messages[1].content

        self.assertIn('"replan": true', payload)
        self.assertIn("SSE stream 이벤트 처리 위치", payload)
        self.assertIn("frontend/src/features/chat/api/chatApi.ts", payload)
        self.assertNotIn("raw snippet should not be copied", payload)

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


class TestAgentServiceSessionMemory(unittest.IsolatedAsyncioTestCase):
    async def test_initial_state_restores_recent_session_messages(self):
        from app.agent.service import CodeMapAgentService

        service = CodeMapAgentService(MagicMock())
        repo_id = UUID("00000000-0000-0000-0000-000000000111")
        session_id = UUID("00000000-0000-0000-0000-000000000222")

        with patch.object(service, "_load_memory_context", AsyncMock(return_value={
            "sessionId": str(session_id),
            "messageCount": 1,
            "messages": [{"role": "user", "content": "이전 질문", "mode": "standard", "referenceCount": 0}],
        })):
            state = await service._build_initial_state(
                repo_id=repo_id,
                user_query="후속 질문",
                clone_path="/tmp/repo",
                run_id="run1",
                session_id=session_id,
            )

        self.assertEqual(state["session_id"], str(session_id))
        self.assertEqual(state["memory_context"]["messages"][0]["content"], "이전 질문")
        self.assertEqual(service._graph_config(session_id=session_id, run_id="run1")["configurable"]["thread_id"], str(session_id))




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
                "evaluator_decision": None,
                "replan_count": 0,
                "max_replans": 1,
                "replan_hint": None,
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
