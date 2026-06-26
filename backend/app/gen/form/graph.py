"""
문서 생성 파이프라인 LangGraph 워크플로우 Supervisor

DOCS-GEN 내부 파이프라인(순서 1~6)을 LangGraph StateGraph로 오케스트레이션한다.
실행 순서: B-205 → B-201 → B-203 → B-206 → B-202 → B-204
"""

import logging
import time

from langgraph.graph import END, START, StateGraph

from app.gen.form.nodes import (
    doc_summary_node,
    flow_explain_node,
    folder_summary_node,
    master_report_node,
    onboarding_guide_node,
    readme_intro_node,
)
from app.gen.form.state import GenFormState

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# 실패 감지 조건부 라우팅 함수
# ──────────────────────────────────────────────
def _check_failure(state: GenFormState) -> str:
    '''
    각 노드 실행 후 실패 여부를 확인하여 다음 라우팅을 결정한다.

    상태가 "failed"이면 "failed"를 반환하여 END로 즉시 종료하고,
    정상이면 "success"를 반환하여 다음 노드로 진행한다.
    '''
    if state.get("status") == "failed":
        logger.warning(
            "[GenForm] 실패 감지 → 파이프라인 조기 종료 (error=%s)",
            state.get("error"),
        )
        return "failed"
    return "success"


# ──────────────────────────────────────────────
# 문서 생성 파이프라인 Supervisor
# ──────────────────────────────────────────────
class GenFormSupervisor:
    '''
    DOCS-GEN 문서 생성 파이프라인 워크플로우 Supervisor

    B-205 → B-201 → B-203 → B-206 → B-202 → B-204 순서로
    각 노드를 순차 실행하며, 실패 시 즉시 END 처리한다.
    '''

    def __init__(self) -> None:
        self.logger = logging.getLogger(
            f"{__name__}.GenFormSupervisor"
        )
        self.build_workflow()

    def build_workflow(self) -> None:
        '''LangGraph StateGraph로 문서 생성 파이프라인 워크플로우를 구성한다.'''
        graph = StateGraph(GenFormState)

        ## 노드 등록 (순서 1~6)
        graph.add_node("readme_intro", readme_intro_node)     ## B-205
        graph.add_node("doc_summary", doc_summary_node)       ## B-201
        graph.add_node("folder_summary", folder_summary_node) ## B-203
        graph.add_node("flow_explain", flow_explain_node)     ## B-206
        graph.add_node("onboarding_guide", onboarding_guide_node) ## B-202
        graph.add_node("master_report", master_report_node)   ## B-204

        ## 시작 엣지: START → B-205
        graph.add_edge(START, "readme_intro")

        ## 조건부 엣지: 실패 시 즉시 END, 성공 시 다음 노드
        graph.add_conditional_edges(
            "readme_intro",
            _check_failure,
            {"success": "doc_summary", "failed": END},
        )
        graph.add_conditional_edges(
            "doc_summary",
            _check_failure,
            {"success": "folder_summary", "failed": END},
        )
        graph.add_conditional_edges(
            "folder_summary",
            _check_failure,
            {"success": "flow_explain", "failed": END},
        )
        graph.add_conditional_edges(
            "flow_explain",
            _check_failure,
            {"success": "onboarding_guide", "failed": END},
        )
        graph.add_conditional_edges(
            "onboarding_guide",
            _check_failure,
            {"success": "master_report", "failed": END},
        )

        ## 최종 단계 종료
        graph.add_edge("master_report", END)

        self.work_flow = graph.compile()
        self.logger.info("문서 생성 파이프라인 워크플로우 컴파일 완료")

    async def run(self, initial_state: GenFormState) -> GenFormState:
        '''
        문서 생성 파이프라인 워크플로우를 실행한다.

        Args:
            initial_state: 파이프라인 초기 상태
                           (repo_id, clone_path, analysis_report 포함)

        Returns:
            최종 파이프라인 상태 (master_report, status, timings 등)
        '''
        repo_id = initial_state["repo_id"]
        _t0 = time.perf_counter()
        self.logger.info("[GenForm] 문서 생성 파이프라인 시작 (repo_id=%s)", repo_id)

        try:
            result = await self.work_flow.ainvoke(initial_state)
        except Exception:
            wall = time.perf_counter() - _t0
            self.logger.exception(
                "[GenForm] ainvoke 미처리 예외 (repo_id=%s, 경과=%.3f초)",
                repo_id, wall,
            )
            raise

        final_status = result.get("status", "UNKNOWN")
        wall = time.perf_counter() - _t0
        self.logger.info(
            "[GenForm] 문서 생성 파이프라인 종료"
            " (repo_id=%s, status=%s, 벽시계=%.3f초)",
            repo_id, final_status, wall,
        )

        if final_status == "failed":
            timings = result.get("timings", {})
            if timings:
                summary = " | ".join(
                    f"{k}={v:.3f}초" for k, v in timings.items()
                )
                self.logger.warning(
                    "[GenForm] 실패 시 소요시간 요약"
                    " repo=%s → %s | 벽시계=%.3f초",
                    repo_id, summary, wall,
                )

        return result
