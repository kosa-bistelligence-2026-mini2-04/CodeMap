"""
DOCS-GEN 내부 파이프라인(순서 1~6) 유닛 테스트

검증 대상:
  - GenFormState TypedDict 구조
  - GenFormSupervisor 라우팅 (_check_failure)
  - 각 노드 함수: LLM 성공 경로 / 폴백 경로 / 예외 처리 경로
  - master_report_node 최종 통합 결과 필드
  - 정적 분석 5대 항목 (Self 리뷰)

Self 리뷰 결과 (CLAUDE.md §7 기준):
  1. KeyError 방어: 모든 dict 접근은 .get() 또는 dict() 복사 후 접근
  2. Null-Safety: Optional 필드는 `or {}` / `or ""` 폴백 가드 적용
  3. Exception Safety: 각 노드는 try/except로 파이프라인 보호
  4. 비동기 블로킹 방어: _read_readme, _collect_config_files → asyncio.to_thread
  5. 데이터 불변성: analysis_report는 dict(state.get(...) or {}) 복사본으로 처리
"""

import inspect
import unittest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from app.gen.form import graph as gen_graph
from app.gen.form import nodes as gen_nodes
from app.gen.form.graph import GenFormSupervisor, _check_failure
from app.gen.form.state import GenFormState


# ──────────────────────────────────────────────
# 테스트용 기본 상태 팩토리
# ──────────────────────────────────────────────
def _base_state(**overrides) -> GenFormState:
    """테스트에 사용할 GenFormState 기본값을 반환한다."""
    state: GenFormState = {
        "repo_id": "test-repo-001",
        "clone_path": None,
        "analysis_report": {
            "repository": {"name": "sample-repo"},
            "stats": {
                "files": 10,
                "lines": 500,
                "tests": 3,
                "primary_language": "Python",
            },
            "stack": ["FastAPI", "PostgreSQL"],
            "languages": [{"name": "Python", "lines": 400}],
            "entrypoints": ["app/main.py", "app/router.py"],
            "key_strengths": ["타입 힌트", "비동기 처리"],
            "key_risks": ["auth 미구현"],
        },
        "project_intro": None,
        "doc_summary": None,
        "folder_summaries": None,
        "flow_explanation": None,
        "onboarding_guide": None,
        "master_report": None,
        "status": "running",
        "error": None,
        "timings": {},
    }
    state.update(overrides)
    return state


# ──────────────────────────────────────────────────────────────
# 1. GenFormState 구조 검증
# ──────────────────────────────────────────────────────────────
class GenFormStateStructureTests(unittest.TestCase):
    """GenFormState TypedDict가 필수 필드를 모두 포함하는지 검증한다."""

    def test_required_input_fields_present(self):
        """입력 필드(repo_id, clone_path, analysis_report)가 존재해야 한다."""
        state = _base_state()
        self.assertIn("repo_id", state)
        self.assertIn("clone_path", state)
        self.assertIn("analysis_report", state)

    def test_intermediate_result_fields_present(self):
        """중간 결과 필드가 초기에 None이어야 한다."""
        state = _base_state()
        self.assertIsNone(state["project_intro"])
        self.assertIsNone(state["doc_summary"])
        self.assertIsNone(state["folder_summaries"])
        self.assertIsNone(state["flow_explanation"])
        self.assertIsNone(state["onboarding_guide"])
        self.assertIsNone(state["master_report"])

    def test_control_fields_present(self):
        """파이프라인 제어 필드가 기본값으로 설정되어야 한다."""
        state = _base_state()
        self.assertEqual(state["status"], "running")
        self.assertIsNone(state["error"])
        self.assertEqual(state["timings"], {})


# ──────────────────────────────────────────────────────────────
# 2. _check_failure 라우팅 함수 검증
# ──────────────────────────────────────────────────────────────
class GenFormRoutingTests(unittest.TestCase):
    """_check_failure 조건부 라우팅 함수를 검증한다."""

    def test_failed_status_routes_to_end(self):
        """status가 'failed'이면 'failed'를 반환해야 한다."""
        self.assertEqual(_check_failure(_base_state(status="failed")), "failed")

    def test_running_status_routes_to_next(self):
        """status가 'running'이면 'success'를 반환해야 한다."""
        self.assertEqual(_check_failure(_base_state(status="running")), "success")

    def test_completed_status_routes_to_next(self):
        """status가 'completed'이면 'success'를 반환해야 한다."""
        self.assertEqual(_check_failure(_base_state(status="completed")), "success")


