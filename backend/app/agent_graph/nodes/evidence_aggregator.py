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
        key = (r.get("path"), r.get("snippet", "")[:200])
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
        if r.get("path"):
            grouped[r["path"]].append(r)
        else:
            no_path.append(r)

    # token budget 내로 compact_context 구성
    grouped_by_file: dict[str, list[dict]] = defaultdict(list)
    total_chars = 0
    selected_count = 0
    budget_exceeded = False

    for file_path, items in sorted(grouped.items()):
        for item in items:
            snippet = item.get("snippet", "")
            if total_chars + len(snippet) > _TOKEN_BUDGET:
                available = _TOKEN_BUDGET - total_chars
                if available > 100:
                    snippet = snippet[:available] + "\n... (budget 초과로 잘림)"
                    budget_exceeded = True
                else:
                    budget_exceeded = True
                    break

            grouped_by_file[file_path].append({
                "id": item.get("id"),
                "lineStart": item.get("lineStart"),
                "lineEnd": item.get("lineEnd"),
                "score": item.get("score"),
                "snippet": snippet,
                "metadata": item.get("metadata", {}),
            })
            total_chars += len(snippet)
            selected_count += 1
            if budget_exceeded:
                break
        if budget_exceeded:
            break

    # 파일 경로 없는 결과 추가
    if no_path and not budget_exceeded:
        for item in no_path:
            snippet = item.get("snippet", "")
            if total_chars + len(snippet) > _TOKEN_BUDGET:
                available = _TOKEN_BUDGET - total_chars
                if available > 100:
                    snippet = snippet[:available] + "\n... (budget 초과로 잘림)"
                    budget_exceeded = True
                else:
                    break

            grouped_by_file["no_path"].append({
                "id": item.get("id"),
                "lineStart": item.get("lineStart"),
                "lineEnd": item.get("lineEnd"),
                "score": item.get("score"),
                "snippet": snippet,
                "metadata": item.get("metadata", {}),
            })
            total_chars += len(snippet)
            selected_count += 1
            if budget_exceeded:
                break

    compact_context = {
        "selectedEvidenceCount": selected_count,
        "tokenBudget": _TOKEN_BUDGET,
        "usedTokens": total_chars // 4,  # 대략적인 토큰 수
        "groupedByFile": dict(grouped_by_file),
    }

    events = [{"type": "evidence_compacted", "evidenceCount": selected_count, "compactContextReady": True}]

    logger.info(
        "[EvidenceAggregator] 완료 — 스니펫=%d chars=%d",
        selected_count, total_chars,
    )
    return {"compact_context": compact_context, "events": events}
