"""
Dispatcher Node: deterministic plan validation and worker fan-out.

The dispatcher is intentionally not an LLM agent. It enforces tool/path policy,
records the security result, and uses LangGraph Send for parallel routing.
"""

from __future__ import annotations

import logging
import re
from pathlib import PurePosixPath

from langgraph.types import Send
from app.agent.state import AccessPlanItem, CodeMapState

logger = logging.getLogger(__name__)

_ALLOWED_WORKERS = frozenset({"search", "dir", "grep", "read"})

_SENSITIVE_PATTERNS = re.compile(
    r"(\.env|id_rsa|id_ed25519|\.pem|\.key|\.p12|\.pfx|secret|password|credential)",
    re.IGNORECASE,
)

_ALLOWED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go", ".rs",
    ".md", ".txt", ".yaml", ".yml", ".toml", ".json", ".sh",
    ".html", ".css", ".sql", "",
}


def _is_safe_path(path: str | None) -> bool:
    """Block traversal, absolute paths, sensitive files, and unsupported extensions."""
    if path is None:
        return True
    if path.startswith("/") or ".." in PurePosixPath(path).parts:
        return False
    if _SENSITIVE_PATTERNS.search(path):
        return False
    suffix = PurePosixPath(path).suffix
    if suffix and suffix not in _ALLOWED_EXTENSIONS:
        return False
    return True


def dispatcher_node(state: CodeMapState) -> dict:
    """Validate access_plan and store approved/rejected entries."""
    plan: list[AccessPlanItem] = state.get("access_plan", [])
    approved: list[AccessPlanItem] = []
    rejected: list[AccessPlanItem] = []

    for item in plan:
        if _is_safe_path(item.get("path")):
            approved.append(item)
        else:
            logger.warning(
                "[Dispatcher] 보안 위반 — 거부된 plan: tool=%s path=%s",
                item.get("tool"), item.get("path"),
            )
            rejected.append(item)

    logger.info("[Dispatcher] 검증 완료 — 승인=%d 거부=%d", len(approved), len(rejected))
    groups = [[item.get("tool", "search")] for item in approved]

    return {
        "security_result": {"approved": approved, "rejected": rejected},
        "events": [{"type": "route_validated", "allowed": True, "parallelGroups": groups}],
    }


def fanout_to_workers(state: CodeMapState) -> list[Send]:
    """
    Conditional edge function that sends approved plan items to worker nodes.
    """
    approved = state.get("security_result", {}).get("approved", [])
    sends: list[Send] = []
    for item in approved:
        tool = item.get("tool", "search")
        if tool not in _ALLOWED_WORKERS:
            logger.warning("[Dispatcher] 미등록 도구 '%s' 차단", tool)
            continue
        sends.append(Send(f"{tool}_worker", {**state, "_plan_item": item}))

    if not sends:
        logger.warning("[Dispatcher] 승인된 plan 없음 — evaluator_node로 직행")
        sends.append(Send("evaluator_node", state))

    return sends
