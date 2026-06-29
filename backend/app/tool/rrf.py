"""
RRF(Reciprocal Rank Fusion) 및 BM25 순수 함수 — 외부 의존성 없음.

이 모듈은 DB나 네트워크 의존성 없이 단독 테스트 가능합니다.
"""

from __future__ import annotations


_RRF_K = 60


def rrf_score(semantic_rank: int | None, bm25_rank: int | None, k: int = _RRF_K) -> float:
    """
    Reciprocal Rank Fusion 점수 계산.

    RRF(r) = Σ 1/(k + rank_i)
    둘 다 있으면 합산, 없으면 0.

    Args:
        semantic_rank: pgvector 유사도 순위 (1-indexed, None이면 시맨틱 검색 제외)
        bm25_rank:     BM25 순위 (1-indexed, None이면 BM25 제외)
        k:             안정화 상수 (기본값 60, DeepMind/Okapi 표준)
    """
    score = 0.0
    if semantic_rank is not None:
        score += 1.0 / (k + semantic_rank)
    if bm25_rank is not None:
        score += 1.0 / (k + bm25_rank)
    return score


def bm25_rank(corpus: list[str], query: str, top_n: int = 5) -> list[tuple[int, float]]:
    """
    BM25Okapi 스코어링으로 corpus 내 관련 문서 순위 반환.

    Args:
        corpus: 검색 대상 텍스트 목록
        query:  검색 쿼리
        top_n:  반환할 최대 결과 수

    Returns:
        [(original_index, score)] top_n개 (내림차순)
        rank_bm25 미설치 시 빈 리스트 반환 (graceful degradation)
    """
    if not corpus:
        return []

    try:
        from rank_bm25 import BM25Okapi  # type: ignore[import]
    except ImportError:
        return []

    tokenized_corpus = [doc.lower().split() for doc in corpus]
    bm25 = BM25Okapi(tokenized_corpus)
    query_tokens = query.lower().split()
    scores = bm25.get_scores(query_tokens)

    indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return [(idx, float(score)) for idx, score in indexed[:top_n]]
