# app/ingestion/indexer.py
import uuid
import asyncpg
from pgvector.asyncpg import register_vector
from app.ingestion.chunker import CodeChunk


async def upsert_chunks(
    conn: asyncpg.Connection,
    repo_id: str,
    chunks: list[CodeChunk],
    embeddings: list[list[float]],
) -> None:
    """Batch upsert chunks + embeddings into pgvector.
    Uses ON CONFLICT to safely re-index without duplicates."""

    await register_vector(conn)

    records = [
        (
            str(uuid.uuid4()),   # id — must be supplied; no DB default
            repo_id,
            c.file_path,
            c.language,
            c.chunk_type,
            c.name,
            c.start_line,
            c.end_line,
            c.content,
            c.context_prefix,
            emb,
        )
        for c, emb in zip(chunks, embeddings)
    ]

    await conn.executemany(
        """
        INSERT INTO chunks (
            id, repo_id, file_path, language, chunk_type, name,
            start_line, end_line, content, context_prefix, embedding
        )
        VALUES (
            $1::uuid, $2::uuid, $3, $4, $5, $6,
            $7, $8, $9, $10, $11::vector
        )
        ON CONFLICT (repo_id, file_path, start_line)
        DO UPDATE SET
            content        = EXCLUDED.content,
            context_prefix = EXCLUDED.context_prefix,
            embedding      = EXCLUDED.embedding,
            chunk_type     = EXCLUDED.chunk_type,
            name           = EXCLUDED.name,
            end_line       = EXCLUDED.end_line
        """,
        records,
    )
    print(f"[indexer] upserted {len(records)} chunks for repo {repo_id}")