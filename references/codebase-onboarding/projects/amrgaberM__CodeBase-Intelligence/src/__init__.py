"""CodeBase Intelligence RAG - Main package."""

from .ingestion import GitHubLoader, FileContent, CodeElement
from .chunking import ASTChunker, SemanticChunker, CodeChunk
from .embeddings import CodeEmbedder, HybridEmbedder
from .retrieval import VectorStore, HybridRetriever, BM25Retriever
from .generation import CodeGenerator
from .evaluation import RAGEvaluator

__version__ = "1.0.0"

__all__ = [
    # Ingestion
    "GitHubLoader",
    "FileContent",
    "CodeElement",
    # Chunking
    "ASTChunker",
    "SemanticChunker",
    "CodeChunk",
    # Embeddings
    "CodeEmbedder",
    "HybridEmbedder",
    # Retrieval
    "VectorStore",
    "HybridRetriever",
    "BM25Retriever",
    # Generation
    "CodeGenerator",
    # Evaluation
    "RAGEvaluator",
]
