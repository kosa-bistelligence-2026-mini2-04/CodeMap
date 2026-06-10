"""Pluggable embedding providers.

A provider turns text into L2-comparable float32 vectors. The crucial contract change
from the old CodeRAG: providers embed a *list of already-chunked texts* and return one
vector per text — there is no file-level averaging anywhere. The embedding dimension is a
property of the provider (and its model), never a hard-coded constant.
"""

from __future__ import annotations

from typing import Protocol, Sequence, runtime_checkable

import numpy as np

from coderag.config import Config


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Minimal interface every embedding backend implements."""

    name: str

    @property
    def model_id(self) -> str:
        """Stable identifier of the underlying model (stored with each chunk)."""

    @property
    def dim(self) -> int:
        """Embedding dimensionality."""

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        """Embed code chunks. Returns a ``(len(texts), dim)`` float32 array."""

    def embed_query(self, text: str) -> np.ndarray:
        """Embed a single query. Returns a ``(dim,)`` float32 array."""


def get_provider(config: Config) -> EmbeddingProvider:
    """Construct the embedding provider named by ``config.provider``.

    Heavy backends (fastembed/openai) are imported lazily so that ``coderag --help`` and
    the ``fake`` provider used in tests stay dependency-light and instant.
    """
    provider = config.provider.lower()
    if provider == "fake":
        from coderag.embeddings.fake_provider import FakeEmbeddingProvider

        return FakeEmbeddingProvider()
    if provider == "fastembed":
        from coderag.embeddings.fastembed_provider import FastEmbedProvider

        return FastEmbedProvider(config.model, cache_dir=config.cache_dir)
    if provider == "openai":
        from coderag.embeddings.openai_provider import OpenAIEmbeddingProvider

        return OpenAIEmbeddingProvider(
            model=config.openai_model, api_key=config.openai_api_key
        )
    raise ValueError(
        f"Unknown embedding provider {config.provider!r}. "
        "Expected one of: fastembed, openai, fake."
    )


__all__ = ["EmbeddingProvider", "get_provider"]
