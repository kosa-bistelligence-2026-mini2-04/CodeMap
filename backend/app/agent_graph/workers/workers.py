"""
Tool Workers: 단일 목적 코드 래퍼 / LLM 에이전트.

각 Worker는:
- 하나의 도구만 실행
- 결과를 요약하지 않고 Raw Data 그대로 State에 병합
- Command(update={"worker_results": [...]}) 패턴으로 fan-in

Workers:
- search_worker: LLM 기반 시맨틱 검색 (pgvector)
- dir_worker:    결정론적 코드 래퍼 — 디렉토리 구조 탐색
- grep_worker:   결정론적 코드 래퍼 — 키워드/정규식 검색
- read_worker:   결정론적 코드 래퍼 — 파일 내용 읽기
"""

from __future__ import annotations

import asyncio
import uuid
import logging
import os
import re
from pathlib import Path

from app.agent_graph.state import CodeMapState, WorkerResult

logger = logging.getLogger(__name__)

_MAX_FILE_SIZE = 50_000    # 50KB 초과 파일은 잘라 읽기
_MAX_GREP_RESULTS = 30     # grep 결과 최대 개수


# ─────────────────────────────────────────────
# Search Worker (LLM + pgvector)
# ─────────────────────────────────────────────

async def search_worker(state: CodeMapState) -> dict:
    """
    Hybrid Search Worker (pgvector 시맨틱 + BM25 + RRF).

    실행 전략:
    1. pgvector 시맨틱 검색 + BM25 재스코어링 + RRF 결합
    2. 실패/미준비 시 기존 키워드 검색(search_repository)으로 폴백

    State에서 repo_id를 읽어 DB에서 임베딩 벡터를 조회합니다.
    """
    item = state.get("_plan_item", {})
    query = item.get("query", state.get("rewritten_query", state["user_query"]))
    repo_id = state.get("repo_id", "")
    clone_path = state.get("clone_path", "")

    logger.info("[SearchWorker] 시작 — query=%r repo_id=%s", query, repo_id)

    worker_results: list[WorkerResult] = []

    # ── 1. Hybrid Search (pgvector + BM25 + RRF) ──
    try:
        from uuid import UUID as _UUID
        from app.core.database import async_session_factory
        from app.agent_graph.search.hybrid_search import hybrid_search

        async with async_session_factory() as db:
            hits = await hybrid_search(
                db=db,
                job_id=_UUID(repo_id),
                query=query,
                top_n=5,
            )

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
                        lineStart=None,
                        lineEnd=None,
                        score=rrf,
                        snippet=content,
                        metadata={
                            "worker": "search",
                            "tool": f"hybrid_search(sem={sem},bm25={bm},rrf={rrf:.4f})",
                            "query": query,
                        }
                    )
                )
            logger.info("[SearchWorker] Hybrid Search 완료 — %d 결과", len(hits))
            return {
                "worker_results": worker_results,
                "events": [{"type": "worker_result", "worker": "search", "resultCount": len(worker_results), "evidenceIds": [w["id"] for w in worker_results]}]
            }

    except Exception as exc:
        logger.info("[SearchWorker] Hybrid Search 실패/미준비, 키워드 폴백: %s", exc)

    # ── 2. 키워드 검색 폴백 ──
    try:
        from app.repo.analyzer import search_repository

        raw: list[dict] = await asyncio.to_thread(
            search_repository, clone_path, query, 5
        )
        for r in raw:
            snippet = r.get("snippet", "") or r.get("content", "")
            worker_results.append(
                WorkerResult(
                    id=f"ev_{uuid.uuid4().hex[:8]}",
                    path=r.get("file"),
                    lineStart=None,
                    lineEnd=None,
                    score=None,
                    snippet=snippet,
                    metadata={"worker": "search", "tool": "keyword_search", "query": query}
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
                metadata={"worker": "search", "tool": "fallback_failed", "query": query}
            )
        )

    return {
        "worker_results": worker_results,
        "events": [{"type": "worker_result", "worker": "search", "resultCount": len(worker_results), "evidenceIds": [w["id"] for w in worker_results]}]
    }



# ─────────────────────────────────────────────
# Dir Worker (결정론적 코드 래퍼)
# ─────────────────────────────────────────────

