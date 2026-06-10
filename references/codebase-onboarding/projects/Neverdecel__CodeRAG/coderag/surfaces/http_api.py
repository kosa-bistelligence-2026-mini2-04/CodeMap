"""Self-hostable HTTP/REST API over a CodeRAG instance (optional ``[server]`` extra).

Lets custom apps, remote frontends, or a shared team deployment query a big codebase over
the network. Endpoints: ``GET /search``, ``POST /index``, ``GET /status``, ``GET /file``.

Note: this module intentionally does NOT use ``from __future__ import annotations`` — FastAPI
must see the real Pydantic model classes (not stringized annotations) to bind request bodies.
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from coderag.api import CodeRAG


def create_app(cr: "CodeRAG"):
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel

    app = FastAPI(
        title="CodeRAG",
        version="1.0.0",
        description="Semantic code-search engine.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    class IndexRequest(BaseModel):
        path: Optional[str] = None
        full: bool = False

    @app.get("/status")
    def status() -> dict:
        return cr.status()

    @app.get("/search")
    def search(
        q: str = Query(..., description="Search query"),
        k: int = Query(8, ge=1, le=100),
    ) -> dict:
        hits = cr.search(q, top_k=k)
        return {"query": q, "count": len(hits), "results": [h.as_dict() for h in hits]}

    @app.post("/index")
    def index(req: IndexRequest) -> dict:
        stats = cr.index(req.path, full=req.full)
        return stats.as_dict()

    @app.get("/file")
    def get_file(
        path: str = Query(...),
        start_line: Optional[int] = Query(None, ge=1),
        end_line: Optional[int] = Query(None, ge=1),
    ) -> dict:
        try:
            content = cr.get_file(path, start_line, end_line)
        except (ValueError, FileNotFoundError) as exc:
            raise HTTPException(status_code=404, detail=str(exc))
        return {"path": path, "content": content}

    return app


def run_server(cr: "CodeRAG", host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn

    # Warm the index/provider so the first request isn't slow.
    cr.status()
    uvicorn.run(create_app(cr), host=host, port=port)
