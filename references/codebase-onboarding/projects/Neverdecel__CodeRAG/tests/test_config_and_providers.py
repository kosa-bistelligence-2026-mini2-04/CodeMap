"""P0 scaffolding tests: Config behaviour and the embedding provider abstraction."""

from __future__ import annotations

import numpy as np

from coderag.config import Config
from coderag.embeddings import EmbeddingProvider, get_provider


def test_config_defaults_and_derived_paths(tmp_path):
    cfg = Config(store_dir=tmp_path / ".coderag")
    assert cfg.provider == "fastembed"
    assert cfg.db_path == tmp_path / ".coderag" / "coderag.db"
    assert cfg.faiss_path == tmp_path / ".coderag" / "index.faiss"


def test_config_is_immutable_and_copies():
    cfg = Config()
    updated = cfg.with_overrides(top_k=42)
    assert updated.top_k == 42
    assert cfg.top_k == 8  # original untouched


def test_from_env_reads_and_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("CODERAG_PROVIDER", "fake")
    monkeypatch.setenv("CODERAG_TOP_K", "3")
    cfg = Config.from_env(store_dir=tmp_path)
    assert cfg.provider == "fake"
    assert cfg.top_k == 3
    assert cfg.store_dir == tmp_path  # explicit override wins


def test_from_env_ignores_bad_ints(monkeypatch):
    monkeypatch.setenv("CODERAG_TOP_K", "not-a-number")
    cfg = Config.from_env()
    assert cfg.top_k == 8  # falls back to default


def test_fake_provider_conforms_to_protocol():
    provider = get_provider(Config(provider="fake"))
    assert isinstance(provider, EmbeddingProvider)
    assert provider.dim == 16


def test_fake_provider_is_deterministic_and_normalized():
    provider = get_provider(Config(provider="fake"))
    a = provider.embed_documents(["def foo(): pass", "class Bar: ..."])
    b = provider.embed_documents(["def foo(): pass", "class Bar: ..."])
    assert a.shape == (2, provider.dim)
    assert a.dtype == np.dtype("float32")
    np.testing.assert_array_equal(a, b)  # deterministic
    norms = np.linalg.norm(a, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-5)  # unit vectors


def test_fake_provider_query_matches_identical_document():
    provider = get_provider(Config(provider="fake"))
    q = provider.embed_query("hello world")
    d = provider.embed_documents(["hello world"])[0]
    np.testing.assert_allclose(q, d)


def test_empty_documents_returns_empty_array():
    provider = get_provider(Config(provider="fake"))
    out = provider.embed_documents([])
    assert out.shape == (0, provider.dim)


def test_unknown_provider_raises():
    import pytest

    with pytest.raises(ValueError):
        get_provider(Config(provider="bogus"))