async def dir_worker(state: CodeMapState) -> dict:
    """
    디렉토리 구조 탐색 Worker.

    지정된 경로의 파일·폴더 구조를 트리 형태로 반환합니다.
    """
    item = state.get("_plan_item", {})
    rel_path = item.get("path", "")
    clone_path = state.get("clone_path", "")
    target = (Path(clone_path) / rel_path).resolve()
    if not str(target).startswith(str(Path(clone_path).resolve())):
        return {"worker_results": [], "events": []}

    logger.info("[DirWorker] 시작 — path=%s", target)

    lines: list[str] = []
    try:
        for root, dirs, files in os.walk(target):
            # 숨김 폴더 및 __pycache__ 제외
            dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
            depth = len(Path(root).relative_to(target).parts)
            indent = "  " * depth
            lines.append(f"{indent}{Path(root).name}/")
            for f in sorted(files):
                lines.append(f"{indent}  {f}")
            if len(lines) > 200:
                lines.append("... (truncated)")
                break
    except Exception as exc:
        logger.warning("[DirWorker] 탐색 실패: %s", exc)
        lines = [f"탐색 실패: {exc}"]

    content = "\n".join(lines)
    logger.info("[DirWorker] 완료 — 줄 수=%d", len(lines))
    wr = WorkerResult(
        id=f"ev_{uuid.uuid4().hex[:8]}",
        path=rel_path or None,
        lineStart=None,
        lineEnd=None,
        score=None,
        snippet=content,
        metadata={"worker": "dir", "tool": "os.walk", "query": rel_path}
    )
    return {
        "worker_results": [wr],
        "events": [{"type": "worker_result", "worker": "dir", "resultCount": 1, "evidenceIds": [wr["id"]]}]
    }


# ─────────────────────────────────────────────
# Grep Worker (결정론적 코드 래퍼)
# ─────────────────────────────────────────────

async def grep_worker(state: CodeMapState) -> dict:
    """
    키워드/정규식 검색 Worker.

    지정된 경로에서 패턴 매칭 결과를 반환합니다.
    """
    item = state.get("_plan_item", {})
    pattern = item.get("query", "")
    rel_path = item.get("path", "")
    clone_path = state.get("clone_path", "")
    base = (Path(clone_path) / rel_path).resolve()
    if not str(base).startswith(str(Path(clone_path).resolve())):
        return {"worker_results": [], "events": []}

    logger.info("[GrepWorker] 시작 — pattern=%r path=%s", pattern, base)

    matches: list[str] = []
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
        count = 0
        for fpath in sorted(base.rglob("*")):
            if not fpath.is_file() or fpath.stat().st_size > _MAX_FILE_SIZE:
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore")
                for lineno, line in enumerate(text.splitlines(), 1):
                    if compiled.search(line):
                        rel = fpath.relative_to(clone_path)
                        matches.append(f"{rel}:{lineno}: {line.strip()}")
                        count += 1
                        if count >= _MAX_GREP_RESULTS:
                            break
            except Exception:
                continue
            if count >= _MAX_GREP_RESULTS:
                break
    except re.error as exc:
        matches = [f"정규식 오류: {exc}"]

    content = "\n".join(matches) or "(결과 없음)"
    logger.info("[GrepWorker] 완료 — 매칭=%d", len(matches))
    wr = WorkerResult(
        id=f"ev_{uuid.uuid4().hex[:8]}",
        path=rel_path or None,
        lineStart=None,
        lineEnd=None,
        score=None,
        snippet=content,
        metadata={"worker": "grep", "tool": "rglob+regex", "query": pattern}
    )
    return {
        "worker_results": [wr],
        "events": [{"type": "worker_result", "worker": "grep", "resultCount": 1, "evidenceIds": [wr["id"]]}]
    }


# ─────────────────────────────────────────────
# Read Worker (결정론적 코드 래퍼)
# ─────────────────────────────────────────────

async def read_worker(state: CodeMapState) -> dict:
    """
    파일 내용 읽기 Worker.

    지정된 파일의 실제 소스코드를 반환합니다.
    """
    item = state.get("_plan_item", {})
    rel_path = item.get("path", "")
    clone_path = state.get("clone_path", "")
    target = (Path(clone_path) / rel_path).resolve()
    if not str(target).startswith(str(Path(clone_path).resolve())):
        return {"worker_results": [], "events": []}

    logger.info("[ReadWorker] 시작 — path=%s", target)

    try:
        text = target.read_text(encoding="utf-8", errors="ignore")
        if len(text) > _MAX_FILE_SIZE:
            text = text[:_MAX_FILE_SIZE] + f"\n... (파일 크기 초과, {_MAX_FILE_SIZE}자까지만 표시)"
        content = text
    except Exception as exc:
        logger.warning("[ReadWorker] 읽기 실패: %s", exc)
        content = f"파일 읽기 실패: {exc}"

    logger.info("[ReadWorker] 완료 — 길이=%d", len(content))
    wr = WorkerResult(
        id=f"ev_{uuid.uuid4().hex[:8]}",
        path=rel_path or None,
        lineStart=None,
        lineEnd=None,
        score=None,
        snippet=content,
        metadata={"worker": "read", "tool": "file.read", "query": rel_path}
    )
    return {
        "worker_results": [wr],
        "events": [{"type": "worker_result", "worker": "read", "resultCount": 1, "evidenceIds": [wr["id"]]}]
    }
