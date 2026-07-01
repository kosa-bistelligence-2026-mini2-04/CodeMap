"""
Dispatcher Node: deterministic plan validation and worker fan-out.

The dispatcher is intentionally not an LLM agent. It enforces tool/path policy,
records the security result, and uses LangGraph Send for parallel routing.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

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


def _is_safe_path(path: str | None, clone_root: str | None = None) -> bool:
    """Block traversal, absolute paths, sensitive files, and unsupported extensions."""
    if path is None:
        return True
    normalized = path.replace("\\", "/")
    if normalized.startswith("/") or re.match(r"^[a-zA-Z]:", normalized):
        return False
    posix_path = PurePosixPath(normalized)
    if ".." in posix_path.parts:
        return False
    if _SENSITIVE_PATTERNS.search(normalized):
        return False
    suffix = posix_path.suffix
    if suffix and suffix not in _ALLOWED_EXTENSIONS:
        return False
    if clone_root:
        root = Path(clone_root).resolve()
        candidate = (root / normalized).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            return False
    return True


def _dedup_signature(tool: str, path: str | None, query: str | None) -> str:
    """탐색 중복 방지 키 (tool, target).

    search는 `query`, grep은 `path+query`, dir/read는 `path`가 탐색 대상이다.
    grep에서 path를 누락하면 같은 패턴을 다른 파일/디렉터리에 적용하는 탐색까지
    중복으로 오판해 검색 기능이 막히므로 target에 path를 함께 포함한다.
    """
    normalized_path = (path or "").strip().replace("\\", "/")
    normalized_query = (query or "").strip()
    if tool == "search":
        target = normalized_query
    elif tool == "grep":
        target = f"{normalized_path}\0{normalized_query}"
    else:
        target = normalized_path
    target_str = (target or "").strip().replace("\\", "/")
    return f"{tool}:{target_str}"


def dispatcher_node(state: CodeMapState) -> dict:
    """Validate access_plan, drop duplicate searches, and store approved/rejected entries."""
    plan: list[AccessPlanItem] = state.get("access_plan", [])
    approved: list[AccessPlanItem] = []
    rejected: list[AccessPlanItem] = []

    # 이전 반복(단계)에서 이미 수행한 (tool, target) 집합 을 누적 state에서 추출.
    # 같은 path/query에 대한 탐색 시도는 결정론적으로 스킵합니다(프롬프트 soft 지시 보강).
    executed: set[str] = set(state.get("attempted_signatures") or [])
    for result in state.get("worker_results", []):
        meta = result.get("metadata") or {}
        worker = meta.get("worker")
        if worker:
            executed.add(_dedup_signature(
                worker,
                meta.get("path") or result.get("path"),
                meta.get("query"),
            ))

    seen: set[str] = set()  # 단일 plan 내 중복을 1회로 잡는 용도
    duplicates = 0

    for item in plan:
        if not _is_safe_path(item.get("path"), state.get("clone_path")):
            logger.warning(
                "[Dispatcher] 보안 위반 — 거부된 plan: tool=%s path=%s",
                item.get("tool"), item.get("path"),
            )
            rejected.append(item)
            continue

        signature = _dedup_signature(item.get("tool", "search"), item.get("path"), item.get("query"))
        if signature in executed or signature in seen:
            duplicates += 1
            logger.info(
                "[Dispatcher] 중복 탐색 스킵 : %s", signature,
            )
            continue
        seen.add(signature)
        approved.append(item)

    logger.info(
        "[Dispatcher] 검증 완료 — 승인=%d 거부=%d 중복스킵=%d",
        len(approved), len(rejected), duplicates,
    )
    groups = [[item.get("tool", "search")] for item in approved]

    return {
        "security_result": {"approved": approved, "rejected": rejected},
        "attempted_signatures": list(seen),
        "events": [{
            "type": "route_validated",
            "allowed": len(approved) > 0,
            "parallelGroups": groups,
            "dedupedCount": duplicates,
        }],
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
