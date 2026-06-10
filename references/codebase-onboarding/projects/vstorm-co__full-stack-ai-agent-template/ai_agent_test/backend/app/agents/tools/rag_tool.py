"""RAG tool for agent knowledge base search."""

import asyncio
import contextvars
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from app.services.rag.retrieval import BaseRetrievalService

_retrieval_service: "BaseRetrievalService | None" = None


def _get_retrieval_service() -> "BaseRetrievalService":
    """Get or create retrieval service singleton."""
    global _retrieval_service
    if _retrieval_service is not None:
        return _retrieval_service
    from app.core.config import settings
    from app.services.rag.embeddings import EmbeddingService
    from app.services.rag.retrieval import RetrievalService
    from app.services.rag.vectorstore import MilvusVectorStore

    rag_settings = settings.rag
    embedding_service = EmbeddingService(rag_settings)
    vector_store = MilvusVectorStore(rag_settings, embedding_service)
    _retrieval_service = RetrievalService(vector_store, rag_settings)
    return _retrieval_service


def get_retrieval_service() -> "BaseRetrievalService":
    """Get the RetrievalService singleton."""
    return _get_retrieval_service()


def _format_results(results: list) -> str:
    if not results:
        return "No relevant documents found in the knowledge base."
    formatted = []
    for i, result in enumerate(results, start=1):
        source = result.metadata.get("filename", "unknown")
        page = result.metadata.get("page_num", "")
        chunk = result.metadata.get("chunk_num", "")
        col = result.metadata.get("collection", "")
        page_info = f", page {page}" if page else ""
        chunk_info = f", chunk {chunk}" if chunk else ""
        col_info = f" [{col}]" if col else ""
        formatted.append(
            f"[{i}] Source: {source}{page_info}{chunk_info}{col_info} (score: {result.score:.3f})\n"
            f"{result.content}"
        )
    return "Search results (cite sources using [1], [2], etc. in your response):\n\n" + "\n\n".join(
        formatted
    )


# ContextVar set by non-PydanticAI frameworks before each agent invocation so that
# the tool can read the active KB collections without needing explicit Deps injection.
# Default is None (not []) — mutable defaults on ContextVar are a foot-gun
# because every reader gets the same shared list. Callers should treat None
# as "no collections active".
_active_kb_collections: contextvars.ContextVar[list[str] | None] = contextvars.ContextVar(
    "_active_kb_collections", default=None
)


async def search_knowledge_base(
    query: str,
    kb_collection_names: list[str] | None = None,
    top_k: int = 5,
) -> str:
    """Search the knowledge base and return formatted results.

    Args:
        query: The search query string.
        kb_collection_names: Vector-store collection names resolved server-side from the
            conversation's active_knowledge_base_ids. Never supplied by the LLM directly —
            injected via PydanticAI Deps or the _active_kb_collections ContextVar.
        top_k: Number of top results to retrieve (default: 5).
    """
    from typing import Any

    resolved = kb_collection_names if kb_collection_names else (_active_kb_collections.get() or [])
    if not resolved:
        return "No active knowledge bases selected for this conversation."

    service: Any = get_retrieval_service()
    try:
        if len(resolved) == 1:
            results = await service.retrieve(query=query, collection_name=resolved[0], limit=top_k)
        else:
            results = await service.retrieve_multi(
                query=query, collection_names=resolved, limit=top_k
            )
    except Exception as e:
        logger.error("Knowledge base search failed: %s", e)
        return f"Error accessing knowledge base: {e}"

    return _format_results(results)


def _run_async_search(query: str, kb_collection_names: list[str], top_k: int) -> str:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            search_knowledge_base(query, kb_collection_names, top_k=top_k)
        )
    finally:
        loop.close()


def search_knowledge_base_sync(
    query: str,
    kb_collection_names: list[str] | None = None,
    top_k: int = 5,
) -> str:
    """Synchronous wrapper for search_knowledge_base. Use in CrewAI agents."""
    logger.debug(
        "search_knowledge_base_sync called: query=%s, kb_collections=%s, top_k=%s",
        query,
        kb_collection_names,
        top_k,
    )
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_async_search, query, kb_collection_names or [], top_k)
            result = future.result()
        logger.debug("search_knowledge_base_sync completed successfully")
        return result
    except Exception as e:
        logger.error("search_knowledge_base_sync failed: %s", str(e), exc_info=True)
        raise


__all__ = ["search_knowledge_base", "search_knowledge_base_sync"]
