"""
에이전트 실행 제어 및 LangGraph 워크플로우 기동을 담당하는 서비스.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import get_compiled_graph
from app.agent.state import CodeMapState
from app.chat.repository import ChatRepository
from app.infra.config import get_settings
from langchain_core.runnables import RunnableConfig

logger = logging.getLogger(__name__)
_MEMORY_MESSAGE_LIMIT = 8
_MEMORY_CONTENT_LIMIT = 700

_MAX_REPLAN_CAP = 3


def _bounded_max_replans(raw_value: int | str | None) -> int:
    """Clamp configured re-plan retries so a bad env value cannot overload the graph."""
    try:
        value = int(raw_value if raw_value is not None else 2)
    except (TypeError, ValueError):
        value = 2
    return max(0, min(value, _MAX_REPLAN_CAP))


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
        self.max_replans = _bounded_max_replans(getattr(self.settings, "AGENT_MAX_REPLANS", 2))

    # ──────────────────────────────────────────────
    # 에이전트 동기/비동기 실행 메서드
    # ──────────────────────────────────────────────
    async def run_agent(
        self,
        repo_id: UUID,
        user_query: str,
        clone_path: str,
        mode: str = "quick",
        session_id: UUID | None = None,
        target_file: str | None = None,
    ) -> dict:
        '''
        LangGraph 워크플로우를 실행하고 최종 compact_context 및 worker_results를 반환합니다.
        '''
        try:
            initial_state = await self._build_initial_state(
                repo_id=repo_id,
                user_query=user_query,
                clone_path=clone_path,
                run_id="",
                session_id=session_id,
                target_file=target_file,
            )
            final_state = await get_compiled_graph().ainvoke(
                initial_state,
                config=self._graph_config(session_id=session_id, run_id=""),
            )
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

    async def _build_initial_state(
        self,
        repo_id: UUID,
        user_query: str,
        clone_path: str,
        run_id: str,
        session_id: UUID | None,
        target_file: str | None = None,
    ) -> CodeMapState:
        memory_context = await self._load_memory_context(repo_id, session_id, current_query=user_query)
        return {
                "user_query": user_query,
                "repo_id": str(repo_id),
                "clone_path": clone_path,
                "run_id": run_id,
                "session_id": str(session_id) if session_id else None,
                "target_file": target_file,
                "memory_context": memory_context,
                "rewritten_query": "",
                "_plan_item": None,
                "access_plan": [],
                "security_result": {"approved": [], "rejected": []},
                "worker_results": [],
                "events": [],
                "errors": [],
                "durations": {},
                "compact_context": {},
                "evaluator_decision": None,
                "replan_count": 0,
                "max_replans": self.max_replans,
                "replan_hint": None,
                "final_answer": None,
            }

    async def _load_memory_context(
        self,
        repo_id: UUID,
        session_id: UUID | None,
        *,
        current_query: str = "",
    ) -> dict:
        """Restore recent DB-backed conversation context for the current session."""
        if not session_id:
            return {"messages": [], "messageCount": 0}

        messages = await ChatRepository(self.db).list_messages(repo_id, session_id)
        if messages and messages[-1].role == "user" and messages[-1].content.strip() == current_query.strip():
            messages = messages[:-1]
        recent = messages[-_MEMORY_MESSAGE_LIMIT:]
        return {
            "sessionId": str(session_id),
            "messageCount": len(messages),
            "messages": [
                {
                    "role": message.role,
                    "content": message.content[:_MEMORY_CONTENT_LIMIT],
                    "mode": message.mode,
                    "referenceCount": len(message.references or []),
                }
                for message in recent
            ],
        }

    def _graph_config(self, *, session_id: UUID | None, run_id: str) -> RunnableConfig | None:
        thread_id = str(session_id) if session_id else run_id
        return RunnableConfig(configurable={"thread_id": thread_id}) if thread_id else None

    # ──────────────────────────────────────────────
    # 에이전트 스트리밍 실행 메서드
    # ──────────────────────────────────────────────
    async def run_agent_stream(
        self,
        repo_id: UUID,
        user_query: str,
        clone_path: str,
        run_id: str,
        session_id: UUID | None = None,
        target_file: str | None = None,
    ) -> AsyncIterator[dict]:
        '''
        LangGraph 워크플로우를 스트리밍하여 실행 중간 이벤트를 발행합니다.
        '''
        initial_state = await self._build_initial_state(
            repo_id=repo_id,
            user_query=user_query,
            clone_path=clone_path,
            run_id=run_id,
            session_id=session_id,
            target_file=target_file,
        )

        compact_context = {}
        worker_results = []

        async for output in get_compiled_graph().astream(
            initial_state,
            config=self._graph_config(session_id=session_id, run_id=run_id),
        ):
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
