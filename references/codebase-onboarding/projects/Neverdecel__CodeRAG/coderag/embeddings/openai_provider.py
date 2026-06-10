"""Opt-in OpenAI embedding provider.

Unlike the old CodeRAG, this embeds each chunk independently (no file-level averaging) and
batches requests for throughput. The client and dimension are resolved lazily.
"""

from __future__ import annotations

import logging
from functools import cached_property
from typing import List, Optional, Sequence

import numpy as np
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Known output dimensions; anything else is probed on first use.
_KNOWN_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}

_BATCH = 128


class OpenAIEmbeddingProvider:
    name = "openai"

    def __init__(self, model: str, api_key: Optional[str] = None):
        self._model = model
        self._api_key = api_key
        self._dim = _KNOWN_DIMS.get(model)

    @cached_property
    def _client(self):
        from openai import OpenAI

        if not self._api_key:
            raise RuntimeError(
                "OpenAI provider requires an API key (set OPENAI_API_KEY)."
            )
        return OpenAI(api_key=self._api_key)

    @property
    def model_id(self) -> str:
        return self._model

    @property
    def dim(self) -> int:
        if self._dim is None:
            self._dim = self.embed_query("probe").shape[0]
        return self._dim

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, max=8),
        reraise=True,
    )
    def _embed_batch(self, inputs: List[str]) -> np.ndarray:
        resp = self._client.embeddings.create(
            model=self._model, input=inputs, timeout=30
        )
        return np.array([d.embedding for d in resp.data], dtype="float32")

    def embed_documents(self, texts: Sequence[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim if self._dim else 1), dtype="float32")
        out: List[np.ndarray] = []
        for i in range(0, len(texts), _BATCH):
            out.append(self._embed_batch(list(texts[i : i + _BATCH])))
        return np.vstack(out).astype("float32")

    def embed_query(self, text: str) -> np.ndarray:
        return self._embed_batch([text])[0]
