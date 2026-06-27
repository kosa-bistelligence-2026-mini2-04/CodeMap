"""
Hybrid Search: pgvector 시맨틱 검색 + BM25 키워드 검색 → RRF(Reciprocal Rank Fusion) 결합.

알고리즘:
  1. Semantic Search (pgvector cosine distance) — top-K 후보 추출
  2. BM25 Keyword Search (rank_bm25 라이브러리) — 동일 후보 풀에서 재스코어링
  3. RRF 점수 = Σ 1/(k + rank_i) 로 두 순위 병합 (k=60, DeepMind/Okapi 표준)

폴백 전략:
  - pgvector 임베딩 미준비 또는 OPENAI_API_KEY 미설정 → 빈 리스트 반환 (caller에서 폴백)
  - rank_bm25 미설치 → 시맨틱 검색 순위만 단독 사용
  - 모두 실패 → 빈 리스트 반환 (caller에서 키워드 검색 폴백)

외부 의존성(sqlalchemy, openai)은 모두 lazy import로 처리합니다.
순수 함수(rrf_score, bm25_rank)는 app.agent.tools.rrf에서 임포트합니다.
"""

from __future__ import annotations

import logging
from uuid import UUID

from app.tool.rrf import bm25_rank as _bm25_rank, rrf_score as _rrf_score

logger = logging.getLogger(__name__)

_SEMANTIC_K = 20     # pgvector top-K 후보 수
_HYBRID_TOP_N = 5    # 최종 반환 결과 수


# ─────────────────────────────────────────────────────
# _semantic_search 제거됨 (app.embed.service.vector_search로 대체)
# ─────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────

async def hybrid_search(
    db,           # AsyncSession (lazy import 호환)
    job_id: UUID,
    query: str,
    top_n: int = _HYBRID_TOP_N,
) -> list[dict]:
    """
    Hybrid Search (pgvector + BM25 + RRF).

    반환: top_n개 결과 목록
    [{"file_path", "content", "summary", "rrf_score", "semantic_rank", "bm25_rank", "start_line"}]
    start_line은 코드 청크 시작 라인 번호. DB에 없으면 None.

    폴백 전략:
      - 시맨틱 결과 없으면 → 빈 리스트 반환 (caller에서 키워드 검색 폴백)
      - BM25 미설치 → 시맨틱 순위만 사용하여 RRF 계산
    """
    try:
        from app.embed.service import vector_search, embed_ready
        
        # 0. embed_ready 가드
        if not await embed_ready(db, job_id):
            logger.info("[HybridSearch] 레포지토리 임베딩 미준비 — 키워드 검색으로 즉시 폴백")
            return []

        # 1. 시맨틱 검색 (단일 진입점 사용)
        vector_results = await vector_search(db, job_id, query, k=_SEMANTIC_K)
        if not vector_results:
            logger.info("[HybridSearch] 시맨틱 결과 없음 — 빈 리스트 반환 (caller 폴백)")
            return []
            
        semantic_results = []
        for rank, res in enumerate(vector_results, 1):
            semantic_results.append({
                "node_id": f"dummy_{rank}", # vector_search에서 node_id를 주지 않으므로 더미값
                "file_path": res.get("file", ""),
                "content": res.get("snippet", ""),
                "summary": "",  # vector_search가 summary를 주지 않으므로 빈 문자열
                "distance": 1.0 - res.get("score", 0.0),
                "rank": rank,
                "start_line": res.get("line"),  ## chunk start_line (None이면 null 유지)
            })
            
    except Exception as exc:
        logger.warning("[HybridSearch] 시맨틱 검색 연동 실패: %s", exc)
        return []

    # 2. BM25 재스코어링 (시맨틱 후보 풀을 corpus로 사용)
    #    summary가 비어있어도 content 만으로 충분히 동작
    corpus = [r["content"] + " " + r["summary"] for r in semantic_results]
    bm25_ranked = _bm25_rank(corpus, query, top_n=len(semantic_results))

    # BM25 rank 매핑: original_index → rank (1-indexed)
    bm25_rank_map: dict[int, int] = {
        idx: rank for rank, (idx, _) in enumerate(bm25_ranked, 1)
    }

    # 3. RRF 점수 계산 및 정렬
    fused: list[dict] = []
    for i, result in enumerate(semantic_results):
        sem_rank = result["rank"]       # 1-indexed
        bm_rank = bm25_rank_map.get(i)  # None if BM25 미설치
        rrf = _rrf_score(sem_rank, bm_rank)
        fused.append({
            **result,
            "rrf_score": rrf,
            "semantic_rank": sem_rank,
            "bm25_rank": bm_rank,
        })

    fused.sort(key=lambda x: x["rrf_score"], reverse=True)
    top = fused[:top_n]

    logger.info(
        "[HybridSearch] RRF 완료 — 후보=%d 반환=%d",
        len(fused), len(top),
    )
    return top
