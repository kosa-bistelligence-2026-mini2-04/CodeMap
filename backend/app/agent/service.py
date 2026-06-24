"""
에이전트 실행 제어 및 LangGraph 워크플로우 기동을 담당하는 서비스.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import compiled_graph
from app.agent.state import CodeMapState
from app.infra.config import get_settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# CodeMap 에이전트 서비스 클래스
# ──────────────────────────────────────────────
class CodeMapAgentService:
    '''
    LangGraph 에이전트 워크플로우를 기동하고 실행 상태 및 이벤트를 제어합니다.
    '''

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    # ──────────────────────────────────────────────
    # 에이전트 동기/비동기 실행 메서드
    # ──────────────────────────────────────────────
    async def run_agent(
        self,
        repo_id: UUID,
        user_query: str,
        clone_path: str,
        mode: str = "quick",
    ) -> dict:
        '''
        LangGraph 워크플로우를 실행하고 최종 compact_context 및 worker_results를 반환합니다.
        '''
        try:
            initial_state: CodeMapState = {
                "user_query": user_query,
                "repo_id": str(repo_id),
                "clone_path": clone_path,
                "run_id": "",
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

            final_state = await compiled_graph.ainvoke(initial_state)
            logger.info(
                "[AgentService] 실행 완료 — worker_results=%d",
                len(final_state.get("worker_results", [])),
            )
            return {
                "worker_results": final_state.get("worker_results", []),
                "compact_context": final_state.get("compact_context", {}),
            }

        except Exception as exc:
            logger.warning(
                "[AgentService] 에이전트 실행 중 예외 발생: %s",
                exc,
            )
            raise exc

    # ──────────────────────────────────────────────
    # 에이전트 스트리밍 실행 메서드
    # ──────────────────────────────────────────────
    async def run_agent_stream(
        self,
        repo_id: UUID,
        user_query: str,
        clone_path: str,
        run_id: str,
    ) -> AsyncIterator[dict]:
        '''
        LangGraph 워크플로우를 스트리밍하여 실행 중간 이벤트를 발행합니다.
        '''
        initial_state: CodeMapState = {
            "user_query": user_query,
            "repo_id": str(repo_id),
            "clone_path": clone_path,
            "run_id": run_id,
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

        compact_context = {}
        worker_results = []

        async for output in compiled_graph.astream(initial_state):
            for node_name, state_update in output.items():
                if "events" in state_update:
                    for event in state_update["events"]:
                        yield event

                if "compact_context" in state_update:
                    compact_context = state_update["compact_context"]
                if "worker_results" in state_update:
                    worker_results.extend(state_update["worker_results"])

        yield {
            "type": "internal_state",
            "compact_context": compact_context,
            "worker_results": worker_results,
        }
