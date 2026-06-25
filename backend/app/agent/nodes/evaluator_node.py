"""
Evaluator Node: deterministic evidence aggregation for Phase 1.

Phase 1 evaluates evidence by deduplicating, grouping, and compacting it into
compact_context. Phase 2 can add LLM sufficiency decisions on top of this node.
"""

from __future__ import annotations

import logging
from collections import defaultdict

from app.agent.state import CodeMapState, WorkerResult

logger = logging.getLogger(__name__)

_TOKEN_BUDGET = 12_000


def _deduplicate(results: list[WorkerResult]) -> list[WorkerResult]:
    """Remove duplicate evidence by file path and snippet prefix."""
    seen: set[tuple] = set()
    deduped: list[WorkerResult] = []
    for result in results:
        key = (result.get("path"), result.get("snippet", "")[:200])
        if key not in seen:
            seen.add(key)
            deduped.append(result)
    return deduped


def evaluator_node(state: CodeMapState) -> dict:
    """Build compact_context from raw worker_results."""
    raw_results: list[WorkerResult] = state.get("worker_results", [])
    logger.info("[Evaluator] 시작 — 원본 결과 수=%d", len(raw_results))

    deduped = _deduplicate(raw_results)
    grouped: dict[str, list[WorkerResult]] = defaultdict(list)
    no_path: list[WorkerResult] = []
    for result in deduped:
        if result.get("path"):
            grouped[result["path"]].append(result)
        else:
            no_path.append(result)

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
        "usedTokens": total_chars // 4,
        "groupedByFile": dict(grouped_by_file),
    }

    logger.info("[Evaluator] 완료 — 스니펫=%d chars=%d", selected_count, total_chars)
    return {
        "compact_context": compact_context,
        "events": [{
            "type": "evidence_compacted",
            "evidenceCount": selected_count,
            "compactContextReady": True,
        }],
    }
