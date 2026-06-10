"""Streamlit UI for CodeRAG (optional ``[ui]`` extra).

Search box + retrieved chunks shown with ``path:line`` citations and similarity scores, an
optional streamed LLM answer, and a sidebar with index status and a reindex button. Launch
via ``coderag ui`` (which runs ``streamlit run`` on this file).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import streamlit as st

from coderag.api import CodeRAG
from coderag.config import Config


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--watched-dir")
    parser.add_argument("--store-dir")
    args, _ = parser.parse_known_args()
    return args


@st.cache_resource
def get_engine(watched_dir: str | None, store_dir: str | None) -> CodeRAG:
    overrides: dict = {}
    if watched_dir:
        overrides["watched_dir"] = Path(watched_dir)
    if store_dir:
        overrides["store_dir"] = Path(store_dir)
    return CodeRAG(Config.from_env(**overrides))


def main() -> None:
    args = _parse_args()
    st.set_page_config(page_title="CodeRAG", page_icon="🔎", layout="wide")
    st.title("🔎 CodeRAG")
    st.caption("Local-first semantic search over your codebase.")

    cr = get_engine(args.watched_dir, args.store_dir)

    with st.sidebar:
        st.header("Index")
        try:
            status = cr.status()
            st.metric("Files", status["total_files"])
            st.metric("Chunks", status["total_chunks"])
            st.write(f"**Model:** `{status['model']}`")
            st.write(f"**Index:** `{status['index_type']}`")
            st.write(f"**Root:** `{status['watched_dir']}`")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not read index: {exc}")
        if st.button("🔄 Reindex"):
            with st.spinner("Reindexing..."):
                stats = cr.index()
            st.success(
                f"+{stats.files_indexed} files, {stats.total_chunks} chunks total."
            )
        want_answer = st.toggle("Generate LLM answer", value=False)
        top_k = st.slider("Results", min_value=1, max_value=20, value=8)

    query = st.text_input("Search", placeholder="e.g. where is retry/backoff handled?")
    if not query:
        return

    hits = cr.search(query, top_k=top_k)
    if not hits:
        st.warning(
            "No results. Have you indexed this codebase? Use the Reindex button."
        )
        return

    if want_answer:
        from coderag.llm import stream_answer

        st.subheader("Answer")
        try:
            st.write_stream(stream_answer(cr, query, top_k))
        except RuntimeError as exc:
            st.info(f"LLM answer unavailable: {exc}")

    st.subheader(f"{len(hits)} results")
    for hit in hits:
        title = f"`{hit.location}`"
        if hit.symbol:
            title += f" — **{hit.symbol}** ({hit.kind})"
        title += f"  ·  sim {hit.similarity:.2f}"
        with st.expander(title, expanded=False):
            st.code(hit.text, language=hit.language)


main()
