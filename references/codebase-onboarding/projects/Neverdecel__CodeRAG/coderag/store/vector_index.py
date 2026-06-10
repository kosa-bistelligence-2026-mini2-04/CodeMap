"""FAISS vector index — a rebuildable cache over the vectors stored in SQLite.

Two backends behind one interface, selected by corpus size:
- **flat** (``IndexIDMap2(IndexFlatIP)``): exact cosine, ideal for small/medium repos.
- **ivf** (``IndexIVFFlat``): approximate, stays fast at 100k+ vectors.

Both support ``add_with_ids`` and ``remove_ids``, so incremental indexing (delete a file's
old chunks, add the new ones) works identically regardless of backend. Because every vector
also lives in SQLite, the on-disk ``.faiss`` file is disposable and can be rebuilt at any
time (``rebuild_from_store``).
"""

from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import TYPE_CHECKING, Tuple

import faiss
import numpy as np

from coderag.config import Config

if TYPE_CHECKING:
    from coderag.store.sqlite_store import SQLiteStore

logger = logging.getLogger(__name__)


def _normalized(vectors: np.ndarray) -> np.ndarray:
    """Return an L2-normalized float32 copy (cosine similarity via inner product)."""
    mat = np.ascontiguousarray(vectors, dtype="float32")
    if mat.size:
        mat = mat.copy()
        faiss.normalize_L2(mat)
    return mat


def _derive_nlist(n: int, configured: int) -> int:
    if configured > 0:
        return max(1, min(configured, n))
    return max(1, min(int(4 * math.sqrt(n)), max(1, n // 39)))


class FaissVectorIndex:
    def __init__(self, index: faiss.Index, kind: str, config: Config, dim: int) -> None:
        self._index = index
        self.kind = kind
        self.config = config
        self.dim = dim

    # --- construction / persistence ---

    @classmethod
    def _empty_flat(cls, dim: int) -> faiss.Index:
        return faiss.IndexIDMap2(faiss.IndexFlatIP(dim))

    @classmethod
    def open(cls, config: Config, dim: int) -> "FaissVectorIndex":
        path = config.faiss_path
        meta_path = Path(str(path) + ".kind")
        if path.exists() and meta_path.exists():
            try:
                index = faiss.read_index(str(path))
                kind = meta_path.read_text().strip() or "flat"
                if kind == "ivf":
                    index.nprobe = config.ivf_nprobe
                return cls(index, kind, config, dim)
            except Exception as exc:  # pragma: no cover - corrupt cache
                logger.warning("Failed to load FAISS index (%s); starting empty.", exc)
        return cls(cls._empty_flat(dim), "flat", config, dim)

    def save(self) -> None:
        path = self.config.faiss_path
        path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(path))
        Path(str(path) + ".kind").write_text(self.kind)

    # --- properties ---

    @property
    def ntotal(self) -> int:
        return int(self._index.ntotal)

    # --- mutations ---

    def add(self, ids: np.ndarray, vectors: np.ndarray) -> None:
        if len(ids) == 0:
            return
        vecs = _normalized(vectors)
        id_arr = np.ascontiguousarray(ids, dtype="int64")
        self._index.add_with_ids(vecs, id_arr)

    def remove(self, ids) -> int:
        ids = list(ids)
        if not ids:
            return 0
        selector = faiss.IDSelectorBatch(np.asarray(ids, dtype="int64"))
        return int(self._index.remove_ids(selector))

    def search(self, query: np.ndarray, k: int) -> Tuple[np.ndarray, np.ndarray]:
        """Return ``(ids, scores)`` for the top-k, with FAISS ``-1`` padding stripped."""
        if self.ntotal == 0:
            return np.empty(0, dtype="int64"), np.empty(0, dtype="float32")
        q = _normalized(np.asarray(query, dtype="float32").reshape(1, -1))
        k = min(k, self.ntotal)
        scores, ids = self._index.search(q, k)
        ids_row, scores_row = ids[0], scores[0]
        mask = ids_row != -1
        return ids_row[mask].astype("int64"), scores_row[mask].astype("float32")

    # --- rebuild / consistency ---

    def _choose_kind(self, n: int) -> str:
        if self.config.index_type == "flat":
            return "flat"
        if self.config.index_type == "ivf":
            return "ivf" if n > 0 else "flat"
        # auto
        return "ivf" if n > self.config.ivf_threshold else "flat"

    def _build_ivf(self, ids: np.ndarray, vecs: np.ndarray) -> faiss.Index:
        nlist = _derive_nlist(len(ids), self.config.ivf_nlist)
        quantizer = faiss.IndexFlatIP(self.dim)
        index = faiss.IndexIVFFlat(
            quantizer, self.dim, nlist, faiss.METRIC_INNER_PRODUCT
        )
        index.train(vecs)
        index.add_with_ids(vecs, ids)
        index.nprobe = self.config.ivf_nprobe
        logger.info("Built IVF index: %d vectors, nlist=%d", len(ids), nlist)
        return index

    def rebuild_from_store(self, store: "SQLiteStore") -> None:
        """Discard the current index and rebuild it from the SQLite vectors."""
        n = store.total_chunks()
        kind = self._choose_kind(n)
        if n == 0:
            self._index = self._empty_flat(self.dim)
            self.kind = "flat"
            self.save()
            return

        if kind == "ivf":
            # IVF needs all training vectors up front.
            all_ids, all_vecs = [], []
            for ids, vecs in store.iter_vectors():
                all_ids.append(ids)
                all_vecs.append(_normalized(vecs))
            ids = np.concatenate(all_ids)
            vecs = np.vstack(all_vecs)
            self._index = self._build_ivf(ids, vecs)
            self.kind = "ivf"
        else:
            index = self._empty_flat(self.dim)
            for ids, vecs in store.iter_vectors():
                index.add_with_ids(_normalized(vecs), np.ascontiguousarray(ids))
            self._index = index
            self.kind = "flat"
            logger.info("Built flat index: %d vectors", n)
        self.save()

    def ensure_consistent(self, store: "SQLiteStore") -> None:
        """Rebuild from SQLite if the cached vector count disagrees with the store."""
        if self.ntotal != store.total_chunks():
            logger.info(
                "FAISS cache out of sync (%d vs %d chunks); rebuilding.",
                self.ntotal,
                store.total_chunks(),
            )
            self.rebuild_from_store(store)

    def maybe_upgrade(self, store: "SQLiteStore") -> bool:
        """Switch flat->ivf when an auto index grows past the threshold. Returns True
        if a rebuild happened."""
        if self.config.index_type != "auto" or self.kind == "ivf":
            return False
        if store.total_chunks() > self.config.ivf_threshold:
            logger.info("Corpus exceeded IVF threshold; upgrading flat -> ivf.")
            self.rebuild_from_store(store)
            return True
        return False
