"""P4 tests: RRF fusion and end-to-end hybrid search."""

from __future__ import annotations

from coderag.api import CodeRAG
from coderag.retrieval.fusion import reciprocal_rank_fusion
from tests.conftest import write


def test_rrf_merges_and_dedupes():
    dense = [1, 2, 3]
    lexical = [3, 4, 1]
    fused = reciprocal_rank_fusion([dense, lexical], k=60)
    ids = [i for i, _ in fused]
    # ids appearing in both lists should rank above singletons
    assert set(ids) == {1, 2, 3, 4}
    assert ids[0] in (1, 3)  # shared, high-ranked items win


def test_rrf_respects_weights():
    a = [10, 11]
    b = [20, 21]
    fused = reciprocal_rank_fusion([a, b], k=60, weights=[5.0, 1.0])
    assert fused[0][0] == 10  # heavily-weighted list dominates


def test_rrf_empty():
    assert reciprocal_rank_fusion([[], []]) == []


def _indexed(config) -> CodeRAG:
    config.watched_dir.mkdir(parents=True, exist_ok=True)
    write(
        config.watched_dir / "auth.py",
        "def authenticate_user(token):\n"
        "    '''Validate a session token and return the user.'''\n"
        "    return verify(token)\n",
    )
    write(
        config.watched_dir / "math_utils.py",
        "def add_numbers(a, b):\n    return a + b\n",
    )
    cr = CodeRAG(config)
    cr.index()
    return cr


def test_search_finds_relevant_symbol(config):
    cr = _indexed(config)
    hits = cr.search("authenticate_user", top_k=3)
    assert hits
    assert hits[0].path == "auth.py"
    assert hits[0].symbol == "authenticate_user"
    assert hits[0].location == "auth.py:1"


def test_lexical_recall_via_fts(config):
    # An exact identifier that should be found even if dense recall is weak.
    cr = _indexed(config)
    hits = cr.search("add_numbers", top_k=3)
    assert any(h.path == "math_utils.py" for h in hits)


def test_search_empty_query(config):
    cr = _indexed(config)
    assert cr.search("   ", top_k=3) == []


def test_search_returns_scores_and_similarity(config):
    cr = _indexed(config)
    hits = cr.search("authenticate_user", top_k=3)
    assert all(h.score > 0 for h in hits)
    assert all(0.0 <= h.similarity <= 1.0 for h in hits)


def test_hits_are_serializable(config):
    cr = _indexed(config)
    hits = cr.search("token", top_k=2)
    for h in hits:
        d = h.as_dict()
        assert "path" in d and "location" in d and "score" in d
