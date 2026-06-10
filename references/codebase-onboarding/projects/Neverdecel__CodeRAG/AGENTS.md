# Repository Guidelines

## Project Structure & Module Organization
- `coderag/api.py`: The `CodeRAG` facade — the public entry point every surface routes through.
- `coderag/config.py`, `coderag/types.py`: Immutable `Config` and shared dataclasses.
- `coderag/embeddings/`: `EmbeddingProvider` protocol + `fastembed` (default), `openai`, `fake`.
- `coderag/chunking/`: Symbol-aware chunking (`python_ast.py`, `treesitter.py`, line-window `base.py`).
- `coderag/store/`: `sqlite_store.py` (source of truth + FTS5) and `vector_index.py` (FAISS Flat/IVF cache).
- `coderag/retrieval/`: Hybrid dense + BM25 search fused with RRF.
- `coderag/indexer.py`, `coderag/watch.py`: Incremental indexing and the debounced watcher.
- `coderag/surfaces/`: `cli.py`, `http_api.py` (FastAPI), `streamlit_app.py` — thin adapters over the facade.
- `tests/`: pytest suite (offline by default via the `fake` provider; real model behind `-m integration`).
- `example.env` → copy to `.env`; CI lives in `.github/`.

## Build, Test, and Development Commands
- Create env: `python -m venv venv && source venv/bin/activate`.
- Install: `pip install -e ".[dev,server,openai]"` (extras: `server`, `ui`, `openai`).
- Use it: `coderag index`, `coderag search "QUERY"`, `coderag watch`, `coderag serve`, `coderag ui`, `coderag status`.
- Tests: `pytest -m "not integration"` (fast/offline) or `pytest -m integration` (real fastembed).
- Quality: `black --check . && isort --check-only . && flake8 coderag tests && mypy coderag`.

## Coding Style & Naming Conventions
- Black (88-col code), isort profile "black". flake8 config in `.flake8` allows up to 100 cols (prose slack).
- Typing: mypy (py311 target). Prefer typed signatures and concise docstrings.
- Indentation: 4 spaces. `snake_case` functions/files, `PascalCase` classes, `UPPER_SNAKE` constants.
- First-party module is `coderag`; surfaces must stay thin — no engine logic in `surfaces/`.

## Architecture Invariants
- SQLite is the source of truth; the FAISS index is a rebuildable cache (`rebuild_from_store`).
- `chunks.id` is the FAISS id and is `AUTOINCREMENT` (ids never reused).
- Incremental indexing is delete-before-add (no duplicate/stale vectors); unchanged files skip via content hash.
- Embedding dimension comes from the provider, not a constant; a model change triggers a rebuild.

## Testing Guidelines
- Place tests in `tests/` as `test_*.py`; keep them deterministic and offline (use the `fake` provider fixture).
- Mark anything that downloads a model or hits the network with `@pytest.mark.integration` (deselected in CI).
- Mock OpenAI; never call the network in default tests.

## Commit & Pull Request Guidelines
- Conventional Commits: `feat:`, `fix:`, `docs:`, `ci:`, `refactor:`, `test:`.
- Before pushing: run the quality gate above and update docs when behavior changes.
- PRs: clear description, validation steps, screenshots/GIFs for UI changes, note config changes (`.env`).

## Security & Configuration Tips
- Never commit secrets. The default local provider needs no key; OpenAI is opt-in.
- The index/database live in `CODERAG_STORE_DIR` (default `./.coderag/`, gitignored).
