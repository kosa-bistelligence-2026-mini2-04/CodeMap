"""API routes for CodeBase RAG."""

import time
from typing import Optional

from fastapi import APIRouter, HTTPException

from ..ingestion import GitHubLoader
from ..chunking import ASTChunker
from ..retrieval import HybridRetriever, LightweightReranker
from ..generation import CodeGenerator
from ..utils import logger
from .schemas import (
    IngestRequest, IngestResponse,
    QueryRequest, QueryResponse, ChunkInfo,
    StatsResponse,
)

router = APIRouter()

# Global instances (initialized on first use)
_retriever: Optional[HybridRetriever] = None
_generator: Optional[CodeGenerator] = None
_reranker: Optional[LightweightReranker] = None
_indexed_repos: list = []


def get_retriever() -> HybridRetriever:
    """Get or create retriever instance."""
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


def get_generator() -> CodeGenerator:
    """Get or create generator instance."""
    global _generator
    if _generator is None:
        _generator = CodeGenerator()
    return _generator


def get_reranker() -> LightweightReranker:
    """Get or create reranker instance."""
    global _reranker
    if _reranker is None:
        _reranker = LightweightReranker()
    return _reranker


@router.post("/ingest", response_model=IngestResponse)
async def ingest_repository(request: IngestRequest):
    """Ingest a GitHub repository into the RAG system."""
    global _indexed_repos
    
    try:
        logger.info(f"Ingesting repository: {request.repo_url}")
        
        # Load repository
        loader = GitHubLoader()
        files = loader.clone_repo(
            request.repo_url,
            branch=request.branch,
            force=request.force,
        )
        
        if not files:
            raise HTTPException(status_code=400, detail="No files found in repository")
        
        # Chunk files
        chunker = ASTChunker()
        chunks = chunker.chunk_files(files)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks created from files")
        
        # Index chunks
        retriever = get_retriever()
        retriever.index(chunks)
        
        # Track indexed repo
        repo_name = loader._parse_repo_name(request.repo_url)
        if repo_name not in _indexed_repos:
            _indexed_repos.append(repo_name)
        
        return IngestResponse(
            success=True,
            repo_name=repo_name,
            files_processed=len(files),
            chunks_created=len(chunks),
            message=f"Successfully indexed {len(chunks)} chunks from {len(files)} files",
        )
        
    except Exception as e:
        logger.error(f"Ingestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query", response_model=QueryResponse)
async def query_codebase(request: QueryRequest):
    """Query the indexed codebase."""
    try:
        retriever = get_retriever()
        generator = get_generator()
        reranker = get_reranker()
        
        # Build filter if specified
        filter_dict = None
        if request.filter_file:
            filter_dict = {"file_path": request.filter_file}
        
        # Retrieve
        start_retrieval = time.time()
        results = retriever.search(
            request.query,
            top_k=request.top_k * 2,  # Get more for reranking
            filter_dict=filter_dict,
        )
        
        # Rerank
        if request.use_reranking and results:
            results = reranker.rerank(request.query, results, top_k=request.top_k)
        else:
            results = results[:request.top_k]
        
        retrieval_time = (time.time() - start_retrieval) * 1000
        
        # Generate
        start_generation = time.time()
        answer = generator.generate(request.query, results)
        generation_time = (time.time() - start_generation) * 1000
        
        # Format sources
        sources = []
        for r in results:
            metadata = r.get("metadata", {})
            sources.append(ChunkInfo(
                chunk_id=r.get("chunk_id", ""),
                file_path=metadata.get("file_path", "unknown"),
                chunk_type=metadata.get("chunk_type", "unknown"),
                name=metadata.get("name"),
                start_line=metadata.get("start_line", 0),
                end_line=metadata.get("end_line", 0),
                score=r.get("score", 0.0),
                content=r.get("content", "")[:500],  # Truncate for response
            ))
        
        return QueryResponse(
            query=request.query,
            answer=answer,
            sources=sources,
            retrieval_time_ms=retrieval_time,
            generation_time_ms=generation_time,
        )
        
    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get system statistics."""
    try:
        retriever = get_retriever()
        stats = retriever.vector_store.get_stats()
        
        return StatsResponse(
            collection_name=stats["name"],
            total_chunks=stats["count"],
            repos_indexed=_indexed_repos,
        )
        
    except Exception as e:
        logger.error(f"Stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/collection")
async def delete_collection():
    """Delete the entire collection (reset)."""
    global _indexed_repos
    
    try:
        retriever = get_retriever()
        retriever.vector_store.delete_collection()
        _indexed_repos = []
        
        return {"success": True, "message": "Collection deleted"}
        
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
