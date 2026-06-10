import asyncpg
import cohere
import voyageai
import hashlib
import json
import os
import uuid
from pgvector.asyncpg import register_vector
from app.query.hyde import hyde_expand
from dotenv import load_dotenv

load_dotenv()

voyage_client = voyageai.AsyncClient(api_key=os.getenv("VOYAGE_API_KEY"))
cohere_client = cohere.AsyncClient(os.getenv("COHERE_API_KEY"))


async def retrieve(
    query: str,
    repo_id: uuid.UUID,           # Fix: use UUID type, not str
    conn: asyncpg.Connection,
    redis_client,
    top_k: int = 5,
) -> list[dict]:

    # Fix: include top_k in the cache key so different top_k values don't collide
    cache_key = f"query:{hashlib.sha256(f'{query}{repo_id}{top_k}'.encode()).hexdigest()}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # HyDE: embed a hypothetical answer, not the raw question
    hypothetical = await hyde_expand(query)
    embed_result = await voyage_client.embed(
        [hypothetical],
        model="voyage-code-2",
        input_type="query",
    )
    vec = embed_result.embeddings[0]

    # Vector search: top 20 candidates from pgvector
    await register_vector(conn)
    rows = await conn.fetch(
        """
        SELECT
          id,
          content,
          context_prefix,
          file_path,
          start_line,
          end_line,
          1 - (embedding <=> $1::vector) AS similarity
        FROM chunks
        WHERE repo_id = $2
        ORDER BY embedding <=> $1::vector
        LIMIT 20
        """,
        vec,
        repo_id,   # Fix: pass uuid.UUID directly, not a str
    )

    if not rows:
        return []

    # Cohere rerank: compress 20 -> top_k
    docs = [r["content"] for r in rows]
    try:
        rerank_result = await cohere_client.rerank(
            query=query,
            documents=docs,
            model="rerank-english-v3.0",
            top_n=top_k,
        )
        results = [
            {
                "content": rows[r.index]["content"],
                "context_prefix": rows[r.index]["context_prefix"],
                "file_path": rows[r.index]["file_path"],
                "start_line": rows[r.index]["start_line"],
                "end_line": rows[r.index]["end_line"],
                "relevance_score": r.relevance_score,
            }
            for r in rerank_result.results
        ]
    except Exception as e:
        # Fix: fallback to raw vector results if Cohere rerank fails
        print(f"[retriever] Cohere rerank failed, falling back to vector results: {e}")
        results = [
            {
                "content": r["content"],
                "context_prefix": r["context_prefix"],
                "file_path": r["file_path"],
                "start_line": r["start_line"],
                "end_line": r["end_line"],
                "relevance_score": float(r["similarity"]),
            }
            for r in rows[:top_k]
        ]

    # Cache for 1 hour; guard against non-serialisable floats (NaN/inf)
    await redis_client.setex(
        cache_key, 3600,
        json.dumps(results, default=lambda x: str(x))
    )
    return results
