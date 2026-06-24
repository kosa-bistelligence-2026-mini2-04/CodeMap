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
from pathlib import Path, PurePosixPath

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


def _is_safe_path(path: str | None, clone_root: str = "") -> bool:
    """Path Traversal 공격 및 민감 파일 접근 차단."""
    if path is None:
        return True  # search 도구는 path 없음 → 안전
        
    # 민감 파일 패턴 차단
    if _SENSITIVE_PATTERNS.search(path):
        return False

    # 절대 경로 또는 상위 디렉토리 탐색 차단 & symlink 우회 방지
    if clone_root:
        try:
            target = Path(clone_root) / path
            # resolve() 후 clone_root 내에 위치하는지 검증
            if not target.resolve().is_relative_to(Path(clone_root).resolve()):
                return False
        except Exception:
            return False
    else:
        # clone_root가 제공되지 않은 경우 단순 문자열 기반 차단
        if path.startswith("/") or ".." in PurePosixPath(path).parts:
            return False
            
    return True


def route_node(state: CodeMapState) -> dict:
    """
    Route Node.

    access_plan을 검증 후 승인된 계획을 State에 반영합니다.
    (실제 라우팅은 graph.py의 조건부 엣지에서 수행)
    """
    plan: list[AccessPlanItem] = state.get("access_plan", [])
    clone_path = state.get("clone_path", "")
    approved: list[AccessPlanItem] = []
    rejected: list[AccessPlanItem] = []

    for item in plan:
        if _is_safe_path(item.get("path"), clone_root=clone_path):
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

    return {"security_result": {"approved": approved, "rejected": rejected}}
