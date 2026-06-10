"""CodeRAG: a standalone, local-first semantic code-search engine.

Public API::

    from coderag import CodeRAG, Config

    cr = CodeRAG(Config.from_env(watched_dir="/path/to/repo"))
    cr.index()
    for hit in cr.search("where is retry/backoff handled?"):
        print(hit.path, hit.start_line, hit.score)
"""

from __future__ import annotations

from coderag.config import Config

__version__ = "1.0.0"

__all__ = ["CodeRAG", "Config", "__version__"]


def __getattr__(name: str) -> object:
    # Lazy re-export so ``import coderag`` stays light (no faiss/fastembed at import).
    if name == "CodeRAG":
        from coderag.api import CodeRAG

        return CodeRAG
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
