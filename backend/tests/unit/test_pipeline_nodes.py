import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from app.pipeline import nodes
from app.pipeline.graph import AnalysisPipelineSupervisor, _check_failure
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


class PipelineSupervisorTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_logs_wall_time_when_ainvoke_raises(self):
        supervisor = AnalysisPipelineSupervisor()
        supervisor.work_flow = Mock()
        supervisor.work_flow.ainvoke = AsyncMock(side_effect=RuntimeError("langgraph boom"))

        with self.assertLogs(
            "app.pipeline.graph.AnalysisPipelineSupervisor",
            level="ERROR",
        ) as logs:
            with self.assertRaisesRegex(RuntimeError, "langgraph boom"):
                await supervisor.run(pipeline_state())

        self.assertTrue(any("ainvoke 미처리 예외" in message for message in logs.output))
        self.assertTrue(any("벽시계=" in message for message in logs.output))


class PipelineNodeTests(unittest.IsolatedAsyncioTestCase):
    async def test_code_map_node_persists_grounded_scan(self):
        report = {"stats": {"files": 3}, "entrypoints": ["app/main.py"]}
        mock_service = AsyncMock()
        mock_service.execute_analysis_and_persist = AsyncMock(return_value=report)

        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__.return_value = AsyncMock()

        with (
            patch("app.repo.service.AnalysisService", autospec=True) as mock_class,
            patch.object(nodes, "_publish", AsyncMock()),
            patch.object(nodes, "async_session_factory", return_value=mock_session_ctx),
        ):
            mock_class.return_value = mock_service
            result = await nodes.code_map_node(pipeline_state())

        self.assertEqual(result["analysis_report"], report)
        self.assertEqual(result["progress"], 55)
        mock_service.execute_analysis_and_persist.assert_called_once()

    async def test_execute_analysis_and_persist_contracts(self):
        """execute_analysis_and_persist 반환 리포트가 프론트/API 계약 필드를 보장하는지 검사한다."""
        import tempfile
        import uuid
        from pathlib import Path
        from app.repo.service import AnalysisService

        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.update_job_status = AsyncMock()

        service = AnalysisService(mock_db)
        service.repository = mock_repo

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "main.py").write_text("print('hello')", encoding="utf-8")
            (tmp_path / "requirements.txt").write_text("fastapi", encoding="utf-8")

            job_id = uuid.uuid4()
            report = await service.execute_analysis_and_persist(
                job_id, str(tmp_path), "test_repo"
            )

            # 필수 계약 필드 검증
            self.assertIn("executive_summary", report)
            self.assertIn("files", report)
            self.assertTrue(len(report["files"]) > 0)

            # files 리스트 내부 컬럼 계약 검증 (bytes, chars, language 등)
            first_file = report["files"][0]
            self.assertIn("bytes", first_file)
            self.assertIn("chars", first_file)
            self.assertIn("language", first_file)

            # 리포지토리 상태 업데이트 호출 인자 검증 (DB 원본 report 적재 검증)
            mock_repo.update_job_status.assert_called_once()
            call_kwargs = mock_repo.update_job_status.call_args.kwargs
            self.assertEqual(call_kwargs["status"], "IN_PROGRESS")
            self.assertEqual(call_kwargs["progress"], 55)
            self.assertEqual(call_kwargs["report_json"], report)

    async def test_execute_analysis_and_persist_empty_repo_contracts(self):
        """빈 레포(텍스트 파일 없음) 폴백 리포트도 정상 경로와 동일한 필수 계약 필드를 유지해야 한다."""
        import tempfile
        import uuid
        from pathlib import Path
        from app.repo.service import AnalysisService

        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.update_job_status = AsyncMock()

        service = AnalysisService(mock_db)
        service.repository = mock_repo

        with tempfile.TemporaryDirectory() as tmpdir:
            # 분석 대상 텍스트 파일을 만들지 않아 total_files == 0 폴백 경로를 강제한다.
            job_id = uuid.uuid4()
            report = await service.execute_analysis_and_persist(
                job_id, str(tmpdir), "empty_repo"
            )

        # 프론트 WorkspaceReport 계약상 필수 필드 검증
        self.assertIn("executive_summary", report)
        self.assertIsInstance(report["executive_summary"], str)
        self.assertTrue(report["executive_summary"].strip())
        self.assertEqual(report["files"], [])
        self.assertEqual(report["stats"]["files"], 0)

        # 폴백 경로도 DB 진행 상태를 동일하게 갱신해야 한다.
        mock_repo.update_job_status.assert_called_once()
        call_kwargs = mock_repo.update_job_status.call_args.kwargs
        self.assertEqual(call_kwargs["status"], "IN_PROGRESS")
        self.assertEqual(call_kwargs["progress"], 55)
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