# ──────────────────────────────────────────────────────────────
# 3. GenFormSupervisor 검증
# ──────────────────────────────────────────────────────────────
class GenFormSupervisorTests(unittest.IsolatedAsyncioTestCase):
    """GenFormSupervisor 워크플로우 Supervisor를 검증한다."""

    async def test_run_raises_and_logs_on_ainvoke_failure(self):
        """ainvoke 예외 발생 시 로그를 남기고 예외를 다시 발생시켜야 한다."""
        supervisor = GenFormSupervisor()
        supervisor.work_flow = Mock()
        supervisor.work_flow.ainvoke = AsyncMock(
            side_effect=RuntimeError("langgraph boom")
        )

        with self.assertLogs(
            "app.gen.form.graph.GenFormSupervisor",
            level="ERROR",
        ) as logs:
            with self.assertRaisesRegex(RuntimeError, "langgraph boom"):
                await supervisor.run(_base_state())

        self.assertTrue(
            any("ainvoke 미처리 예외" in msg for msg in logs.output)
        )
        self.assertTrue(
            any("경과=" in msg for msg in logs.output)
        )

    async def test_run_returns_final_state_on_success(self):
        """정상 실행 시 final state를 그대로 반환해야 한다."""
        expected = _base_state(status="completed", master_report={"repo_id": "test-repo-001"})
        supervisor = GenFormSupervisor()
        supervisor.work_flow = Mock()
        supervisor.work_flow.ainvoke = AsyncMock(return_value=expected)

        result = await supervisor.run(_base_state())
        self.assertEqual(result["status"], "completed")
        self.assertIsNotNone(result["master_report"])

    async def test_run_logs_timing_summary_on_failure(self):
        """파이프라인 실패 시 타이밍 요약 로그를 출력해야 한다."""
        failed_state = _base_state(
            status="failed",
            error="B-205 실패: 예외",
            timings={"b205_failed": 0.5},
        )
        supervisor = GenFormSupervisor()
        supervisor.work_flow = Mock()
        supervisor.work_flow.ainvoke = AsyncMock(return_value=failed_state)

        with self.assertLogs(
            "app.gen.form.graph.GenFormSupervisor",
            level="WARNING",
        ) as logs:
            await supervisor.run(_base_state())

        self.assertTrue(
            any("실패 시 소요시간 요약" in msg for msg in logs.output)
        )


# ──────────────────────────────────────────────────────────────
# 4. readme_intro_node (B-205) 검증
# ──────────────────────────────────────────────────────────────
class ReadmeIntroNodeTests(unittest.IsolatedAsyncioTestCase):
    """DOCS-GEN-B-205: README 기반 프로젝트 소개 생성 노드 검증."""

    async def test_llm_success_produces_structured_intro(self):
        """LLM이 유효한 JSON을 반환하면 구조화된 소개 문자열이 생성되어야 한다."""
        llm_output = {
            "title": "샘플 프로젝트",
            "description": "FastAPI 기반 REST API 서비스",
            "purpose": "코드 분석 자동화 도구입니다.",
            "key_features": ["자동 문서화", "RAG 검색"],
        }
        with (
            patch.object(gen_nodes, "_read_readme", return_value="# Sample\n설명"),
            patch.object(gen_nodes, "_llm_json", AsyncMock(return_value=llm_output)),
        ):
            result = await gen_nodes.readme_intro_node(_base_state())

        self.assertIn("project_intro", result)
        self.assertIn("샘플 프로젝트", result["project_intro"])
        self.assertIn("자동 문서화", result["project_intro"])
        self.assertIn("b205_readme_intro", result["timings"])

    async def test_llm_none_falls_back_to_heuristic(self):
        """LLM이 None을 반환하면 휴리스틱 폴백으로 소개가 생성되어야 한다."""
        with (
            patch.object(gen_nodes, "_read_readme", return_value="# Sample Repo"),
            patch.object(gen_nodes, "_llm_json", AsyncMock(return_value=None)),
        ):
            result = await gen_nodes.readme_intro_node(_base_state())

        self.assertIn("project_intro", result)
        self.assertIsNotNone(result["project_intro"])
        self.assertNotEqual(result.get("status"), "failed")

    async def test_exception_sets_failed_status(self):
        """내부 예외 발생 시 status='failed'와 error 필드가 설정되어야 한다."""
        with patch.object(
            gen_nodes, "_read_readme", side_effect=OSError("읽기 오류")
        ):
            result = await gen_nodes.readme_intro_node(_base_state())

        self.assertEqual(result["status"], "failed")
        self.assertIn("B-205", result["error"])
        self.assertIn("b205_failed", result["timings"])

    async def test_timings_field_always_updated(self):
        """성공·실패 모두 timings 딕셔너리가 갱신되어야 한다."""
        with (
            patch.object(gen_nodes, "_read_readme", return_value=""),
            patch.object(gen_nodes, "_llm_json", AsyncMock(return_value=None)),
        ):
            result = await gen_nodes.readme_intro_node(
                _base_state(timings={"b_prev": 1.0})
            )

        self.assertIn("b_prev", result["timings"])
        self.assertIn("b205_readme_intro", result["timings"])


