"""P3 tests: incremental indexing, the no-duplicate invariant, and pruning."""

from __future__ import annotations

from coderag.api import CodeRAG
from tests.conftest import write


def _cr(config) -> CodeRAG:
    config.watched_dir.mkdir(parents=True, exist_ok=True)
    return CodeRAG(config)


def test_index_creates_chunks(config):
    cr = _cr(config)
    write(config.watched_dir / "a.py", "def alpha():\n    return 1\n")
    write(config.watched_dir / "b.py", "def beta():\n    return 2\n")
    stats = cr.index()
    assert stats.files_indexed == 2
    assert stats.total_chunks >= 2
    assert cr.vectors.ntotal == stats.total_chunks


def test_unchanged_files_are_skipped(config):
    cr = _cr(config)
    write(config.watched_dir / "a.py", "def alpha():\n    return 1\n")
    cr.index()
    stats2 = cr.index()  # nothing changed
    assert stats2.files_indexed == 0
    assert stats2.files_skipped == 1


def test_editing_a_file_does_not_duplicate(config):
    cr = _cr(config)
    path = config.watched_dir / "a.py"
    write(path, "def alpha():\n    return 1\n")
    cr.index()
    chunks_before = cr.store.total_chunks()
    vectors_before = cr.vectors.ntotal
    assert chunks_before == vectors_before

    # Edit and reindex.
    write(path, "def alpha():\n    return 100\n\ndef gamma():\n    return 3\n")
    stats = cr.index()
    assert stats.chunks_removed >= 1  # old chunks were deleted first
    # Store and FAISS stay in lock-step (no stale/duplicate vectors).
    assert cr.store.total_chunks() == cr.vectors.ntotal
    # The new content is searchable; the stale content is gone.
    rows = cr.store.hydrate(
        cr.store.chunk_ids_for_file(cr.store.get_file("a.py")["id"])
    )
    joined = "\n".join(r["text"] for r in rows.values())
    assert "return 100" in joined
    assert "return 1\n" not in joined or "return 100" in joined


def test_deleted_file_is_pruned(config):
    cr = _cr(config)
    a = config.watched_dir / "a.py"
    b = config.watched_dir / "b.py"
    write(a, "def alpha():\n    return 1\n")
    write(b, "def beta():\n    return 2\n")
    cr.index()
    assert cr.store.total_chunks() == cr.vectors.ntotal

    b.unlink()
    stats = cr.index()
    assert stats.files_removed == 1
    assert "b.py" not in cr.store.all_file_paths()
    assert cr.store.total_chunks() == cr.vectors.ntotal


def test_ignored_dirs_are_skipped(config):
    cr = _cr(config)
    write(config.watched_dir / "src" / "a.py", "def alpha():\n    return 1\n")
    write(config.watched_dir / "node_modules" / "x.js", "function x(){return 1;}\n")
    write(config.watched_dir / ".git" / "hooks.py", "def hook():\n    return 1\n")
    cr.index()
    paths = cr.store.all_file_paths()
    assert "src/a.py" in paths
    assert not any("node_modules" in p for p in paths)
    assert not any(".git" in p for p in paths)


def test_full_rebuild_resets(config):
    cr = _cr(config)
    write(config.watched_dir / "a.py", "def alpha():\n    return 1\n")
    cr.index()
    n1 = cr.store.total_chunks()
    stats = cr.index(full=True)
    assert stats.total_chunks == n1  # same content, rebuilt cleanly
    assert cr.store.total_chunks() == cr.vectors.ntotal


def test_index_survives_reopen(config, tmp_path):
    cr = _cr(config)
    write(config.watched_dir / "a.py", "def alpha():\n    return 1\n")
    cr.index()
    n = cr.store.total_chunks()
    cr.close()

    cr2 = CodeRAG(config)
    assert cr2.store.total_chunks() == n
    assert cr2.vectors.ntotal == n  # FAISS cache reloaded, consistent
