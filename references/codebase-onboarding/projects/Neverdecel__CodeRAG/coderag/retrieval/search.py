"""Hybrid searcher: dense + lexical retrieval fused with RRF, hydrated from the store."""

from __future__ import annotations

import logging
from typing import Dict, List

from coderag.config import Config
from coderag.embeddings import EmbeddingProvider
from coderag.retrieval.fusion import reciprocal_rank_fusion
from coderag.store.sqlite_store import SQLiteStore
from coderag.store.vector_index import FaissVectorIndex
from coderag.types import SearchHit

logger = logging.getLogger(__name__)


class HybridSearcher:
    def __init__(
        self,
        config: Config,
        provider: EmbeddingProvider,
        store: SQLiteStore,
        vectors: FaissVectorIndex,
    ) -> None:
        self.config = config
        self.provider = provider
        self.store = store
        self.vectors = vectors

    def search(self, query: str, top_k: int) -> List[SearchHit]:
        if not query or not query.strip():
            return []

        fetch_k = max(self.config.fetch_k, top_k)

        # Dense retrieval.
        qvec = self.provider.embed_query(query)
        dense_ids, dense_scores = self.vectors.search(qvec, fetch_k)
        similarity: Dict[int, float] = {
            int(i): float(max(0.0, min(1.0, s)))
            for i, s in zip(dense_ids, dense_scores)
        }
        dense_ranked = [int(i) for i in dense_ids]

        # Lexical retrieval (BM25 over FTS5).
        lexical_ranked = [cid for cid, _ in self.store.fts_search(query, fetch_k)]

        # Fuse and trim.
        fused = reciprocal_rank_fusion(
            [dense_ranked, lexical_ranked],
            k=self.config.rrf_k,
            weights=[self.config.dense_weight, self.config.lexical_weight],
        )[:top_k]
        if not fused:
            return []

        ids = [cid for cid, _ in fused]
        rows = self.store.hydrate(ids)

        hits: List[SearchHit] = []
        for cid, score in fused:
            row = rows.get(cid)
            if row is None:
                continue
            hits.append(
                SearchHit(
                    chunk_id=cid,
                    path=row["path"],
                    symbol=row["symbol"],
                    kind=row["kind"],
                    language=row["language"],
                    start_line=int(row["start_line"]),
                    end_line=int(row["end_line"]),
                    text=row["text"],
                    score=float(score),
                    similarity=similarity.get(cid, 0.0),
                )
            )
        return hits
