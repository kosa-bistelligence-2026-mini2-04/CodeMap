"""Grep Worker: repository regex scan adapter."""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from collections import defaultdict

from app.agent.state import CodeMapState, WorkerResult
from app.tool.grep_scan import grep_repository_path

logger = logging.getLogger(__name__)

## grep_repository_path 출력 형식: "{rel_path}:{lineno}: {line}"
_GREP_LINE_RE = re.compile(r"^(.+?):(\d+): ")


def _parse_grep_results(
    content: str,
    rel_path: str,
    pattern: str,
) -> list[WorkerResult]:
    """grep 출력을 파일별 WorkerResult로 변환한다. 라인 번호를 최대한 보존."""
    file_lines: dict[str, list[int]] = defaultdict(list)
    for line in content.splitlines():
        m = _GREP_LINE_RE.match(line)
        if m:
            file_lines[m.group(1)].append(int(m.group(2)))

    if not file_lines:
        ## 파싱 실패: 단일 결과, 라인 미확인
        return [WorkerResult(
            id=f"ev_{uuid.uuid4().hex[:8]}",
            path=rel_path or None,
            lineStart=None,
            lineEnd=None,
            score=None,
            snippet=content,
            metadata={"worker": "grep", "tool": "grep_scan", "query": pattern},
        )]

    results: list[WorkerResult] = []
    for file_path, lines in file_lines.items():
        results.append(WorkerResult(
            id=f"ev_{uuid.uuid4().hex[:8]}",
            path=file_path,
            lineStart=min(lines),
            lineEnd=max(lines),
            score=None,
            snippet=content,
            metadata={"worker": "grep", "tool": "grep_scan", "query": pattern},
        ))
    return results


async def grep_worker(state: CodeMapState) -> dict:
    """Run a bounded grep scan for the current plan item."""
    item = state.get("_plan_item") or {}
    pattern = item.get("query", "")
    rel_path = item.get("path", "")
    clone_path = state.get("clone_path", "")

    logger.info("[GrepWorker] 시작 — pattern=%r path=%s", pattern, rel_path or ".")
    started_event = {"type": "worker_started", "worker": "grep", "target": rel_path or "."}
    content = await asyncio.to_thread(grep_repository_path, clone_path, rel_path, pattern)
    if not content:
        return {"worker_results": [], "events": [
            started_event,
            {"type": "worker_result", "worker": "grep", "resultCount": 0, "evidenceIds": []},
        ]}

    results = _parse_grep_results(content, rel_path, pattern)
    return {
        "worker_results": results,
        "events": [
            started_event,
            {
                "type": "worker_result",
                "worker": "grep",
                "resultCount": len(results),
                "evidenceIds": [r["id"] for r in results],
            },
        ],
    }
