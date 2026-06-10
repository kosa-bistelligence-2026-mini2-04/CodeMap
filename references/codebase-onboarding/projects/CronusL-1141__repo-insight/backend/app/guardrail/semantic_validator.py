from __future__ import annotations

import logging
import math
import os
import re

from app.models.api_schemas import GuardrailSemanticFilter

logger = logging.getLogger(__name__)

_SENT_SPLIT = re.compile(r"(?<=[。！？!?])\s+|\n+")
_DEFAULT_THRESHOLD = 0.35

_MODEL = None


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_SPLIT.split(text) if s.strip()]


def _split_paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    return parts


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _load_sentence_transformers_backend():
    """Conditional import — only called when backend == 'sentence_transformers'."""
    from sentence_transformers import SentenceTransformer  # noqa: F401 (conditional)

    return SentenceTransformer("all-MiniLM-L6-v2")


def _tfidf_encode(texts: list[str]) -> list[list[float]]:
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
    except ImportError:
        logger.warning("sklearn not available; semantic filter degrades to no-op")
        return [[0.0] for _ in texts]
    vec = TfidfVectorizer()
    matrix = vec.fit_transform(texts)
    return matrix.toarray().tolist()


def _get_backend() -> str:
    return os.environ.get("SEMANTIC_VALIDATOR_BACKEND", "stub")


class SemanticValidator:
    """Layer-2 filter: lazy-singleton embedding backend, outputs telemetry filters."""

    def __init__(
        self,
        threshold: float = _DEFAULT_THRESHOLD,
    ) -> None:
        self.threshold = threshold

    def _encode_pair(
        self, sentences: list[str], sources: list[str]
    ) -> tuple[list[list[float]], list[list[float]]]:
        global _MODEL
        backend = _get_backend()

        if backend == "stub":
            return [], []

        if backend == "sentence_transformers":
            if _MODEL is None:
                try:
                    _MODEL = _load_sentence_transformers_backend()
                except Exception as exc:
                    logger.warning(
                        "sentence_transformers load failed (%s), using tfidf fallback",
                        exc,
                    )
                    _MODEL = "_tfidf_fallback_"
            if _MODEL == "_tfidf_fallback_":
                combined = sentences + sources
                vecs = _tfidf_encode(combined)
                return vecs[: len(sentences)], vecs[len(sentences) :]
            sent_vecs = _MODEL.encode(sentences, normalize_embeddings=True).tolist()
            src_vecs = _MODEL.encode(sources, normalize_embeddings=True).tolist()
            return sent_vecs, src_vecs

        if backend == "tfidf":
            combined = sentences + sources
            vecs = _tfidf_encode(combined)
            return vecs[: len(sentences)], vecs[len(sentences) :]

        return [], []

    def validate(
        self,
        llm_output: str,
        source_text: str,
        threshold: float | None = None,
    ) -> list[GuardrailSemanticFilter]:
        thr = self.threshold if threshold is None else threshold
        backend = _get_backend()
        if backend == "stub":
            return []

        sentences = _split_sentences(llm_output)
        sources = _split_paragraphs(source_text)
        if not sentences or not sources:
            return []

        sent_vecs, src_vecs = self._encode_pair(sentences, sources)
        if not sent_vecs or not src_vecs:
            return []

        filters: list[GuardrailSemanticFilter] = []
        for sent, sv in zip(sentences, sent_vecs):
            best = 0.0
            for srv in src_vecs:
                sim = _cosine(sv, srv)
                if sim > best:
                    best = sim
            if best < thr:
                filters.append(
                    GuardrailSemanticFilter(
                        original_text=sent,
                        similarity_score=float(best),
                        threshold=float(thr),
                    )
                )
        return filters
