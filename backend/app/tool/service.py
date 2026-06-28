"""
MCP-style 외부 도구 Job 실행 서비스.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.state import WorkerResult
from app.infra.config import get_settings
from app.repo.repository import AnalysisJobRepository
from app.tool.ast_quality_tool import calculate_ast_quality
from app.tool.dir_scan import scan_directory_tree
from app.tool.file_read import read_repository_file
from app.tool.grep_scan import grep_repository_path
from app.tool.hybrid_search import hybrid_search

logger = logging.getLogger(__name__)

_SUPPORTED_TOOLS = frozenset({"vector_search", "file_read", "dir_scan", "grep_scan", "ast_quality"})


# ──────────────────────────────────────────────
# CodeMap 도구 서비스 클래스
# ──────────────────────────────────────────────
class CodeMapToolService:
    '''
    {tool_name, arguments} 기반의 JSON Job을 실행하는 MCP-style I/O 인터페이스입니다.
    '''

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    # ──────────────────────────────────────────────
    # 도구 Job 실행 메서드
    # ──────────────────────────────────────────────
    async def execute_job(
        self,
        job_id: UUID,
        run_id: UUID,
        tool_name: str,
        arguments: dict,
    ) -> dict:
        '''
        MCP-style JSON Job을 내부 결정론적 tool helper에 연결합니다.
        '''
        if tool_name not in _SUPPORTED_TOOLS:
            raise ValueError(f"지원하지 않는 tool_name입니다: {tool_name}")

        logger.info(
            "[ToolService] Job 실행 — tool=%s, run_id=%s",
            tool_name,
            run_id,
        )

        if tool_name == "vector_search":
            results = await self._execute_vector_search(job_id, tool_name, arguments)
        elif tool_name == "ast_quality":
            results = await self._execute_ast_quality(job_id, tool_name, arguments)
        else:
            results = self._execute_filesystem_tool(job_id, tool_name, arguments)

        return {
            "code": 200,
            "message": "success",
            "status": "success",
            "data": {
                "jobId": str(job_id),
                "runId": str(run_id),
                "toolName": tool_name,
                "results": results,
            },
        }

    async def _execute_vector_search(self, job_id: UUID, tool_name: str, arguments: dict) -> list[WorkerResult]:
        query = str(arguments.get("query") or "").strip()
        if not query:
            return []

        top_n = int(arguments.get("top_n") or 5)
        hits = await hybrid_search(db=self.db, job_id=job_id, query=query, top_n=top_n)
        return [
            WorkerResult(
                id=f"ev_{uuid.uuid4().hex[:8]}",
                path=hit.get("file_path") or None,
                lineStart=None,
                lineEnd=None,
                score=hit.get("rrf_score"),
                snippet=hit.get("content", "") or hit.get("summary", ""),
                metadata={
                    "worker": "search",
                    "tool": tool_name,
                    "query": query,
                    "semanticRank": hit.get("semantic_rank"),
                    "bm25Rank": hit.get("bm25_rank"),
                },
            )
            for hit in hits
        ]

    def _execute_filesystem_tool(self, job_id: UUID, tool_name: str, arguments: dict) -> list[WorkerResult]:
        clone_path = Path(self.settings.CLONE_BASE_DIR) / str(job_id) / "repo"
        rel_path = str(arguments.get("path") or "")

        if tool_name == "file_read":
            snippet = read_repository_file(str(clone_path), rel_path)
            worker = "read"
        elif tool_name == "dir_scan":
            snippet = scan_directory_tree(str(clone_path), rel_path)
            worker = "dir"
        elif tool_name == "grep_scan":
            pattern = str(arguments.get("query") or arguments.get("pattern") or "")
            snippet = grep_repository_path(str(clone_path), rel_path, pattern)
            worker = "grep"
        else:  # pragma: no cover - guarded by _SUPPORTED_TOOLS
            raise ValueError(f"지원하지 않는 tool_name입니다: {tool_name}")

        if not snippet:
            return []

        return [
            WorkerResult(
                id=f"ev_{uuid.uuid4().hex[:8]}",
                path=rel_path or None,
                lineStart=None,
                lineEnd=None,
                score=None,
                snippet=snippet,
                metadata={
                    "worker": worker,
                    "tool": tool_name,
                    "query": arguments.get("query") or arguments.get("pattern") or rel_path,
                },
            )
        ]


    async def _execute_ast_quality(self, job_id: UUID, tool_name: str, arguments: dict) -> list[WorkerResult]:
        clone_path = Path(self.settings.CLONE_BASE_DIR) / str(job_id) / "repo"
        rel_path = str(arguments.get("path") or "")

        metrics = await asyncio.to_thread(calculate_ast_quality, str(clone_path), rel_path)

        repo = AnalysisJobRepository(self.db)
        job = await repo.get_job_by_id(job_id)
        if job:
            report = dict(job.report_json or {})
            if "health_metrics" not in report:
                report["health_metrics"] = {}
            report["health_metrics"]["complexity"] = metrics.get("complexity", 50)
            report["health_metrics"]["modularity"] = metrics.get("modularity", 50)
            await repo.update_job_status(job_id=job_id, status=job.status, report_json=report)
            await self.db.commit()

        snippet = f"Complexity Score: {metrics.get('complexity', 50)}\nModularity Score: {metrics.get('modularity', 50)}"

        return [
            WorkerResult(
                id=f"ev_{uuid.uuid4().hex[:8]}",
                path=rel_path or None,
                lineStart=None,
                lineEnd=None,
                score=None,
                snippet=snippet,
                metadata={
                    "worker": "ast",
                    "tool": tool_name,
                    "complexity": metrics.get("complexity", 50),
                    "modularity": metrics.get("modularity", 50),
                },
            )
        ]