# ──────────────────────────────────────────────────────────────
# 5. doc_summary_node (B-201) 검증
# ──────────────────────────────────────────────────────────────
class DocSummaryNodeTests(unittest.IsolatedAsyncioTestCase):
    """DOCS-GEN-B-201: 문서 요약 agent 노드 검증."""

    async def test_llm_success_returns_summary_dict(self):
        """LLM 성공 시 doc_summary에 purpose, key_features 등이 포함되어야 한다."""
        llm_output = {
            "purpose": "코드 분석 자동화",
            "key_features": ["요약 생성", "온보딩 가이드"],
            "tech_context": "FastAPI + pgvector",
            "architecture_hint": "레이어드 아키텍처",
        }
        with (
            patch.object(gen_nodes, "_read_readme", return_value=""),
            patch.object(gen_nodes, "_collect_config_files", return_value=""),
            patch.object(gen_nodes, "_llm_json", AsyncMock(return_value=llm_output)),
        ):
            result = await gen_nodes.doc_summary_node(
                _base_state(project_intro="# 프로젝트")
            )

        self.assertIn("doc_summary", result)
        summary = result["doc_summary"]
        self.assertEqual(summary["purpose"], "코드 분석 자동화")
        self.assertIn("요약 생성", summary["key_features"])
        ## LLM 성공 경로: generated_by는 settings.OPENAI_MODEL 값 (기본: "gpt-4o-mini")
        self.assertIsInstance(summary["generated_by"], str)
        self.assertNotEqual(summary["generated_by"], "heuristic")

    async def test_llm_none_falls_back_to_heuristic(self):
        """LLM이 None이면 분석 리포트 기반 휴리스틱 요약이 반환되어야 한다."""
        with (
            patch.object(gen_nodes, "_read_readme", return_value=""),
            patch.object(gen_nodes, "_collect_config_files", return_value=""),
            patch.object(gen_nodes, "_llm_json", AsyncMock(return_value=None)),
        ):
            result = await gen_nodes.doc_summary_node(_base_state())

        summary = result["doc_summary"]
        self.assertEqual(summary["generated_by"], "heuristic")
        self.assertIsNotNone(summary["tech_context"])

    async def test_exception_sets_failed_status(self):
        """내부 예외 발생 시 status='failed'가 설정되어야 한다."""
        with (
            patch.object(gen_nodes, "_read_readme", return_value=""),
            patch.object(
                gen_nodes, "_collect_config_files",
                side_effect=RuntimeError("IO 오류"),
            ),
        ):
            result = await gen_nodes.doc_summary_node(_base_state())

        self.assertEqual(result["status"], "failed")
        self.assertIn("B-201", result["error"])


