from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(
    title="CodeLens API",
    description="AI-powered codebase intelligence",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
state = {
    "retriever": None,
    "generator": None,
    "reranker": None,
    "intelligence": None,
    "indexed": False,
}

class IndexRequest(BaseModel):
    repo_url: str

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5

class QueryResponse(BaseModel):
    answer: str
    sources: List[dict]
    time_ms: float

@app.get("/")
def root():
    return {"name": "CodeLens API", "status": "running"}

@app.get("/health")
def health():
    return {"status": "healthy", "indexed": state["indexed"]}

@app.post("/index")
def index_repo(request: IndexRequest):
    from src.ingestion import GitHubLoader
    from src.chunking import ASTChunker
    from src.retrieval import HybridRetriever, LightweightReranker
    from src.generation import CodeGenerator, CodeIntelligence
    
    try:
        loader = GitHubLoader()
        files = loader.clone_repo(request.repo_url)
        
        chunker = ASTChunker()
        chunks = chunker.chunk_files(files)
        
        state["retriever"] = HybridRetriever()
        state["generator"] = CodeGenerator()
        state["reranker"] = LightweightReranker()
        state["retriever"].index(chunks, files)
        state["intelligence"] = CodeIntelligence(state["retriever"], state["generator"])
        state["indexed"] = True
        
        return {
            "success": True,
            "files": len(files),
            "chunks": len(chunks)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):
    import time
    
    if not state["indexed"]:
        raise HTTPException(status_code=400, detail="No repository indexed")
    
    try:
        start = time.time()
        results = state["retriever"].search(request.query, top_k=request.top_k * 2)
        results = state["reranker"].rerank(request.query, results, top_k=request.top_k)
        answer = state["generator"].generate(request.query, results)
        elapsed = (time.time() - start) * 1000
        
        sources = []
        for r in results[:5]:
            meta = r.get("metadata", {})
            sources.append({
                "file": meta.get("file_path", ""),
                "name": meta.get("name", ""),
                "type": meta.get("chunk_type", "")
            })
        
        return QueryResponse(answer=answer, sources=sources, time_ms=elapsed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/explain")
def explain(name: str):
    if not state["indexed"]:
        raise HTTPException(status_code=400, detail="No repository indexed")
    return state["intelligence"].explain_function(name)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
