"""Pydantic schemas for API."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Request to ingest a repository."""
    
    repo_url: str = Field(..., description="GitHub repository URL")
    branch: Optional[str] = Field(None, description="Branch to clone")
    force: bool = Field(False, description="Force re-clone if exists")


class IngestResponse(BaseModel):
    """Response after ingestion."""
    
    success: bool
    repo_name: str
    files_processed: int
    chunks_created: int
    message: str


class QueryRequest(BaseModel):
    """Request to query the codebase."""
    
    query: str = Field(..., description="Question about the codebase")
    top_k: int = Field(5, description="Number of chunks to retrieve")
    use_reranking: bool = Field(True, description="Use reranking")
    filter_file: Optional[str] = Field(None, description="Filter to specific file")


class ChunkInfo(BaseModel):
    """Information about a retrieved chunk."""
    
    chunk_id: str
    file_path: str
    chunk_type: str
    name: Optional[str]
    start_line: int
    end_line: int
    score: float
    content: str


class QueryResponse(BaseModel):
    """Response to a query."""
    
    query: str
    answer: str
    sources: List[ChunkInfo]
    retrieval_time_ms: float
    generation_time_ms: float


class ExplainRequest(BaseModel):
    """Request to explain a function."""
    
    file_path: str = Field(..., description="Path to file")
    function_name: str = Field(..., description="Function to explain")


class ExplainResponse(BaseModel):
    """Response with function explanation."""
    
    function_name: str
    file_path: str
    code: str
    explanation: str


class StatsResponse(BaseModel):
    """System statistics."""
    
    collection_name: str
    total_chunks: int
    repos_indexed: List[str]