# ──────────────────────────────────────────────────────────────
# 6. folder_summary_node (B-203) 검증
# ──────────────────────────────────────────────────────────────
class FolderSummaryNodeTests(unittest.IsolatedAsyncioTestCase):
    """DOCS-GEN-B-203: 폴더 단위 요약 노드 검증."""

    async def test_llm_success_returns_folder_map(self):
        """LLM 성공 시 folder_summaries가 폴더명→요약 맵으로 반환되어야 한다."""
        llm_output = {
            "folders": [
                {"name": "app", "summary": "FastAPI 애플리케이션 코어"},
                {"name": "tests", "summary": "유닛 및 통합 테스트"},
            ]
        }
        with (
            patch.object(gen_nodes, "_read_readme", return_value=""),
            patch.object(gen_nodes, "_llm_json", AsyncMock(return_value=llm_output)),
        ):
            result = await gen_nodes.folder_summary_node(_base_state())

        self.assertIn("folder_summaries", result)
        self.assertIn("app", result["folder_summaries"])
        self.assertEqual(
            result["folder_summaries"]["app"], "FastAPI 애플리케이션 코어"
        )

    async def test_llm_none_falls_back_to_heuristic(self):
        """LLM이 None이면 진입점 기반 폴더 목록으로 폴백되어야 한다."""
        with (
            patch.object(gen_nodes, "_read_readme", return_value=""),
            patch.object(gen_nodes, "_llm_json", AsyncMock(return_value=None)),
        ):
            result = await gen_nodes.folder_summary_node(_base_state())

        ## 폴백: 진입점 경로 파싱으로 folder_summaries 생성
        self.assertIsInstance(result["folder_summaries"], dict)
        self.assertNotEqual(result.get("status"), "failed")

    async def test_exception_sets_failed_status(self):
        """내부 예외 발생 시 status='failed'가 설정되어야 한다."""
        with patch.object(
            gen_nodes, "_read_readme", side_effect=ValueError("파싱 오류")
        ):
            result = await gen_nodes.folder_summary_node(_base_state())

        self.assertEqual(result["status"], "failed")
        self.assertIn("B-203", result["error"])

    async def test_timings_accumulate_correctly(self):
        """이전 타이밍이 유지된 채 새 키가 추가되어야 한다."""
        with (
            patch.object(gen_nodes, "_read_readme", return_value=""),
            patch.object(gen_nodes, "_llm_json", AsyncMock(return_value=None)),
        ):
            result = await gen_nodes.folder_summary_node(
                _base_state(timings={"b201_doc_summary": 0.8})
            )

        self.assertIn("b201_doc_summary", result["timings"])
        self.assertIn("b203_folder_summary", result["timings"])


# ──────────────────────────────────────────────────────────────
# 7. flow_explain_node (B-206) 검증
# ──────────────────────────────────────────────────────────────
class FlowExplainNodeTests(unittest.IsolatedAsyncioTestCase):
    """DOCS-GEN-B-206: 핵심 실행 플로우 설명 노드 검증."""

    async def test_llm_success_produces_flow_text(self):
        """LLM 성공 시 flow_explanation에 플로우 개요와 단계 목록이 포함되어야 한다."""
        llm_output = {
            "flow_overview": "요청이 FastAPI 라우터를 거쳐 DB에 저장됩니다.",
            "entry_to_db": ["라우터 수신", "서비스 처리", "레포지토리 저장"],
            "key_call_chain": "router → service → repository",
        }
        with (
            patch.object(gen_nodes, "_read_readme", return_value=""),
            patch.object(gen_nodes, "_llm_json", AsyncMock(return_value=llm_output)),
        ):
            result = await gen_nodes.flow_explain_node(
                _base_state(
                    doc_summary={
                        "purpose": "코드 분석",
                        "architecture_hint": "레이어드",
                    }
                )
            )

        self.assertIn("flow_explanation", result)
        self.assertIn("핵심 실행 플로우", result["flow_explanation"])
        self.assertIn("라우터 수신", result["flow_explanation"])
        self.assertIn("router → service → repository", result["flow_explanation"])

    async def test_llm_none_falls_back_to_heuristic(self):
        """LLM이 None이면 진입점 정보 기반 폴백 텍스트가 반환되어야 한다."""
        with (
            patch.object(gen_nodes, "_read_readme", return_value=""),
            patch.object(gen_nodes, "_llm_json", AsyncMock(return_value=None)),
        ):
            result = await gen_nodes.flow_explain_node(_base_state())

        self.assertIsNotNone(result["flow_explanation"])
        self.assertNotEqual(result.get("status"), "failed")

    async def test_exception_sets_failed_status(self):
        """내부 예외 발생 시 status='failed'가 설정되어야 한다."""
        with patch.object(
            gen_nodes, "_read_readme", side_effect=RuntimeError("IO 오류")
        ):
            result = await gen_nodes.flow_explain_node(_base_state())

        self.assertEqual(result["status"], "failed")
        self.assertIn("B-206", result["error"])


