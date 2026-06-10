"""Optional LLM answer surface — turn retrieved chunks into a grounded, cited answer.

This is intentionally thin and optional: CodeRAG's core value is retrieval. When an OpenAI
key is configured, ``stream_answer`` composes the top hits into a prompt and streams a
response; otherwise callers should just show the retrieved chunks.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Iterator, List

from coderag.types import SearchHit

if TYPE_CHECKING:
    from coderag.api import CodeRAG

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a precise coding assistant. Answer the user's question using ONLY the "
    "retrieved code context. Cite files as `path:line`. If the context is insufficient, "
    "say so plainly rather than guessing."
)


def build_context(hits: List[SearchHit], max_chars: int = 8000) -> str:
    blocks: List[str] = []
    used = 0
    for hit in hits:
        header = f"# {hit.location}" + (f" ({hit.symbol})" if hit.symbol else "")
        block = f"{header}\n```{hit.language}\n{hit.text}\n```"
        if used + len(block) > max_chars:
            break
        blocks.append(block)
        used += len(block)
    return "\n\n".join(blocks)


def stream_answer(cr: "CodeRAG", query: str, top_k: int | None = None) -> Iterator[str]:
    """Yield answer tokens. Raises RuntimeError if no OpenAI key is configured."""
    hits = cr.search(query, top_k or cr.config.top_k)
    if not hits:
        yield "No relevant code was found in the index for that query."
        return

    api_key = cr.config.openai_api_key
    if not api_key:
        raise RuntimeError(
            "LLM answers require an OpenAI API key (set OPENAI_API_KEY). "
            "Retrieved chunks are still available without it."
        )

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    context = build_context(hits)
    user = f"Question: {query}\n\nRetrieved code context:\n{context}"
    stream = client.chat.completions.create(
        model=cr.config.chat_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        stream=True,
    )
    for part in stream:
        if part.choices and part.choices[0].delta.content:
            yield part.choices[0].delta.content
