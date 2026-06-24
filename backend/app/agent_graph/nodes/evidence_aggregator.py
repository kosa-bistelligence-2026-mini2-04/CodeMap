"""
Evidence Aggregator Node: 결정론적 코드 노드 (LLM 아님).

역할:
- worker_results 중복 제거
- 파일 경로 / 라인 기준 정렬
- token budget 내로 compact_context 생성
- Final Answer Agent가 소비할 수 있는 구조화된 근거 묶음 출력
"""

from __future__ import annotations

import logging
from collections import defaultdict

from app.agent_graph.state import CodeMapState, WorkerResult

logger = logging.getLogger(__name__)

_TOKEN_BUDGET = 12_000   # 대략 글자 수 기준 (1 token ≈ 4 chars)


def _deduplicate(results: list[WorkerResult]) -> list[WorkerResult]:
    """동일 파일 + 동일 content의 중복 결과 제거."""
    seen: set[tuple] = set()
    deduped: list[WorkerResult] = []
    for r in results:
        key = (r.get("file_path"), r.get("content", "")[:200])
        if key not in seen:
            seen.add(key)
            deduped.append(r)
    return deduped


def evidence_aggregator(state: CodeMapState) -> dict:
    """
    Evidence Aggregator Node.

    worker_results를 정제하여 compact_context를 생성합니다.
    """
    raw_results: list[WorkerResult] = state.get("worker_results", [])
    logger.info("[EvidenceAggregator] 시작 — 원본 결과 수=%d", len(raw_results))

    deduped = _deduplicate(raw_results)

    # 파일 경로 기준 그룹핑
    grouped: dict[str, list[WorkerResult]] = defaultdict(list)
    no_path: list[WorkerResult] = []
    for r in deduped:
        if r.get("file_path"):
            grouped[r["file_path"]].append(r)
        else:
            no_path.append(r)

    # token budget 내로 compact_context 구성
    snippets: list[dict] = []
    total_chars = 0

    for file_path, items in sorted(grouped.items()):
        for item in items:
            content = item.get("content", "")
            if total_chars + len(content) > _TOKEN_BUDGET:
                # 남은 budget만큼 잘라서 포함
                available = _TOKEN_BUDGET - total_chars
                if available > 100:
                    content = content[:available] + "\n... (budget 초과로 잘림)"
                else:
                    break
            snippets.append({
                "file": file_path,
                "worker": item.get("worker"),
                "query": item.get("query"),
                "content": content,
            })
            total_chars += len(content)

    # 파일 경로 없는 결과 (search 결과 등) 추가
    for item in no_path:
        content = item.get("content", "")
        if total_chars + len(content) > _TOKEN_BUDGET:
            available = _TOKEN_BUDGET - total_chars
            if available > 100:
                content = content[:available] + "\n... (budget 초과로 잘림)"
            else:
                break
        snippets.append({
            "file": None,
            "worker": item.get("worker"),
            "query": item.get("query"),
            "content": content,
        })
        total_chars += len(content)

    compact_context = {
        "total_results": len(raw_results),
        "deduplicated": len(deduped),
        "total_chars": total_chars,
        "snippets": snippets,
    }

    logger.info(
        "[EvidenceAggregator] 완료 — 스니펫=%d chars=%d",
        len(snippets), total_chars,
    )
    return {"compact_context": compact_context}
