"""Repository-grounded conversational service — LangGraph 멀티에이전트 연동."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repository import ChatRepository
from app.chat.schemas import ChatRequest
from app.core.config import get_settings
from app.repo.repository import AnalysisJobRepository

logger = logging.getLogger(__name__)


class RepositoryChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_repository = ChatRepository(db)
        self.job_repository = AnalysisJobRepository(db)
        self.settings = get_settings()

    async def prepare(self, repo_id: UUID, request: ChatRequest):
        """스레드 생성, 사용자 메시지 저장 후 job/thread/mode를 반환."""
        job = await self.job_repository.get_job_by_id(repo_id)
        if not job:
            raise ValueError("분석 프로젝트를 찾을 수 없습니다.")
        clone_path = Path(self.settings.CLONE_BASE_DIR) / str(repo_id) / "repo"
        if not clone_path.exists():
            raise ValueError("저장소 스냅샷이 아직 준비되지 않았습니다.")

        thread = await self.chat_repository.get_or_create_thread(
            repo_id,
            request.threadId,
            request.message.strip().replace("\n", " ")[:72],
        )
        mode = "quick" if request.mode == "fast" else request.mode
        await self.chat_repository.add_message(thread, "user", request.message, mode)
        await self.db.commit()
        return job, thread, mode, str(clone_path)

    async def run_agent_graph(
        self,
        repo_id: UUID,
        user_query: str,
        clone_path: str,
        mode: str = "quick",
    ) -> dict:
        """
        LangGraph 멀티에이전트 워크플로우를 실행하고 최종 State를 반환.

        반환값:
          - worker_results: 각 Worker가 수집한 원본 결과 목록
          - compact_context: Evidence Aggregator가 생성한 token budget 내 근거 묶음
        """
        try:
            from app.agent_graph.graph import compiled_graph
            from app.agent_graph.state import CodeMapState

            initial_state: CodeMapState = {
                "user_query": user_query,
                "repo_id": str(repo_id),
                "clone_path": clone_path,
                "rewritten_query": "",
                "access_plan": [],
                "security_result": {"approved": [], "rejected": []},
                "worker_results": [],
                "compact_context": {},
                "final_answer": None,
            }

            # LangGraph invoke (비동기)
            final_state = await compiled_graph.ainvoke(initial_state)
            logger.info(
                "[ChatService] agent_graph 실행 완료 — worker_results=%d",
                len(final_state.get("worker_results", [])),
            )
            return {
                "worker_results": final_state.get("worker_results", []),
                "compact_context": final_state.get("compact_context", {}),
            }

        except Exception as exc:
            # LangGraph 실패 시 기존 키워드 검색으로 폴백
            logger.warning(
                "[ChatService] agent_graph 실패, 키워드 검색 폴백: %s", exc
            )
            return await self._keyword_search_fallback(user_query, clone_path, mode)

    async def _keyword_search_fallback(
        self, query: str, clone_path: str, mode: str
    ) -> dict:
        """
        LangGraph 미설치 또는 실패 시 기존 search_repository 키워드 검색 폴백.
        worker_results / compact_context 형식에 맞춰 변환하여 반환합니다.
        """
        from app.repo.analyzer import search_repository

        raw: list[dict] = await asyncio.to_thread(
            search_repository,
            clone_path,
            query,
            10 if mode == "deep" else 5,
        )

        # 기존 참조 형식 → WorkerResult 형식 변환
        worker_results = [
            {
                "worker": "search",
                "tool": "keyword_search",
                "query": query,
                "content": f"{item.get('snippet', '')}",
                "file_path": item.get("file"),
            }
            for item in raw
        ]

        # 동일한 compact_context 형식 구성
        compact_context = {
            "total_results": len(raw),
            "deduplicated": len(raw),
            "total_chars": sum(len(r["content"]) for r in worker_results),
            "snippets": [
                {
                    "file": item.get("file"),
                    "worker": "search",
                    "query": query,
                    "content": item.get("snippet", ""),
                }
                for item in raw
            ],
        }
        return {"worker_results": worker_results, "compact_context": compact_context}

    def stream_answer(
        self,
        repo_name: str,
        user_query: str,
        compact_context: dict,
        worker_results: list[dict],
        mode: str = "quick",
    ) -> AsyncIterator[dict]:
        """
        Final Answer Agent — SSE 이벤트 딕셔너리 스트림을 반환.

        router에서 json.dumps() 후 SSE 포맷으로 전송합니다.
        """
        from app.agent_graph.agents.final_answer_agent import stream_final_answer

        return stream_final_answer(
            repo_name=repo_name,
            user_query=user_query,
            compact_context=compact_context,
            worker_results=worker_results,
            mode=mode,
        )

    async def persist_answer(
        self,
        thread,
        answer: str,
        mode: str,
        worker_results: list[dict],
    ) -> None:
        """어시스턴트 응답과 참조 파일 목록을 DB에 저장."""
        # 기존 references 형식으로 변환 (file_path가 있는 Worker 결과만)
        references = [
            {"file": r.get("file_path", ""), "line": 0, "snippet": r.get("content", "")[:200]}
            for r in worker_results
            if r.get("file_path")
        ]
        await self.chat_repository.add_message(thread, "assistant", answer, mode, references)
        await self.db.commit()
