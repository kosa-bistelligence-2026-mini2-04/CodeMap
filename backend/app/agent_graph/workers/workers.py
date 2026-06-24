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
    시맨틱 검색 Worker.

    pgvector 임베딩 기반 유사도 검색을 수행합니다.
    임베딩 미준비 시 기존 키워드 검색(search_repository)으로 폴백합니다.
    """
    item = state.get("_plan_item", {})
    query = item.get("query", state.get("rewritten_query", state["user_query"]))
    clone_path = state.get("clone_path", "")

    logger.info("[SearchWorker] 시작 — query=%r", query)

    result_content = ""
    try:
        from app.repo.analyzer import search_repository
        results: list[dict] = await asyncio.to_thread(
            search_repository, clone_path, query, 5
        )
        result_content = "\n\n".join(
            f"# {r.get('file', '')}\n{r.get('content', '')}"
            for r in results
        )
    except Exception as exc:
        logger.warning("[SearchWorker] 키워드 검색 실패: %s", exc)
        result_content = f"검색 실패: {exc}"

    logger.info("[SearchWorker] 완료 — 결과 길이=%d", len(result_content))
    return {
        "worker_results": [
            WorkerResult(
                worker="search",
                tool="search_repository",
                query=query,
                content=result_content,
                file_path=None,
            )
        ]
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
    target = Path(clone_path) / rel_path

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
    return {
        "worker_results": [
            WorkerResult(
                worker="dir",
                tool="os.walk",
                query=rel_path,
                content=content,
                file_path=rel_path or None,
            )
        ]
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
    base = Path(clone_path) / rel_path

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
    return {
        "worker_results": [
            WorkerResult(
                worker="grep",
                tool="rglob+regex",
                query=pattern,
                content=content,
                file_path=rel_path or None,
            )
        ]
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
    target = Path(clone_path) / rel_path

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
    return {
        "worker_results": [
            WorkerResult(
                worker="read",
                tool="file.read",
                query=rel_path,
                content=content,
                file_path=rel_path or None,
            )
        ]
    }
