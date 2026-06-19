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
