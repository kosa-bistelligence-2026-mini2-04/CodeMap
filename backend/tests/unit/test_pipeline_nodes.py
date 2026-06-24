import unittest
from unittest.mock import AsyncMock, patch

from app.repo.pipeline import nodes
from app.repo.pipeline.graph import _check_failure
from app.repo.schemas import JobStatus, PipelineStage


def pipeline_state(**overrides):
    state = {
        "messages": [],
        "job_id": "550e8400-e29b-41d4-a716-446655440000",
        "repo_url": "https://github.com/example/sample",
        "branch": "main",
        "owner": "example",
        "repo_name": "sample",
        "model": "auto",
        "force_refresh": False,
        "analysis_report": None,
        "clone_path": "/tmp/sample",
        "current_stage": PipelineStage.CLONE.value,
        "progress": 20,
        "status": JobStatus.IN_PROGRESS.value,
        "error": None,
    }
    state.update(overrides)
    return state


class PipelineRoutingTests(unittest.TestCase):
    def test_failure_routes_to_end(self):
        self.assertEqual(_check_failure(pipeline_state(status=JobStatus.FAILED.value)), "failed")

    def test_non_failure_routes_to_next_node(self):
        self.assertEqual(_check_failure(pipeline_state()), "success")


class PipelineNodeTests(unittest.IsolatedAsyncioTestCase):
    async def test_code_map_node_persists_grounded_scan(self):
        report = {"stats": {"files": 3}, "entrypoints": ["app/main.py"]}
        with (
            patch.object(nodes, "scan_repository", return_value=report),
            patch.object(nodes, "_update_db", AsyncMock()) as update,
            patch.object(nodes, "_publish", AsyncMock()),
        ):
            result = await nodes.code_map_node(pipeline_state())
        self.assertEqual(result["analysis_report"], report)
        self.assertEqual(result["progress"], 55)
        self.assertEqual(update.await_args.kwargs["report_json"], report)

    async def test_document_and_onboarding_nodes_enrich_report(self):
        state = pipeline_state(analysis_report={"entrypoints": ["a.py", "b.py", "c.py"]})
        with (
            patch.object(nodes, "_update_db", AsyncMock()),
            patch.object(nodes, "_llm_json", AsyncMock(return_value=None)),
        ):
            documented = await nodes.doc_gen_node(state)
            onboarded = await nodes.onboarding_node(
                pipeline_state(analysis_report=documented["analysis_report"])
            )
        self.assertEqual(documented["analysis_report"]["reading_order"], ["a.py", "b.py", "c.py"])
        self.assertEqual(len(onboarded["analysis_report"]["onboarding_steps"]), 3)

    async def test_report_node_finishes_pipeline(self):
        with (
            patch.object(nodes, "_update_db", AsyncMock()),
            patch.object(nodes, "_publish", AsyncMock()),
        ):
            result = await nodes.report_node(pipeline_state(analysis_report={"stats": {"files": 3}}))
        self.assertEqual(result["status"], JobStatus.COMPLETED.value)
        self.assertEqual(result["progress"], 100)
        self.assertEqual(result["analysis_report"]["model_used"], "auto")

    # ── 회귀 테스트: doc_gen / onboarding 예외 시 DB·SSE 종료 상태 기록 ──────────────────
    # PR #112 리뷰 blocker — 두 노드의 except 블록이 _update_db·_publish를 호출하지 않아
    # 클라이언트가 IN_PROGRESS에서 무한 대기하는 버그를 막기 위한 테스트.

    async def test_doc_gen_node_failure_publishes_failed_event(self):
        """doc_gen_node 내부 예외 발생 시 FAILED 이벤트가 DB·SSE에 기록되어야 한다."""
        with (
            patch.object(nodes, "_update_db", AsyncMock()) as mock_update,
            patch.object(nodes, "_publish", AsyncMock()) as mock_publish,
            patch.object(nodes, "_llm_json", AsyncMock(side_effect=RuntimeError("boom"))),
        ):
            result = await nodes.doc_gen_node(pipeline_state(analysis_report={"entrypoints": []}))

        self.assertEqual(result["status"], JobStatus.FAILED.value)
        self.assertEqual(result["current_stage"], PipelineStage.DOC_GEN.value)
        self.assertIsNotNone(result["error"])

        # DB가 FAILED로 갱신되었는지 검증
        update_kwargs = mock_update.call_args.kwargs
        self.assertEqual(update_kwargs["status"], JobStatus.FAILED.value)
        self.assertEqual(update_kwargs["stage"], PipelineStage.DOC_GEN.value)

        # SSE FAILED 이벤트가 발행되었는지 검증
        publish_args = mock_publish.call_args.args
        self.assertIs(publish_args[2], JobStatus.FAILED)

    async def test_onboarding_node_failure_publishes_failed_event(self):
        """onboarding_node 내부 예외 발생 시 FAILED 이벤트가 DB·SSE에 기록되어야 한다."""
        with (
            patch.object(nodes, "_update_db", AsyncMock()) as mock_update,
            patch.object(nodes, "_publish", AsyncMock()) as mock_publish,
            patch.object(nodes, "_llm_json", AsyncMock(side_effect=RuntimeError("boom"))),
        ):
            result = await nodes.onboarding_node(pipeline_state(analysis_report={"entrypoints": []}))

        self.assertEqual(result["status"], JobStatus.FAILED.value)
        self.assertEqual(result["current_stage"], PipelineStage.ONBOARDING.value)

        # DB가 FAILED로 갱신되었는지 검증
        update_kwargs = mock_update.call_args.kwargs
        self.assertEqual(update_kwargs["status"], JobStatus.FAILED.value)
        self.assertEqual(update_kwargs["stage"], PipelineStage.ONBOARDING.value)

        # SSE FAILED 이벤트가 발행되었는지 검증
        publish_args = mock_publish.call_args.args
        self.assertIs(publish_args[2], JobStatus.FAILED)
