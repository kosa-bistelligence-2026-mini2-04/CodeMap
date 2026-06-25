"""Repository-grounded conversational service — LangGraph 멀티에이전트 연동."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import AsyncIterator
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repository import ChatRepository
from app.chat.schemas import ChatRunRequest
from app.infra.config import get_settings
from app.repo.repository import AnalysisJobRepository

logger = logging.getLogger(__name__)


class RepositoryChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_repository = ChatRepository(db)
        self.job_repository = AnalysisJobRepository(db)
        self.settings = get_settings()

    async def prepare(
        self,
        repo_id: UUID,
        request: ChatRunRequest,
        *,
        commit_user_message: bool = True,
    ):
        """스레드 생성, 사용자 메시지 저장 후 job/thread/mode를 반환."""
        job = await self.job_repository.get_job_by_id(repo_id)
        if not job:
            raise ValueError("분석 프로젝트를 찾을 수 없습니다.")
        clone_path = Path(self.settings.CLONE_BASE_DIR) / str(repo_id) / "repo"
        if not clone_path.exists():
            raise ValueError("저장소 스냅샷이 아직 준비되지 않았습니다.")

        thread = await self.chat_repository.get_or_create_thread(
            repo_id,
            request.sessionId,
            request.question.strip().replace("\n", " ")[:72],
        )
        await self.chat_repository.add_message(thread, "user", request.question, request.mode)
        if commit_user_message:
            await self.db.commit()
        else:
            await self.db.flush()
        return job, thread, request.mode, str(clone_path)

    async def prepare_run_context(self, repo_id: UUID, request: ChatRunRequest):
        """Run 생성 요청에서 DB 메시지 쓰기 없이 분석 job과 clone 경로만 검증한다."""
        job = await self.job_repository.get_job_by_id(repo_id)
        if not job:
            raise ValueError("분석 프로젝트를 찾을 수 없습니다.")
        clone_path = Path(self.settings.CLONE_BASE_DIR) / str(repo_id) / "repo"
        if not clone_path.exists():
            raise ValueError("저장소 스냅샷이 아직 준비되지 않았습니다.")
        return job, request.mode, str(clone_path)

    async def run_agent(
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
          - compact_context: Evaluator가 생성한 token budget 내 근거 묶음
        """
        try:
            from app.agent.service import CodeMapAgentService

            agent_service = CodeMapAgentService(self.db)
            return await agent_service.run_agent(
                repo_id=repo_id,
                user_query=user_query,
                clone_path=clone_path,
                mode=mode,
            )

        except Exception as exc:
            # LangGraph 실패 시 기존 키워드 검색으로 폴백
            logger.warning(
                "[ChatService] agent 실패, 키워드 검색 폴백: %s", exc
            )
            return await self._keyword_search_fallback(user_query, clone_path, mode)

    async def _keyword_search_fallback(self, user_query: str, clone_path: str, mode: str) -> dict:
        from app.repo.analyzer import search_repository

        raw_results: list[dict] = await asyncio.to_thread(search_repository, clone_path, user_query, 5)
        worker_results = []
        grouped_by_file: dict[str, list[dict]] = {}
        for result in raw_results:
            snippet = result.get("snippet", "") or result.get("content", "")
            file_path = result.get("file") or "no_path"
            worker_result = {
                "id": f"ev_{uuid4().hex[:8]}",
                "path": None if file_path == "no_path" else file_path,
                "lineStart": None,
                "lineEnd": None,
                "score": None,
                "snippet": snippet,
                "metadata": {
                    "worker": "search",
                    "tool": "keyword_search_fallback",
                    "query": user_query,
                    "mode": mode,
                },
            }
            worker_results.append(worker_result)
            grouped_by_file.setdefault(file_path, []).append({
                "id": worker_result["id"],
                "lineStart": None,
                "lineEnd": None,
                "score": None,
                "snippet": snippet,
                "metadata": worker_result["metadata"],
            })

        total_chars = sum(len(item["snippet"]) for item in worker_results)
        return {
            "worker_results": worker_results,
            "compact_context": {
                "selectedEvidenceCount": len(worker_results),
                "tokenBudget": 12_000,
                "usedTokens": total_chars // 4,
                "groupedByFile": grouped_by_file,
            },
        }

    async def run_agent_stream(
        self,
        repo_id: UUID,
        user_query: str,
        clone_path: str,
        run_id: str,
    ) -> AsyncIterator[dict]:
        from app.agent.service import CodeMapAgentService

        agent_service = CodeMapAgentService(self.db)
        async for event in agent_service.run_agent_stream(
            repo_id=repo_id,
            user_query=user_query,
            clone_path=clone_path,
            run_id=run_id,
        ):
            yield event

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
        from app.chat.final_answer_agent import stream_final_answer

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
        references = [
            {"file": r.get("path", ""), "line": 0, "snippet": r.get("snippet", "")[:200]}
            for r in worker_results
            if r.get("path")
        ]
        await self.chat_repository.add_message(thread, "assistant", answer, mode, references)
        await self.db.commit()
