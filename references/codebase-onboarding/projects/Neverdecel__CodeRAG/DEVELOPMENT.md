# 🛠️ Development Guide

## Setup

```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -e ".[dev,server,openai]"             # editable install + all extras
pre-commit install                                # optional: run quality checks on commit
```

No configuration is required to run — the default `fastembed` provider downloads a small
local model on first use. Copy `example.env` to `.env` only if you want to set defaults.

## Architecture

CodeRAG is one engine (`coderag.api.CodeRAG`) behind several surfaces. The facade wires
together four swappable pieces and constructs them lazily.

```
coderag/
├── api.py              # CodeRAG facade — the public entry point every surface uses
├── config.py           # Immutable Config dataclass (Config.from_env)
├── types.py            # Chunk, SearchHit, IndexStats
├── indexer.py          # Incremental indexing: hash-diff, delete-before-add, prune
├── watch.py            # Debounced filesystem watcher -> indexer
├── llm.py              # Optional streamed LLM answer over retrieved chunks
├── embeddings/         # EmbeddingProvider protocol + fastembed / openai / fake
├── chunking/           # Symbol-aware chunking: python_ast, treesitter, line-window base
├── store/              # SQLite source of truth + pluggable FAISS vector index
│   ├── sqlite_store.py #   files/chunks/vectors + FTS5 lexical search
│   └── vector_index.py #   FaissVectorIndex: Flat (exact) / IVF (scale)
├── retrieval/          # Hybrid search: dense + BM25, fused with RRF
└── surfaces/           # cli.py · http_api.py (FastAPI) · streamlit_app.py
```

### Design invariants (don't break these)

- **SQLite is the source of truth; FAISS is a rebuildable cache.** Vectors are stored as
  BLOBs in SQLite, so `FaissVectorIndex.rebuild_from_store()` can always reconstruct the
  index. `ensure_consistent()` does this automatically when counts disagree.
- **`chunks.id` is the FAISS id and is `AUTOINCREMENT`** — ids are never reused, which keeps
  a stale cache from resurrecting deleted content.
- **Delete-before-add.** A changed file's old chunks are removed from both SQLite and FAISS
  before new ones are added (`Indexer._index_file`). This is the bug the old `monitor.py` had.
- **The embedding dimension comes from the provider**, never a hard-coded constant. A model
  change is detected via `meta.embed_dim` and triggers a clean rebuild.

## Quality gate

The same commands CI runs:

```bash
pytest -m "not integration"   # fast & offline — uses the deterministic fake embedder
pytest -m integration         # exercises the real fastembed model (downloads once)
black --check . && isort --check-only .
flake8 coderag tests          # config in .flake8 (max-line-length 100)
mypy coderag
```

Tests never hit the network or download a model unless marked `integration`. Use the
`config`/`repo`/`write` fixtures in `tests/conftest.py` (they default to the `fake` provider).

## Adding things

- **A new embedding backend:** implement the `EmbeddingProvider` protocol
  (`coderag/embeddings/__init__.py`) and wire it into `get_provider()`.
- **A new language:** add the extension in `chunking/languages.py`; for symbol-aware
  chunking, add a grammar + node types in `chunking/treesitter.py` (or rely on the
  line-window fallback).
- **A new surface:** keep it a thin adapter over `coderag.api.CodeRAG` — no engine logic in
  surfaces.

## Conventions

- Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`).
- Black (88-col code) + isort (black profile); flake8 allows up to 100 cols for prose.
- Typed signatures and concise docstrings on public functions.
