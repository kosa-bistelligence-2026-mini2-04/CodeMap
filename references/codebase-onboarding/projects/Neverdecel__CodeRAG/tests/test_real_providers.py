"""P5 tests: the real embedding backends.

The fastembed test is marked ``integration`` (downloads a model) and is deselected in CI.
The OpenAI test mocks the SDK client so it never hits the network.
"""

from __future__ import annotations

import types

import numpy as np
import pytest

from coderag.embeddings.openai_provider import OpenAIEmbeddingProvider


def test_openai_provider_batches_without_averaging(monkeypatch):
    calls = {"inputs": []}

    class _Resp:
        def __init__(self, n, dim):
            self.data = [
                types.SimpleNamespace(embedding=[float(i)] * dim) for i in range(n)
            ]

    class _Embeddings:
        def create(self, model, input, timeout):
            calls["inputs"].append(list(input))
            return _Resp(len(input), 4)

    class _Client:
        embeddings = _Embeddings()

    provider = OpenAIEmbeddingProvider(model="text-embedding-3-small", api_key="k")
    monkeypatch.setattr(type(provider), "_client", property(lambda self: _Client()))

    vecs = provider.embed_documents(["a", "b", "c"])
    assert vecs.shape == (3, 4)  # one vector per chunk, NOT averaged into one
    assert vecs.dtype == np.dtype("float32")
    assert calls["inputs"][0] == ["a", "b", "c"]


def test_openai_known_dim_without_network():
    provider = OpenAIEmbeddingProvider(model="text-embedding-3-small", api_key="k")
    assert provider.dim == 1536  # resolved from the known-dims map, no API call


@pytest.mark.integration
def test_fastembed_end_to_end():
    from coderag.embeddings.fastembed_provider import FastEmbedProvider

    provider = FastEmbedProvider()
    assert provider.dim == 384
    docs = provider.embed_documents(["def add(a, b): return a + b", "hello world"])
    assert docs.shape == (2, 384)
    q = provider.embed_query("how to add two numbers")
    assert q.shape == (384,)
    # The code doc should be more similar to the query than the unrelated doc.
    sims = docs @ (q / np.linalg.norm(q))
    assert sims[0] > sims[1]