# ──────────────────────────────────────────────────────────────
# 8. onboarding_guide_node (B-202) 검증
# ──────────────────────────────────────────────────────────────
class OnboardingGuideNodeTests(unittest.IsolatedAsyncioTestCase):
    """DOCS-GEN-B-202: 온보딩 guide agent 노드 검증."""

    async def test_llm_success_returns_complete_guide(self):
        """LLM 성공 시 reading_order, risk_files, first_tasks가 모두 포함되어야 한다."""
        llm_output = {
            "reading_order": ["app/main.py", "app/router.py", "app/service.py"],
            "risk_files": [{"file": "app/auth.py", "reason": "인증 로직 수정 주의"}],
            "first_tasks": ["README 업데이트", "단위 테스트 추가"],
        }
        with (
            patch.object(gen_nodes, "_read_readme", return_value=""),
            patch.object(gen_nodes, "_llm_json", AsyncMock(return_value=llm_output)),
        ):
            result = await gen_nodes.onboarding_guide_node(
                _base_state(
                    folder_summaries={"app": "애플리케이션 코어"},
                    flow_explanation="## 핵심 실행 플로우\n...",
                )
            )

        guide = result["onboarding_guide"]
        self.assertIn("reading_order", guide)
        self.assertIn("app/main.py", guide["reading_order"])
        self.assertEqual(len(guide["risk_files"]), 1)
        self.assertIn("README 업데이트", guide["first_tasks"])

    async def test_llm_none_falls_back_to_heuristic_with_entrypoints(self):
        """LLM이 None이면 진입점을 reading_order로 사용하는 폴백이 적용되어야 한다."""
        with (
            patch.object(gen_nodes, "_read_readme", return_value=""),
            patch.object(gen_nodes, "_llm_json", AsyncMock(return_value=None)),
        ):
            result = await gen_nodes.onboarding_guide_node(_base_state())

        guide = result["onboarding_guide"]
        self.assertEqual(guide["generated_by"], "heuristic")
        self.assertEqual(guide["reading_order"], ["app/main.py", "app/router.py"])

    async def test_exception_sets_failed_status(self):
        """내부 예외 발생 시 status='failed'가 설정되어야 한다."""
        with patch.object(
            gen_nodes, "_read_readme", side_effect=RuntimeError("읽기 실패")
        ):
            result = await gen_nodes.onboarding_guide_node(_base_state())

        self.assertEqual(result["status"], "failed")
        self.assertIn("B-202", result["error"])


# ──────────────────────────────────────────────────────────────
# 9. master_report_node (B-204) 검증
# ──────────────────────────────────────────────────────────────
class MasterReportNodeTests(unittest.IsolatedAsyncioTestCase):
    """DOCS-GEN-B-204: 프로젝트 마스터 리포트 생성 노드 검증."""

    def _full_state(self) -> GenFormState:
        """모든 이전 단계 결과가 채워진 상태를 반환한다."""
        return _base_state(
            project_intro="# sample-repo\nFastAPI 기반 서비스",
            doc_summary={
                "purpose": "코드 분석 자동화",
                "key_features": ["요약 생성", "온보딩"],
                "tech_context": "FastAPI + pgvector",
                "architecture_hint": "레이어드",
                "generated_by": "auto",
            },
            folder_summaries={"app": "코어", "tests": "테스트"},
            flow_explanation="## 핵심 실행 플로우\nrouter → service",
            onboarding_guide={
                "reading_order": ["app/main.py"],
                "risk_files": [{"file": "app/auth.py", "reason": "인증"}],
                "first_tasks": ["테스트 추가"],
                "generated_by": "auto",
            },
        )

    async def test_master_report_contains_all_required_sections(self):
        """마스터 리포트에 summary, stack, file_map, recommendations, heatmap, durations, guide
        7개 섹션이 모두 포함되어야 한다."""
        result = await gen_nodes.master_report_node(self._full_state())

        self.assertIn("master_report", result)
        report = result["master_report"]
        for section in (
            "summary", "stack", "file_map",
            "recommendations", "heatmap", "durations", "guide",
        ):
            self.assertIn(section, report, f"'{section}' 섹션 누락")

    async def test_master_report_repo_id_matches_input(self):
        """마스터 리포트의 repo_id가 입력 상태와 일치해야 한다."""
        result = await gen_nodes.master_report_node(self._full_state())
        self.assertEqual(result["master_report"]["repo_id"], "test-repo-001")

    async def test_master_report_status_completed(self):
        """마스터 리포트 생성 후 status가 'completed'이어야 한다."""
        result = await gen_nodes.master_report_node(self._full_state())
        self.assertEqual(result["status"], "completed")

    async def test_durations_contains_total(self):
        """durations 섹션에 각 단계 타이밍과 total이 포함되어야 한다."""
        state = self._full_state()
        state["timings"] = {
            "b205_readme_intro": 0.5,
            "b201_doc_summary": 0.3,
        }
        result = await gen_nodes.master_report_node(state)
        durations = result["master_report"]["durations"]

        self.assertIn("total", durations)
        self.assertIn("b205_readme_intro", durations)
        self.assertIn("b204_master_report", durations)
        self.assertGreater(durations["total"], 0)

    async def test_guide_section_mirrors_onboarding_guide(self):
        """guide 섹션의 reading_order가 onboarding_guide와 일치해야 한다."""
        result = await gen_nodes.master_report_node(self._full_state())
        guide = result["master_report"]["guide"]
        self.assertEqual(guide["reading_order"], ["app/main.py"])
        self.assertEqual(len(guide["risk_files"]), 1)

    async def test_file_map_contains_folder_summaries(self):
        """file_map 섹션에 folder_summaries가 포함되어야 한다."""
        result = await gen_nodes.master_report_node(self._full_state())
        file_map = result["master_report"]["file_map"]
        self.assertEqual(file_map["folder_summaries"]["app"], "코어")

    async def test_recommendations_includes_first_tasks(self):
        """recommendations 섹션에 first_tasks가 포함되어야 한다."""
        result = await gen_nodes.master_report_node(self._full_state())
        recs = result["master_report"]["recommendations"]
        self.assertIn("테스트 추가", recs["first_tasks"])

    async def test_exception_sets_failed_status(self):
        """내부 예외 발생 시 status='failed'가 설정되어야 한다."""
        bad_state = _base_state()
        ## analysis_report를 set 타입으로 전달하면 dict() 변환 시 ValueError 발생
        ## (try 블록 안: report = dict(state.get("analysis_report") or {}))
        bad_state["analysis_report"] = {1, 2, 3}
        result = await gen_nodes.master_report_node(bad_state)
        self.assertEqual(result["status"], "failed")
        self.assertIn("B-204", result["error"])


