"""Reciprocal Rank Fusion (RRF).

Combines several ranked id-lists into one ranking using only positions, not scores — which
makes it robust to the incomparable score scales of dense cosine and BM25. The same id
appearing in multiple lists has its contributions summed, so fusion also deduplicates.
"""

from __future__ import annotations

from collections import defaultdict
from typing import List, Optional, Sequence, Tuple


def reciprocal_rank_fusion(
    ranked_lists: Sequence[Sequence[int]],
    k: int = 60,
    weights: Optional[Sequence[float]] = None,
) -> List[Tuple[int, float]]:
    """Fuse ranked id-lists. Returns ``(id, score)`` sorted best-first."""
    if weights is None:
        weights = [1.0] * len(ranked_lists)
    scores: dict[int, float] = defaultdict(float)
    for ranked, weight in zip(ranked_lists, weights):
        for rank, item_id in enumerate(ranked):
            scores[item_id] += weight * (1.0 / (k + rank + 1))
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
