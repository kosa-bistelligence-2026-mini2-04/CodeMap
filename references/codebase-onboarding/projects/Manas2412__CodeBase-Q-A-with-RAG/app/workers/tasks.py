import asyncio
import os
import asyncpg
from celery import Celery
from pgvector.asyncpg import register_vector
from dotenv import load_dotenv
from voyageai.error import RateLimitError

from app.ingestion.cloner import clone_repo, walk_code_files, cleanup_repo
from app.ingestion.chunker import chunk_file
from app.ingestion.embedder import embed_chunks
from app.ingestion.indexer import upsert_chunks

load_dotenv()

celery = Celery(
    "codeqa",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

def get_dsn():
    raw_url = os.getenv("DATABASE_URL", "")
    db_url = raw_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgres://", "postgresql://")
    return db_url.split("?")[0]

def should_not_retry(exc: Exception) -> bool:
    """
    Some vendor errors will not recover by waiting/retrying.
    In particular, Voyage 429 due to missing payment method is persistent until
    billing is configured, so retrying causes repeated work and logs.
    """
    if isinstance(exc, RateLimitError) and getattr(exc, "http_status", None) == 429:
        text = str(exc).lower()
        return ("payment method" in text) or ("billing page" in text)
    return False

@celery.task(bind=True, max_retries=3, default_retry_delay=10)
def index_repo_task(self, repo_id: str, github_url: str):
    try:
        asyncio.run(_index_repo(repo_id, github_url))
    except Exception as exc:
        if should_not_retry(exc):
            # Status is already set to 'error' in _index_repo; just stop retrying.
            print(f"[indexer] non-retryable error (no retries): {exc}")
            raise
        raise self.retry(exc=exc)


async def _index_repo(repo_id: str, github_url: str):
    conn = None
    repo_path = None
    try:
        dsn = get_dsn()
        conn = await asyncpg.connect(dsn=dsn, ssl=True)
        await register_vector(conn)

        # Mark as indexing
        await conn.execute(
            "UPDATE repos SET status = 'indexing' WHERE id = $1::uuid", repo_id
        )

        repo_path = await clone_repo(github_url)
        
        all_chunks = []
        for file_path, source, language in walk_code_files(repo_path):
            chunks = chunk_file(file_path, source, language)
            all_chunks.extend(chunks)

        print(f"[indexer] {len(all_chunks)} chunks from {github_url}")

        embeddings = await embed_chunks(all_chunks)
        await upsert_chunks(conn, repo_id, all_chunks, embeddings)

        await conn.execute(
            """
            UPDATE repos
            SET status = 'ready', indexed_at = now()
            WHERE id = $1::uuid
            """,
            repo_id,
        )
        print(f"[indexer] done - repo {repo_id} is ready")

    except Exception as e:
        print(f"[indexer] error indexing {github_url}: {e}")
        if conn:
            await conn.execute(
                "UPDATE repos SET status = 'error' WHERE id = $1::uuid", repo_id
            )
        raise e

    finally:
        if repo_path:
            cleanup_repo(repo_path)
        if conn:
            await conn.close()