"""P1 tests: SQLite store + pluggable FAISS vector index."""

from __future__ import annotations

import numpy as np

from coderag.config import Config
from coderag.store.sqlite_store import SQLiteStore
from coderag.store.vector_index import FaissVectorIndex
from coderag.types import Chunk


def _store(tmp_path) -> SQLiteStore:
    store = SQLiteStore(tmp_path / "coderag.db")
    store.bootstrap(embed_dim=16, embed_model="fake-16")
    return store


def _chunk(text: str, start: int = 1) -> Chunk:
    return Chunk(
        text=text,
        start_line=start,
        end_line=start + 2,
        language="python",
        symbol="f",
        kind="function",
    )


def test_add_and_hydrate_chunks(tmp_path):
    store = _store(tmp_path)
    fid = store.upsert_file("a.py", "python", "hash1", 1.0)
    vecs = np.ones((2, 16), dtype="float32")
    ids = store.add_chunks(
        fid, [_chunk("def f(): pass"), _chunk("x = 1", 5)], vecs, "fake-16"
    )
    assert len(ids) == 2
    rows = store.hydrate(ids)
    assert rows[ids[0]]["path"] == "a.py"
    assert rows[ids[0]]["text"] == "def f(): pass"


def test_autoincrement_ids_never_reused(tmp_path):
    store = _store(tmp_path)
    fid = store.upsert_file("a.py", "python", "h", 1.0)
    vecs = np.ones((1, 16), dtype="float32")
    first = store.add_chunks(fid, [_chunk("a")], vecs, "fake-16")
    store.delete_chunks_for_file(fid)
    second = store.add_chunks(fid, [_chunk("b")], vecs, "fake-16")
    assert second[0] > first[0]  # id advanced, not recycled


def test_fts_search_finds_token_and_survives_operators(tmp_path):
    store = _store(tmp_path)
    fid = store.upsert_file("a.py", "python", "h", 1.0)
    vecs = np.ones((1, 16), dtype="float32")
    store.add_chunks(fid, [_chunk("def parse_config(): return 1")], vecs, "fake-16")
    hits = store.fts_search("parse_config", limit=5)
    assert len(hits) == 1
    # Operators in the query must not raise.
    assert store.fts_search("parse_config::*", limit=5)
    assert store.fts_search("", limit=5) == []


def test_iter_vectors_round_trips(tmp_path):
    store = _store(tmp_path)
    fid = store.upsert_file("a.py", "python", "h", 1.0)
    vecs = np.random.default_rng(0).standard_normal((3, 16)).astype("float32")
    ids = store.add_chunks(
        fid, [_chunk("a"), _chunk("b"), _chunk("c")], vecs, "fake-16"
    )
    got_ids, got_vecs = next(store.iter_vectors())
    assert list(got_ids) == ids
    np.testing.assert_allclose(got_vecs, vecs)


def test_model_change_triggers_rebuild_flag(tmp_path):
    store = SQLiteStore(tmp_path / "coderag.db")
    assert store.bootstrap(16, "fake-16") is False
    store.upsert_file("a.py", "python", "h", 1.0)
    # Re-bootstrap with a different dim/model: should clear and request rebuild.
    assert store.bootstrap(384, "bge-small") is True
    assert store.all_file_paths() == []


def _vec_index(tmp_path, **cfg) -> tuple:
    config = Config(store_dir=tmp_path, **cfg)
    store = _store(tmp_path)
    idx = FaissVectorIndex.open(config, dim=16)
    return config, store, idx


def test_vector_add_search_remove(tmp_path):
    _, _, idx = _vec_index(tmp_path)
    rng = np.random.default_rng(1)
    vecs = rng.standard_normal((5, 16)).astype("float32")
    ids = np.array([10, 20, 30, 40, 50], dtype="int64")
    idx.add(ids, vecs)
    assert idx.ntotal == 5
    got_ids, scores = idx.search(vecs[2], k=3)
    assert got_ids[0] == 30  # closest to itself
    assert scores[0] > 0.99
    removed = idx.remove([30])
    assert removed == 1
    got_ids, _ = idx.search(vecs[2], k=3)
    assert 30 not in got_ids


def test_rebuild_from_store_and_consistency(tmp_path):
    config, store, idx = _vec_index(tmp_path)
    fid = store.upsert_file("a.py", "python", "h", 1.0)
    vecs = np.random.default_rng(2).standard_normal((4, 16)).astype("float32")
    store.add_chunks(fid, [_chunk(str(i)) for i in range(4)], vecs, "fake-16")
    # Index is empty but store has 4 chunks -> ensure_consistent rebuilds.
    idx.ensure_consistent(store)
    assert idx.ntotal == 4
    assert idx.kind == "flat"


def test_auto_upgrade_flat_to_ivf(tmp_path):
    # ivf_threshold tiny so a small corpus crosses it.
    config, store, idx = _vec_index(tmp_path, ivf_threshold=10)
    fid = store.upsert_file("a.py", "python", "h", 1.0)
    n = 30
    vecs = np.random.default_rng(3).standard_normal((n, 16)).astype("float32")
    ids = store.add_chunks(fid, [_chunk(str(i)) for i in range(n)], vecs, "fake-16")
    idx.add(np.array(ids, dtype="int64"), vecs)
    assert idx.kind == "flat"
    upgraded = idx.maybe_upgrade(store)
    assert upgraded is True
    assert idx.kind == "ivf"
    assert idx.ntotal == n
    # IVF still returns the self-match.
    got_ids, _ = idx.search(vecs[0], k=1)
    assert got_ids[0] == ids[0]


def test_index_persists_across_open(tmp_path):
    config, store, idx = _vec_index(tmp_path)
    vecs = np.random.default_rng(4).standard_normal((3, 16)).astype("float32")
    idx.add(np.array([1, 2, 3], dtype="int64"), vecs)
    idx.save()
    reopened = FaissVectorIndex.open(config, dim=16)
    assert reopened.ntotal == 3
    assert reopened.kind == "flat"
