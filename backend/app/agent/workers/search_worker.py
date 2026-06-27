"""Search Worker: hybrid search plus keyword fallback."""

from __future__ import annotations

import asyncio
import logging
import uuid
from uuid import UUID

from app.agent.state import CodeMapState, WorkerResult

logger = logging.getLogger(__name__)


async def search_worker(state: CodeMapState) -> dict:
    """
    Run hybrid search for the current plan item and append raw evidence.
    """
    item = state.get("_plan_item") or {}
    query = item.get("query", state.get("rewritten_query", state["user_query"]))
    repo_id = state.get("repo_id", "")
    clone_path = state.get("clone_path", "")

    logger.info("[SearchWorker] 시작 — query=%r repo_id=%s", query, repo_id)
    worker_results: list[WorkerResult] = []

    try:
        from app.infra.database import async_session_factory
        from app.tool.hybrid_search import hybrid_search

        async with async_session_factory() as db:
            hits = await hybrid_search(db=db, job_id=UUID(repo_id), query=query, top_n=5)

        if hits:
            for hit in hits:
                file_path = hit.get("file_path", "")
                content = hit.get("content", "") or hit.get("summary", "")
                rrf = hit.get("rrf_score", 0.0)
                sem = hit.get("semantic_rank")
                bm = hit.get("bm25_rank")
                worker_results.append(
                    WorkerResult(
                        id=f"ev_{uuid.uuid4().hex[:8]}",
                        path=file_path or None,
                        lineStart=hit.get("start_line"),
                        lineEnd=None,
                        score=rrf,
                        snippet=content,
                        metadata={
                            "worker": "search",
                            "tool": f"hybrid_search(sem={sem},bm25={bm},rrf={rrf:.4f})",
                            "query": query,
                        },
                    )
                )
            logger.info("[SearchWorker] Hybrid Search 완료 — %d 결과", len(hits))
            return _worker_event(worker_results, target=query)

    except Exception as exc:
        logger.info("[SearchWorker] Hybrid Search 실패/미준비, 키워드 폴백: %s", exc)

    try:
        from app.repo.analyzer import search_repository

        raw: list[dict] = await asyncio.to_thread(search_repository, clone_path, query, 5)
        for result in raw:
            snippet = result.get("snippet", "") or result.get("content", "")
            worker_results.append(
                WorkerResult(
                    id=f"ev_{uuid.uuid4().hex[:8]}",
                    path=result.get("file"),
                    lineStart=None,
                    lineEnd=None,
                    score=None,
                    snippet=snippet,
                    metadata={"worker": "search", "tool": "keyword_search", "query": query},
                )
            )
        logger.info("[SearchWorker] 키워드 폴백 — %d 결과", len(raw))
    except Exception as exc:
        logger.warning("[SearchWorker] 키워드 검색도 실패: %s", exc)
        worker_results.append(
            WorkerResult(
                id=f"ev_{uuid.uuid4().hex[:8]}",
                path=None,
                lineStart=None,
                lineEnd=None,
                score=None,
                snippet=f"검색 실패: {exc}",
                metadata={"worker": "search", "tool": "fallback_failed", "query": query},
            )
        )

    return _worker_event(worker_results, target=query)


def _worker_event(worker_results: list[WorkerResult], target: str | None = None) -> dict:
    return {
        "worker_results": worker_results,
        "events": [
            {"type": "worker_started", "worker": "search", "target": target},
            {
                "type": "worker_result",
                "worker": "search",
                "resultCount": len(worker_results),
                "evidenceIds": [result["id"] for result in worker_results],
            },
        ],
    }
