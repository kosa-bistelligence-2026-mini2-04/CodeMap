"""
분석 파이프라인 워크플로우 Supervisor

# [Sec09 - CustomerSupportSupervisor]
# kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/supervisor.py 참고
#
# LangGraph StateGraph를 사용하여 파이프라인 단계 간 흐름을 명시적으로 정의한다.
# 실습의 CustomerSupportSupervisor 구조를 CodeMap 분석 파이프라인에 맞게 적용했다.
#
# 차이점:
#   실습 (Sec09): analysis → user_info/knowledge(병렬) → gather → 조건부 전문가 Agent
#   CodeMap:     clone → code_map → doc_gen → onboarding → report (순차)
#                각 단계 실패 시 add_conditional_edges로 즉시 END 처리
"""

import logging

from langgraph.graph import END, START, StateGraph

from app.repo.pipeline.nodes import (
    clone_node,
    code_map_node,
    doc_gen_node,
    onboarding_node,
    report_node,
)
from app.repo.pipeline.state import PipelineState
from app.repo.schemas import JobStatus

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# 조건부 라우팅 함수
#
# [Sec09 - route_node_fun]
# kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/nodes/route_node.py 참고
# 실습에서 문의 유형으로 분기하는 라우팅 함수를 실패 감지 용도로 적용했다.
# ──────────────────────────────────────────────────────────────

def _check_failure(state: PipelineState) -> str:
    """
    각 노드 실행 후 실패 여부를 확인하여 다음 라우팅을 결정한다.

    # [Sec09 - route_node_fun]
    # kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/nodes/route_node.py 참고
    # 실패(FAILED) 상태면 "failed"를 반환하여 END로 즉시 종료한다.
    # 정상 상태면 "success"를 반환하여 다음 파이프라인 단계로 진행한다.

    Returns:
        "failed": FAILED 상태 → END 라우팅
        "success": 정상 상태 → 다음 노드 라우팅
    """
    if state.get("status") == JobStatus.FAILED.value:
        logger.warning(
            f"[Pipeline] 실패 감지 → 파이프라인 조기 종료 "
            f"(error={state.get('error')})"
        )
        return "failed"
    return "success"


# ──────────────────────────────────────────────────────────────
# 분석 파이프라인 Supervisor
#
# [Sec09 - CustomerSupportSupervisor]
# kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/supervisor.py 참고
# ──────────────────────────────────────────────────────────────

class AnalysisPipelineSupervisor:
    """
    CodeMap 분석 파이프라인 워크플로우 Supervisor

    # [Sec09 - CustomerSupportSupervisor]
    # kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/supervisor.py 참고
    #
    # CLONE → CODE_MAP → DOC_GEN → ONBOARDING → REPORT 순서로 파이프라인을 실행하며,
    # 각 단계 실패 시 add_conditional_edges로 즉시 END 처리한다.
    #
    # 실습과의 차이:
    #   실습: 병렬 노드(user_info + knowledge) + 조건부 전문가 라우팅
    #   CodeMap: 순차 단계 실행 + 실패 시 조건부 조기 종료
    """

    def __init__(self) -> None:
        self.logger = logging.getLogger(
            f"{__name__}.AnalysisPipelineSupervisor"
        )
        # [Sec09 - __init__] 초기화 시 워크플로우 컴파일
        self.build_workflow()

    def build_workflow(self) -> None:
        """
        LangGraph StateGraph로 분석 파이프라인 워크플로우를 구성한다.

        # [Sec09 - build_workflow]
        # supervisor.py의 build_workflow() 구조 그대로 적용
        # 1. 노드 등록 → 2. 엣지 정의 → 3. 컴파일
        """
        # [Sec09 - StateGraph] 파이프라인 상태 그래프 초기화
        graph = StateGraph(PipelineState)

        # 1. [Sec09 - add_node] 각 파이프라인 단계를 노드로 등록
        graph.add_node("clone", clone_node)
        graph.add_node("code_map", code_map_node)
        graph.add_node("doc_gen", doc_gen_node)
        graph.add_node("onboarding", onboarding_node)
        graph.add_node("report", report_node)

        # 2. [Sec09 - add_edge] 시작 노드 설정 (START → clone)
        graph.add_edge(START, "clone")

        # 3. [Sec09 - add_conditional_edges] 각 단계 완료 후 실패 감지 및 조건부 라우팅
        #    실습에서 문의 유형별 전문 Agent로 분기하던 것을 실패/성공 분기에 적용
        graph.add_conditional_edges(
            "clone",
            _check_failure,
            {"success": "code_map", "failed": END},
        )
        graph.add_conditional_edges(
            "code_map",
            _check_failure,
            {"success": "doc_gen", "failed": END},
        )
        graph.add_conditional_edges(
            "doc_gen",
            _check_failure,
            {"success": "onboarding", "failed": END},
        )
        graph.add_conditional_edges(
            "onboarding",
            _check_failure,
            {"success": "report", "failed": END},
        )

        # 4. [Sec09 - add_edge] 최종 단계 종료 (report → END)
        graph.add_edge("report", END)

        # 5. [Sec09 - graph.compile()] 워크플로우 컴파일
        self.work_flow = graph.compile()
        self.logger.info("분석 파이프라인 워크플로우 컴파일 완료")

    async def run(self, initial_state: PipelineState) -> PipelineState:
        """
        분석 파이프라인 워크플로우를 실행한다.

        # [Sec09 - work_flow.ainvoke()]
        # supervisor.run()의 ainvoke() 호출 패턴 그대로 적용

        Args:
            initial_state: 파이프라인 초기 상태 (job_id, repo 메타데이터 등)

        Returns:
            최종 파이프라인 상태 (status, progress, error 등)
        """
        self.logger.info(
            f"파이프라인 시작 (job_id={initial_state['job_id']})"
        )
        # [Sec09 - ainvoke] 비동기 워크플로우 실행
        result = await self.work_flow.ainvoke(initial_state)
        self.logger.info(
            f"파이프라인 종료 "
            f"(job_id={initial_state['job_id']}, status={result.get('status')})"
        )
        return result