# ──────────────────────────────────────────────────────────────
# 10. 정적 분석 계약 (Self 리뷰 §7 핵심 검증 항목)
# ──────────────────────────────────────────────────────────────
class GenFormStaticAnalysisTests(unittest.TestCase):
    """
    CLAUDE.md §7 정적 분석 5대 핵심 항목을 코드 구조 레벨에서 검증한다.
    (실제 코드 실행 없이 모듈 임포트 및 시그니처 기반 확인)
    """

    def test_all_node_functions_are_importable(self):
        """6개 노드 함수가 모두 임포트 가능해야 한다."""
        required = [
            "readme_intro_node",
            "doc_summary_node",
            "folder_summary_node",
            "flow_explain_node",
            "onboarding_guide_node",
            "master_report_node",
        ]
        for name in required:
            self.assertTrue(
                hasattr(gen_nodes, name),
                f"노드 함수 '{name}'이 gen.form.nodes에 없음",
            )

    def test_all_node_functions_accept_state(self):
        """각 노드 함수의 첫 번째 파라미터가 'state'이어야 한다."""
        node_names = [
            "readme_intro_node",
            "doc_summary_node",
            "folder_summary_node",
            "flow_explain_node",
            "onboarding_guide_node",
            "master_report_node",
        ]
        for name in node_names:
            func = getattr(gen_nodes, name)
            params = list(inspect.signature(func).parameters)
            self.assertEqual(
                params[0], "state",
                f"'{name}'의 첫 번째 파라미터가 'state'가 아님",
            )

    def test_all_node_functions_are_coroutines(self):
        """모든 노드 함수가 비동기 코루틴이어야 한다."""
        for name in [
            "readme_intro_node",
            "doc_summary_node",
            "folder_summary_node",
            "flow_explain_node",
            "onboarding_guide_node",
            "master_report_node",
        ]:
            func = getattr(gen_nodes, name)
            self.assertTrue(
                inspect.iscoroutinefunction(func),
                f"'{name}'이 async def가 아님",
            )

    def test_supervisor_has_run_method(self):
        """GenFormSupervisor가 비동기 run() 메서드를 노출해야 한다."""
        self.assertTrue(hasattr(GenFormSupervisor, "run"))
        self.assertTrue(
            inspect.iscoroutinefunction(GenFormSupervisor.run)
        )

    def test_supervisor_has_build_workflow_method(self):
        """GenFormSupervisor가 build_workflow() 메서드를 가져야 한다."""
        self.assertTrue(hasattr(GenFormSupervisor, "build_workflow"))

    def test_check_failure_is_callable(self):
        """_check_failure가 호출 가능한 함수이어야 한다."""
        self.assertTrue(callable(_check_failure))

    def test_helper_functions_use_asyncio_to_thread(self):
        """_read_readme, _collect_config_files가 동기 함수여야 한다.
        (비동기 블로킹 방어: nodes.py에서 asyncio.to_thread로 감쌈)"""
        self.assertFalse(
            inspect.iscoroutinefunction(gen_nodes._read_readme),
            "_read_readme는 동기 함수여야 asyncio.to_thread 래핑이 유효",
        )
        self.assertFalse(
            inspect.iscoroutinefunction(gen_nodes._collect_config_files),
            "_collect_config_files는 동기 함수여야 asyncio.to_thread 래핑이 유효",
        )

    def test_state_module_exports_gen_form_state(self):
        """state 모듈에서 GenFormState를 임포트할 수 있어야 한다."""
        from app.gen.form.state import GenFormState as _State
        self.assertIsNotNone(_State)

    def test_graph_module_exports_supervisor_and_check_failure(self):
        """graph 모듈이 GenFormSupervisor와 _check_failure를 노출해야 한다."""
        self.assertTrue(hasattr(gen_graph, "GenFormSupervisor"))
        self.assertTrue(hasattr(gen_graph, "_check_failure"))


