"""
CodeMap LangGraph 워크플로우 정의.

그래프 구조:
  supervisor_agent
      → route_node (Send API 병렬 fan-out)
          → search_worker | dir_worker | grep_worker | read_worker
      → evidence_aggregator (fan-in: worker_results 자동 병합)

Application Layer (chat/service.py)는 이 그래프를 실행하고
반환된 State에서 compact_context와 worker_results를 읽어
Final Answer Agent에 전달합니다.
"""

from __future__ import annotations

from langgraph.graph import StateGraph, END

from app.agent_graph.state import CodeMapState
from app.agent_graph.agents.supervisor_agent import supervisor_node
from app.agent_graph.nodes.route_node import route_node
from app.agent_graph.nodes.evidence_aggregator import evidence_aggregator
from app.agent_graph.workers.workers import (
    search_worker,
    dir_worker,
    grep_worker,
    read_worker,
)


def build_graph() -> StateGraph:
    """
    CodeMap 멀티에이전트 LangGraph 워크플로우를 빌드합니다.

    반환된 graph는 .compile()로 실행 가능한 CompiledGraph가 됩니다.
    """
    builder = StateGraph(CodeMapState)

    # ── 노드 등록 ──────────────────────────────────────
    builder.add_node("supervisor_agent", supervisor_node)
    builder.add_node("route_node", route_node)
    builder.add_node("search_worker", search_worker)
    builder.add_node("dir_worker", dir_worker)
    builder.add_node("grep_worker", grep_worker)
    builder.add_node("read_worker", read_worker)
    builder.add_node("evidence_aggregator", evidence_aggregator)

    # ── 엣지 연결 ──────────────────────────────────────
    # 시작: Supervisor → Route Node
    builder.set_entry_point("supervisor_agent")
    builder.add_edge("supervisor_agent", "route_node")

    # Route Node → Workers (Send API가 동적으로 처리 — conditional edge 사용)
    # route_node가 반환한 dict를 통해 상태 업데이트 후 fanout_to_workers 실행
    from app.agent_graph.nodes.route_node import fanout_to_workers
    builder.add_conditional_edges("route_node", fanout_to_workers, ["search_worker", "dir_worker", "grep_worker", "read_worker", "evidence_aggregator"])

    # Workers → Evidence Aggregator (fan-in)
    # worker_results는 Annotated[list, operator.add]로 자동 병합됨
    builder.add_edge("search_worker", "evidence_aggregator")
    builder.add_edge("dir_worker", "evidence_aggregator")
    builder.add_edge("grep_worker", "evidence_aggregator")
    builder.add_edge("read_worker", "evidence_aggregator")

    # Evidence Aggregator → END
    builder.add_edge("evidence_aggregator", END)

    return builder


# 모듈 로드 시 컴파일된 그래프 인스턴스 (싱글톤)
compiled_graph = build_graph().compile()
