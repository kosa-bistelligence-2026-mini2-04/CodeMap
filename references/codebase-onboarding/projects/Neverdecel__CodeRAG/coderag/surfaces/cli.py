"""The ``coderag`` command — index, search, watch, serve, ui, status.

Every subcommand is a thin adapter over :class:`coderag.api.CodeRAG`.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import textwrap
from pathlib import Path
from typing import List, Optional

from coderag import __version__
from coderag.api import CodeRAG
from coderag.config import Config


def _build_config(args: argparse.Namespace) -> Config:
    overrides: dict = {}
    if getattr(args, "watched_dir", None):
        overrides["watched_dir"] = Path(args.watched_dir).expanduser()
    if getattr(args, "store_dir", None):
        overrides["store_dir"] = Path(args.store_dir).expanduser()
    if getattr(args, "provider", None):
        overrides["provider"] = args.provider
    if getattr(args, "model", None):
        overrides["model"] = args.model
    return Config.from_env(**overrides)


# --- commands ---


def cmd_index(args: argparse.Namespace) -> int:
    cr = CodeRAG(_build_config(args))
    stats = cr.indexer.index(
        Path(args.path).expanduser() if args.path else None,
        full=args.full,
        progress=not args.quiet,
    )
    print(
        f"Indexed {stats.files_indexed} file(s), skipped {stats.files_skipped}, "
        f"removed {stats.files_removed}. "
        f"Total: {stats.total_files} files / {stats.total_chunks} chunks."
    )
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    cr = CodeRAG(_build_config(args))
    hits = cr.search(args.query, top_k=args.k)
    if args.json:
        print(json.dumps([h.as_dict() for h in hits], indent=2))
        return 0 if hits else 1
    if not hits:
        print("No results. Has the codebase been indexed? Try: coderag index")
        return 1
    for i, h in enumerate(hits, 1):
        label = f" ({h.symbol})" if h.symbol else ""
        snippet = textwrap.shorten(
            h.text.replace("\n", " "), width=160, placeholder=" …"
        )
        print(f"{i}. {h.location}{label}  [{h.kind}, sim={h.similarity:.2f}]")
        print(f"   {snippet}")
    if args.answer:
        _print_answer(cr, args.query, args.k)
    return 0


def _print_answer(cr: CodeRAG, query: str, k: int) -> None:
    from coderag.llm import stream_answer

    print("\n--- Answer ---")
    try:
        for token in stream_answer(cr, query, k):
            sys.stdout.write(token)
            sys.stdout.flush()
        print()
    except RuntimeError as exc:
        print(f"(LLM answer unavailable: {exc})")


def cmd_status(args: argparse.Namespace) -> int:
    cr = CodeRAG(_build_config(args))
    print(json.dumps(cr.status(), indent=2))
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    from coderag.watch import watch

    cr = CodeRAG(_build_config(args))
    print(f"Indexing {cr.config.watched_dir} before watching...")
    cr.indexer.index(progress=not args.quiet)
    watch(cr)
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    try:
        from coderag.surfaces.http_api import run_server
    except ImportError:
        print(
            "The HTTP server needs extra deps. Install with: pip install 'coderag[server]'"
        )
        return 1
    cr = CodeRAG(_build_config(args))
    run_server(cr, host=args.host, port=args.port)
    return 0


def cmd_ui(args: argparse.Namespace) -> int:
    import subprocess

    app = Path(__file__).with_name("streamlit_app.py")
    try:
        return subprocess.call(
            ["streamlit", "run", str(app), "--", *_passthrough(args)]
        )
    except FileNotFoundError:
        print("Streamlit is not installed. Install with: pip install 'coderag[ui]'")
        return 1


def _passthrough(args: argparse.Namespace) -> List[str]:
    out: List[str] = []
    if getattr(args, "watched_dir", None):
        out += ["--watched-dir", str(args.watched_dir)]
    if getattr(args, "store_dir", None):
        out += ["--store-dir", str(args.store_dir)]
    return out


# --- parser ---


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--watched-dir", help="Codebase root to index/search.")
    p.add_argument(
        "--store-dir", help="Where the index/database live (default ./.coderag)."
    )
    p.add_argument("--provider", help="Embedding provider: fastembed | openai | fake.")
    p.add_argument("--model", help="Embedding model name.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="coderag",
        description="Standalone, local-first semantic code-search engine.",
    )
    parser.add_argument("--version", action="version", version=f"coderag {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_index = sub.add_parser(
        "index", help="Index (or incrementally update) a codebase."
    )
    p_index.add_argument(
        "path", nargs="?", help="Path to index (defaults to watched dir)."
    )
    p_index.add_argument("--full", action="store_true", help="Force a clean rebuild.")
    p_index.add_argument("--quiet", action="store_true", help="Hide the progress bar.")
    _add_common(p_index)
    p_index.set_defaults(func=cmd_index)

    p_search = sub.add_parser("search", help="Search the indexed codebase.")
    p_search.add_argument("query", help="What to search for.")
    p_search.add_argument(
        "-k", type=int, default=8, help="Number of results (default 8)."
    )
    p_search.add_argument("--json", action="store_true", help="Emit JSON.")
    p_search.add_argument(
        "--answer",
        action="store_true",
        help="Also stream an LLM answer (needs OpenAI key).",
    )
    _add_common(p_search)
    p_search.set_defaults(func=cmd_search)

    p_status = sub.add_parser("status", help="Show index statistics.")
    _add_common(p_status)
    p_status.set_defaults(func=cmd_status)

    p_watch = sub.add_parser(
        "watch", help="Index, then keep the index live on changes."
    )
    p_watch.add_argument("--quiet", action="store_true")
    _add_common(p_watch)
    p_watch.set_defaults(func=cmd_watch)

    p_serve = sub.add_parser("serve", help="Run the HTTP/REST API server.")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8000)
    _add_common(p_serve)
    p_serve.set_defaults(func=cmd_serve)

    p_ui = sub.add_parser("ui", help="Launch the Streamlit web UI.")
    _add_common(p_ui)
    p_ui.set_defaults(func=cmd_ui)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