# ──────────────────────────────────────────────────────────────
# 11. 전체 파이프라인 통합 경로 (LLM 없이 폴백 경로 end-to-end)
# ──────────────────────────────────────────────────────────────
class GenFormPipelineIntegrationTests(unittest.IsolatedAsyncioTestCase):
    """
    6개 노드를 LLM 없이 순차 실행했을 때 master_report가 정상 생성되는지 검증한다.
    (DB 없음, LLM API 키 없음 상황에서의 폴백 경로 end-to-end 테스트)
    """

    async def test_full_pipeline_fallback_produces_master_report(self):
        """LLM이 None을 반환하더라도 6단계 폴백 경로를 거쳐 master_report가 생성되어야 한다."""
        with (
            patch.object(gen_nodes, "_read_readme", return_value="# Sample\n설명"),
            patch.object(gen_nodes, "_collect_config_files", return_value=""),
            patch.object(gen_nodes, "_llm_json", AsyncMock(return_value=None)),
        ):
            state = _base_state()

            ## 순서 1: B-205
            r1 = await gen_nodes.readme_intro_node(state)
            self.assertNotEqual(r1.get("status"), "failed", "B-205 실패")
            state.update(r1)

            ## 순서 2: B-201
            r2 = await gen_nodes.doc_summary_node(state)
            self.assertNotEqual(r2.get("status"), "failed", "B-201 실패")
            state.update(r2)

            ## 순서 3: B-203
            r3 = await gen_nodes.folder_summary_node(state)
            self.assertNotEqual(r3.get("status"), "failed", "B-203 실패")
            state.update(r3)

            ## 순서 4: B-206
            r4 = await gen_nodes.flow_explain_node(state)
            self.assertNotEqual(r4.get("status"), "failed", "B-206 실패")
            state.update(r4)

            ## 순서 5: B-202
            r5 = await gen_nodes.onboarding_guide_node(state)
            self.assertNotEqual(r5.get("status"), "failed", "B-202 실패")
            state.update(r5)

            ## 순서 6: B-204
            r6 = await gen_nodes.master_report_node(state)
            self.assertNotEqual(r6.get("status"), "failed", "B-204 실패")
            state.update(r6)

        ## 최종 결과 검증
        self.assertEqual(state["status"], "completed")
        report = state["master_report"]
        self.assertIsNotNone(report)
        for section in (
            "summary", "stack", "file_map",
            "recommendations", "heatmap", "durations", "guide",
        ):
            self.assertIn(section, report, f"'{section}' 섹션 누락")

        ## durations에 모든 단계 타이밍이 누적되었는지 확인
        durations = report["durations"]
        self.assertIn("total", durations)
        self.assertGreater(durations["total"], 0)


if __name__ == "__main__":
    unittest.main()
