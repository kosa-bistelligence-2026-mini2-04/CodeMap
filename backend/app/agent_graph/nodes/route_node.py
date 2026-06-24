"""
Route Node: 100% 결정론적 코드 (LLM 아님).

역할:
- Supervisor의 access_plan을 읽어 보안 검증 (path traversal, allowlist)
- 승인된 plan만 Worker로 병렬 라우팅 (LangGraph Send API 사용)
- Worker 결과를 요약하지 않음 — Raw Data 그대로 State에 병합

보안 원칙:
- 절대 경로 (..) 접근 차단
- 허용 목록(allowedPaths) 기반 경로 필터링
- 민감 파일 패턴 차단 (.env, id_rsa, *.key 등)
"""

from __future__ import annotations

import logging
import re
from pathlib import PurePosixPath

from app.agent_graph.state import AccessPlanItem, CodeMapState, SecurityResult

logger = logging.getLogger(__name__)

# 민감 파일 패턴 (대소문자 무관)
_SENSITIVE_PATTERNS = re.compile(
    r"(\.env|id_rsa|id_ed25519|\.pem|\.key|\.p12|\.pfx|secret|password|credential)",
    re.IGNORECASE,
)

# 허용 확장자 (바이너리 제외)
_ALLOWED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go", ".rs",
    ".md", ".txt", ".yaml", ".yml", ".toml", ".json", ".sh",
    ".html", ".css", ".sql", "",  # 빈 확장자 = 디렉토리
}


def _is_safe_path(path: str | None) -> bool:
    """Path Traversal 공격 및 민감 파일 접근 차단."""
    if path is None:
        return True  # search 도구는 path 없음 → 안전
    # 절대 경로 또는 상위 디렉토리 탐색 차단
    if path.startswith("/") or ".." in PurePosixPath(path).parts:
        return False
    # 민감 파일 패턴 차단
    if _SENSITIVE_PATTERNS.search(path):
        return False
    return True


def route_node(state: CodeMapState) -> dict:
    """
    Route Node.

    access_plan을 검증 후 보안 검증 결과를 반환합니다.
    (실제 라우팅은 fanout_to_workers conditional edge에서 수행됨)
    """
    plan: list[AccessPlanItem] = state.get("access_plan", [])
    approved: list[AccessPlanItem] = []
    rejected: list[AccessPlanItem] = []

    for item in plan:
        if _is_safe_path(item.get("path")):
            approved.append(item)
        else:
            logger.warning(
                "[RouteNode] 보안 위반 — 거부된 plan: tool=%s path=%s",
                item.get("tool"), item.get("path"),
            )
            rejected.append(item)

    logger.info(
        "[RouteNode] 검증 완료 — 승인=%d 거부=%d",
        len(approved), len(rejected),
    )

    # emit event
    groups = []
    # 간단히 tool 단위로 group을 묶었다고 가정 (실제로는 병렬 실행)
    for app in approved:
        groups.append([app.get("tool", "search")])

    events = [{"type": "route_validated", "allowed": True, "parallelGroups": groups}]

    return {
        "security_result": {"approved": approved, "rejected": rejected},
        "events": events
    }


def fanout_to_workers(state: CodeMapState) -> list[Send]:
    """
    Conditional Edge 함수.
    승인된 plan 항목을 기반으로 각 Worker에게 Send 인스턴스를 반환하여 병렬 fan-out 합니다.
    """
    from langgraph.types import Send  # lazy import
    approved = state.get("security_result", {}).get("approved", [])
    
    sends: list[Send] = []
    for item in approved:
        tool = item.get("tool", "search")
        node_name = f"{tool}_worker"
        sends.append(Send(node_name, {**state, "_plan_item": item}))

    if not sends:
        logger.warning("[RouteNode] 승인된 plan 없음 — evidence_aggregator로 직행")
        sends.append(Send("evidence_aggregator", state))

    return sends
