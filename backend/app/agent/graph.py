"""
CodeMap LangGraph 워크플로우 정의.

그래프 구조:
  planner_node
      → dispatcher_node (Send API 병렬 fan-out)
          → search_worker | dir_worker | grep_worker | read_worker
      → evaluator_node (fan-in: worker_results 자동 병합)

Application Layer (chat/service.py)는 이 그래프를 실행하고
반환된 State에서 compact_context와 worker_results를 읽어
Final Answer Agent에 전달합니다.
"""

from __future__ import annotations

from langgraph.graph import StateGraph, END

from app.agent.state import CodeMapState
from app.agent.nodes.planner_node import planner_node
from app.agent.nodes.dispatcher_node import dispatcher_node, fanout_to_workers
from app.agent.nodes.evaluator_node import evaluator_node
from app.agent.workers.search_worker import search_worker
from app.agent.workers.dir_worker import dir_worker
from app.agent.workers.grep_worker import grep_worker
from app.agent.workers.read_worker import read_worker


def route_after_evaluator(state: CodeMapState) -> str:
    """Continue planning when Evaluator requests more evidence within the retry limit."""
    decision = state.get("evaluator_decision") or {}
    replan_count = int(state.get("replan_count") or 0)
    max_replans = int(state.get("max_replans") or 0)
    # 한도 부등호 주의: evaluator_node는 *증가 전* 값으로 `replan_count < max_replans`를
    # 판정해 should_replan일 때만 replan_count를 +1 증가시키고 replan_hint를 설정한다.
    # 이 라우터는 그 *증가 후* 값을 읽으므로 `replan_count <= max_replans`가 맞다
    # ((count_before + 1) <= max  ⟺  count_before < max). 부등호가 다른 것은 비교 대상이
    # 증가 전/후로 다르기 때문이며 evaluator와 동일한 한도다(불일치 아님). replan_hint가
    # should_replan일 때만 설정되므로 사실상 단일 신호로 게이트된다.
    if decision.get("sufficient") is False and state.get("replan_hint") and replan_count <= max_replans:
        return "planner_node"
    return END


def build_graph() -> StateGraph:
    """
    CodeMap 멀티에이전트 LangGraph 워크플로우를 빌드합니다.

    반환된 graph는 .compile()로 실행 가능한 CompiledGraph가 됩니다.
    """
    builder = StateGraph(CodeMapState)

    # ── 노드 등록 ──────────────────────────────────────
    builder.add_node("planner_node", planner_node)
    builder.add_node("dispatcher_node", dispatcher_node)
    builder.add_node("search_worker", search_worker)
    builder.add_node("dir_worker", dir_worker)
    builder.add_node("grep_worker", grep_worker)
    builder.add_node("read_worker", read_worker)
    builder.add_node("evaluator_node", evaluator_node)

    # ── 엣지 연결 ──────────────────────────────────────
    # 시작: Planner → Dispatcher
    builder.set_entry_point("planner_node")
    builder.add_edge("planner_node", "dispatcher_node")

    # Dispatcher → Workers (Send API가 동적으로 처리 — conditional edge 사용)
    # dispatcher_node가 반환한 dict를 통해 상태 업데이트 후 fanout_to_workers 실행
    builder.add_conditional_edges(
        "dispatcher_node",
        fanout_to_workers,
        ["search_worker", "dir_worker", "grep_worker", "read_worker", "evaluator_node"],
    )

    # Workers → Evaluator (fan-in)
    # worker_results는 Annotated[list, operator.add]로 자동 병합됨
    builder.add_edge("search_worker", "evaluator_node")
    builder.add_edge("dir_worker", "evaluator_node")
    builder.add_edge("grep_worker", "evaluator_node")
    builder.add_edge("read_worker", "evaluator_node")

    # Evaluator → Planner 재계획 또는 END
    builder.add_conditional_edges(
        "evaluator_node",
        route_after_evaluator,
        {"planner_node": "planner_node", END: END},
    )

    return builder


# 모듈 로드 시 컴파일된 그래프 인스턴스 (싱글톤)
compiled_graph = build_graph().compile()
