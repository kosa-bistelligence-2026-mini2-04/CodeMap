import os 
import uuid
import asyncpg
import asyncio
import redis.asyncio as aioredis
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from app.query.retriever import retrieve
from app.query.answerer import stream_answer
from app.workers.tasks import index_repo_task

load_dotenv()

# Connection pool
db_pool: asyncpg.Pool = None
redis_pool: aioredis.Redis = None

def get_dsn():
    raw_url = os.getenv("DATABASE_URL", "")
    db_url = raw_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgres://", "postgresql://")
    return db_url.split("?")[0]

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db_pool, redis_pool
    
    dsn = get_dsn()
    db_pool = await asyncpg.create_pool(dsn, ssl=True)
    
    redis_pool = aioredis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True
    )
    yield 
    await db_pool.close()
    await redis_pool.aclose()
    
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/response models
class AddRequest(BaseModel):
    github_url: str
    
class QueryRequest(BaseModel):
    repo_id: str
    question: str

# Endpoints
@app.post("/repos")
async def add_repo(body: AddRequest):
    """Enqueue indexing job. Returns immediately - indexing runs in background.""" 
    async with db_pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id, status FROM repos WHERE github_url = $1", body.github_url
        )
        if existing:
            return {"repo_id": str(existing["id"]), "status": existing["status"]}
        
        repo_id = uuid.uuid4()
        await conn.execute(
            """
            INSERT INTO repos (id, github_url, status)
            VALUES ($1, $2, 'pending')
            """,
            repo_id, body.github_url
        )
        
    index_repo_task.delay(str(repo_id), body.github_url)
    return {"repo_id": str(repo_id), "status": "pending"}

@app.get("/repos/{repo_id}/status")
async def repo_status(repo_id: str):
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT status, indexed_at FROM repos WHERE id = $1::uuid", repo_id
        )        
    if not row:
        raise HTTPException(status_code=404, detail="Repo not found")
    return {
        "status": row["status"],
        "indexed_at": str(row["indexed_at"]) if row["indexed_at"] else None
    }

@app.post("/query") # Added slash
async def query_repo(body: QueryRequest):
    """Streaming SSE endpoint - token stream back as they're generated. """
    
    # Verify repo is ready
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT status FROM repos WHERE id = $1::uuid", body.repo_id # Fixed table name to repos
        )
    if not row:
        raise HTTPException(status_code=404, detail="Repo not found")
    if row["status"] != "ready":
        raise HTTPException(status_code=400, detail=f"Repo status is '{row['status']}' — wait for indexing to finish")
    
    async def token_stream():
        async with db_pool.acquire() as conn:
            # We need to pass a UUID object to retrieve as it expects uuid.UUID or we fix retriever.py
            real_repo_id = uuid.UUID(body.repo_id)
            chunks = await retrieve(
                body.question,
                real_repo_id,
                conn,
                redis_pool
            )
            
            if not chunks:
                yield "data: No relevant code found for the question.\n\n"
                return
            
            async for token in stream_answer(body.question, chunks):
                yield f"data: {token}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(token_stream(), media_type="text/event-stream")

@app.post("/webhooks/github")
async def github_webhook(payload: dict):
    """
    Re-index on push to default branch.
    """
    default_branch = payload.get("repository", {}).get("default_branch", "main")
    if payload.get("ref") == f"refs/heads/{default_branch}":
        github_url = payload["repository"]["clone_url"]
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM repos WHERE github_url = $1", github_url
            )
            if row:
                index_repo_task.delay(str(row["id"]), github_url)
    return {"ok": True}