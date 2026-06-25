"""Dir Worker: repository tree scan adapter."""

from __future__ import annotations

import asyncio
import logging
import uuid

from app.agent.state import CodeMapState, WorkerResult
from app.tool.dir_scan import scan_directory_tree

logger = logging.getLogger(__name__)


async def dir_worker(state: CodeMapState) -> dict:
    """Run a bounded directory scan for the current plan item."""
    item = state.get("_plan_item", {})
    rel_path = item.get("path", "")
    clone_path = state.get("clone_path", "")

    logger.info("[DirWorker] 시작 — path=%s", rel_path or ".")
    started_event = {"type": "worker_started", "worker": "dir", "target": rel_path or "."}
    content = await asyncio.to_thread(scan_directory_tree, clone_path, rel_path)
    if not content:
        return {"worker_results": [], "events": [
            started_event,
            {"type": "worker_result", "worker": "dir", "resultCount": 0, "evidenceIds": []},
        ]}

    result = WorkerResult(
        id=f"ev_{uuid.uuid4().hex[:8]}",
        path=rel_path or None,
        lineStart=None,
        lineEnd=None,
        score=None,
        snippet=content,
        metadata={"worker": "dir", "tool": "dir_scan", "query": rel_path},
    )
    return {
        "worker_results": [result],
        "events": [
            started_event,
            {
                "type": "worker_result",
                "worker": "dir",
                "resultCount": 1,
                "evidenceIds": [result["id"]],
            },
        ],
    }
