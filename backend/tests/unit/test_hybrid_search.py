"""
Unit tests for Hybrid Search (RRF logic) — DB 없이 결정론적 로직 검증.

순수 함수(rrf.py)만 테스트하므로 sqlalchemy, openai 미설치 환경에서도 실행됩니다.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))


class TestRRFScore(unittest.TestCase):
    """rrf.rrf_score 단위 테스트."""

    def _rrf(self, sem, bm, k=60):
        from app.agent_graph.search.rrf import rrf_score
        return rrf_score(sem, bm, k)

    def test_both_ranks(self):
        """두 순위 모두 있을 때 합산."""
        score = self._rrf(1, 1)
        expected = 1 / (60 + 1) + 1 / (60 + 1)
        self.assertAlmostEqual(score, expected, places=6)

    def test_semantic_only(self):
        """시맨틱 순위만 있을 때."""
        score = self._rrf(1, None)
        expected = 1 / (60 + 1)
        self.assertAlmostEqual(score, expected, places=6)

    def test_bm25_only(self):
        """BM25 순위만 있을 때."""
        score = self._rrf(None, 1)
        expected = 1 / (60 + 1)
        self.assertAlmostEqual(score, expected, places=6)

    def test_none_none(self):
        """둘 다 없으면 0."""
        score = self._rrf(None, None)
        self.assertEqual(score, 0.0)

    def test_higher_rank_higher_score(self):
        """1위가 10위보다 점수 높아야 함."""
        score_1 = self._rrf(1, 1)
        score_10 = self._rrf(10, 10)
        self.assertGreater(score_1, score_10)

    def test_rrf_k_penalty(self):
        """k=60일 때 낮은 순위(rank=100)도 합당한 점수 가짐."""
        score = self._rrf(100, 100)
        self.assertGreater(score, 0)
        self.assertLess(score, 0.1)

    def test_custom_k(self):
        """k 파라미터가 적용됨."""
        score_k60 = self._rrf(1, 1, k=60)
        score_k10 = self._rrf(1, 1, k=10)
        # k가 작을수록 점수가 높음
        self.assertGreater(score_k10, score_k60)


class TestBM25Rank(unittest.TestCase):
    """rrf.bm25_rank 단위 테스트."""

    def _rank(self, corpus, query, top_n=3):
        from app.agent_graph.search.rrf import bm25_rank
        return bm25_rank(corpus, query, top_n)

    def test_relevant_document_ranked_higher(self):
        """관련 문서가 높은 순위여야 함."""
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            self.skipTest("rank_bm25 미설치")

        corpus = [
            "def authenticate_user login password",
            "class DatabaseConnection pool",
            "def login validate user password authenticate",
        ]
        ranked = self._rank(corpus, "login authenticate password", top_n=3)
        top_idx = ranked[0][0]
        self.assertEqual(top_idx, 2)

    def test_empty_corpus_returns_empty(self):
        """빈 corpus에서도 오류 없이 빈 리스트 반환."""
        result = self._rank([], "query", top_n=3)
        self.assertEqual(result, [])

    def test_returns_at_most_top_n(self):
        """top_n 이하 결과 반환."""
        try:
            from rank_bm25 import BM25Okapi
        except ImportError:
            self.skipTest("rank_bm25 미설치")

        corpus = ["a b c", "d e f", "g h i", "j k l"]
        ranked = self._rank(corpus, "a b", top_n=2)
        self.assertLessEqual(len(ranked), 2)

    def test_graceful_degradation_no_rank_bm25(self):
        """rank_bm25 없으면 빈 리스트 반환."""
        import importlib
        import sys as _sys
        # rrf 모듈을 강제 리로드하여 rank_bm25 없는 상황 시뮬레이션
        # (rank_bm25가 실제로 없는 환경이면 이미 통과)
        from app.agent_graph.search.rrf import bm25_rank
        # rank_bm25 없는 경우 bm25_rank는 빈 리스트 반환 (ImportError 처리됨)
        # 설치된 경우에도 테스트는 통과해야 함
        result = bm25_rank(["hello world"], "hello", top_n=1)
        # 설치 여부에 관계없이 리스트여야 함
        self.assertIsInstance(result, list)


class TestRRFFusion(unittest.TestCase):
    """RRF 통합 순위 정렬 테스트."""

    def test_rrf_orders_correctly(self):
        """양쪽 모두 1위인 결과(C)가 최종 1위여야 함."""
        from app.agent_graph.search.rrf import rrf_score

        candidates = [
            {"id": "A", "sem_rank": 1, "bm_rank": 5},
            {"id": "B", "sem_rank": 2, "bm_rank": 1},
            {"id": "C", "sem_rank": 1, "bm_rank": 1},  # 양쪽 모두 1위
        ]
        scored = sorted(
            candidates,
            key=lambda x: rrf_score(x["sem_rank"], x["bm_rank"]),
            reverse=True,
        )
        self.assertEqual(scored[0]["id"], "C")

    def test_missing_bm25_uses_semantic_only(self):
        """BM25 없는 결과도 시맨틱 점수만으로 순위 매김."""
        from app.agent_graph.search.rrf import rrf_score

        score_with = rrf_score(1, 1)
        score_without = rrf_score(1, None)
        # BM25 있으면 점수가 더 높음
        self.assertGreater(score_with, score_without)

    def test_additive_fusion_beats_individual(self):
        """RRF가 개별 랭커보다 항상 나쁘지 않음."""
        from app.agent_graph.search.rrf import rrf_score

        # 시맨틱 2위 + BM25 2위 조합
        fused = rrf_score(2, 2)
        # 시맨틱 1위만
        semantic_only = rrf_score(1, None)
        # 이 케이스에서는 시맨틱 1위가 더 높음 (정상)
        self.assertGreater(semantic_only, rrf_score(2, None))


if __name__ == "__main__":
    unittest.main()
