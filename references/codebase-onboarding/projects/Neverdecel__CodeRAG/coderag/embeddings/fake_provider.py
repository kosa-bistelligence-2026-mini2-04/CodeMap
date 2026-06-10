"""Deterministic, offline embedding provider for tests and CI.

Maps text -> a stable pseudo-random unit vector via a hash seed. Same text always yields
the same vector, and lexically identical text collides — which is exactly what unit tests
need to assert retrieval behaviour without downloading a model or hitting the network.
"""

from __future__ import annotations

import hashlib
from typing import Sequence

import numpy as np


class FakeEmbeddingProvider:
    name = "fake"

    def __init__(self, dim: int = 16) -> None:
        self._dim = dim

    @property
    def model_id(self) -> str:
        return f"fake-{self._dim}"

    @property
    def dim(self) -> int:
        return self._dim

    def _vector(self, text: str) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "little")
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(self._dim).astype("float32")
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self._dim), dtype="float32")
        return np.vstack([self._vector(t) for t in texts]).astype("float32")

    def embed_query(self, text: str) -> np.ndarray:
        return self._vector(text)
