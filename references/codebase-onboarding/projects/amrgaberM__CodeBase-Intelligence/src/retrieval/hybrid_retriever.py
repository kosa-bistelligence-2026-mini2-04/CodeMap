"""Hybrid retriever combining dense and sparse search."""

from typing import Dict, List, Any, Optional, Set
from ..chunking import CodeChunk
from ..utils import logger
from .vector_store import VectorStore
from .bm25_retriever import BM25Retriever


# File priority patterns
HIGH_PRIORITY_FILES = ["main.py", "__init__.py", "app.py", "core.py", "cli.py", "api.py"]
LOW_PRIORITY_PATTERNS = ["docs/management", "docs/release", ".pre-commit", "conftest", "setup.py"]


class HybridRetriever:
    """Advanced hybrid retriever with multi-hop and dependency awareness."""
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        bm25_weight: float = 0.3,
        dense_weight: float = 0.7,
    ):
        self.vector_store = vector_store or VectorStore()
        self.bm25_retriever = BM25Retriever()
        self.bm25_weight = bm25_weight
        self.dense_weight = dense_weight
        self._chunks: List[CodeChunk] = []
        self._file_to_chunks: Dict[str, List[str]] = {}
        self._dependency_graph = None
        self._graph_builder = None
        
    def index(self, chunks: List[CodeChunk], files: List = None) -> None:
        """Index chunks and optionally build dependency graph."""
        logger.info(f"Indexing {len(chunks)} chunks")
        
        # Reset everything for fresh index
        self._chunks = chunks
        self._file_to_chunks = {}
        
        # Create fresh BM25 retriever
        self.bm25_retriever = BM25Retriever()
        
        # Create fresh vector store (this forces complete reset)
        self.vector_store = VectorStore()
        
        # Build file to chunks mapping
        for chunk in chunks:
            file_path = chunk.file_path
            if file_path not in self._file_to_chunks:
                self._file_to_chunks[file_path] = []
            self._file_to_chunks[file_path].append(chunk.chunk_id)
        
        # Index in vector store
        self.vector_store.add_chunks(chunks)
        
        # Index in BM25
        self.bm25_retriever.index(chunks)
        
        # Build dependency graph if files provided
        if files:
            self._build_dependency_graph(files)
        
        logger.info("Hybrid indexing complete")
    
    def _build_dependency_graph(self, files: List) -> None:
        """Build dependency graph from files."""
        try:
            from ..utils.dependency_graph import DependencyGraphBuilder
            builder = DependencyGraphBuilder()
            self._dependency_graph = builder.build_graph(files)
            self._graph_builder = builder
        except Exception as e:
            logger.warning(f"Could not build dependency graph: {e}")
            self._dependency_graph = None
            self._graph_builder = None
    
    def _is_overview_question(self, query: str) -> bool:
        """Detect if query is asking for project overview."""
        overview_keywords = [
            "what is", "what does", "core idea", "purpose", "overview",
            "main feature", "about this", "explain this project",
            "how does this work", "what's this repo", "what is this"
        ]
        query_lower = query.lower()
        return any(kw in query_lower for kw in overview_keywords)
    
    def _is_high_priority_file(self, file_path: str) -> bool:
        """Check if file is high priority."""
        file_name = file_path.split("/")[-1]
        # Check exact matches
        if file_name in HIGH_PRIORITY_FILES:
            return True
        # Check if it's a main module __init__.py (not in tests/docs)
        if file_name == "__init__.py" and "test" not in file_path.lower() and "docs" not in file_path.lower():
            return True
        return False
    
    def _is_low_priority_file(self, file_path: str) -> bool:
        """Check if file should be deprioritized."""
        file_lower = file_path.lower()
        return any(lp in file_lower for lp in LOW_PRIORITY_PATTERNS)
    
    def _rerank_for_overview(self, results: List[Dict]) -> List[Dict]:
        """Rerank results for overview questions - prioritize core code."""
        for result in results:
            file_path = result.get("metadata", {}).get("file_path", "")
            chunk_type = result.get("metadata", {}).get("chunk_type", "")
            
            # Boost high priority files
            if self._is_high_priority_file(file_path):
                result["score"] = result.get("score", 0) + 0.3
            
            # Boost classes and main functions
            if chunk_type in ["class", "module"]:
                result["score"] = result.get("score", 0) + 0.2
            
            # Penalize low priority files
            if self._is_low_priority_file(file_path):
                result["score"] = result.get("score", 0) - 0.4
            
            # Penalize docs that aren't README
            if "docs/" in file_path and "readme" not in file_path.lower():
                result["score"] = result.get("score", 0) - 0.3
        
        # Re-sort by adjusted score
        return sorted(results, key=lambda x: x.get("score", 0), reverse=True)
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        use_hybrid: bool = True,
        use_dependencies: bool = True,
        filter_dict: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """Search with hybrid retrieval and dependency expansion."""
        
        if not use_hybrid:
            return self.vector_store.search(query, top_k, filter_dict)
        
        # Get initial results
        fetch_k = top_k * 3
        
        dense_results = self.vector_store.search(query, fetch_k, filter_dict)
        bm25_results = self.bm25_retriever.search(query, fetch_k)
        
        # If no results, return empty
        if not dense_results and not bm25_results:
            return []
        
        # Combine with RRF
        combined = self._reciprocal_rank_fusion(dense_results, bm25_results)
        
        # Smart reranking for overview questions
        if self._is_overview_question(query):
            combined = self._rerank_for_overview(combined)
        
        # Expand with dependencies
        if use_dependencies and self._graph_builder is not None and combined:
            combined = self._expand_with_dependencies(combined, top_k)
        
        return combined[:top_k]
    
    def _reciprocal_rank_fusion(
        self,
        dense_results: List[Dict],
        bm25_results: List[Dict],
        k: int = 60,
    ) -> List[Dict[str, Any]]:
        """Combine results using Reciprocal Rank Fusion."""
        scores: Dict[str, Dict] = {}
        
        for rank, result in enumerate(dense_results):
            chunk_id = result["chunk_id"]
            scores[chunk_id] = {
                "chunk_id": chunk_id,
                "content": result["content"],
                "metadata": result["metadata"],
                "rrf_score": self.dense_weight / (k + rank + 1),
                "dense_score": result.get("score", 0),
                "dense_rank": rank + 1,
            }
        
        for rank, result in enumerate(bm25_results):
            chunk_id = result["chunk_id"]
            bm25_contribution = self.bm25_weight / (k + rank + 1)
            
            if chunk_id in scores:
                scores[chunk_id]["rrf_score"] += bm25_contribution
                scores[chunk_id]["bm25_score"] = result.get("score", 0)
                scores[chunk_id]["bm25_rank"] = rank + 1
            else:
                scores[chunk_id] = {
                    "chunk_id": chunk_id,
                    "content": result["content"],
                    "metadata": result.get("metadata", {}),
                    "rrf_score": bm25_contribution,
                    "bm25_score": result.get("score", 0),
                    "bm25_rank": rank + 1,
                }
        
        if not scores:
            return []
        
        combined = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
        
        results = []
        for item in combined:
            results.append({
                "chunk_id": item["chunk_id"],
                "content": item["content"],
                "metadata": item["metadata"],
                "score": item["rrf_score"],
                "dense_rank": item.get("dense_rank"),
                "bm25_rank": item.get("bm25_rank"),
            })
        
        return results
    
    def _expand_with_dependencies(
        self,
        results: List[Dict],
        top_k: int,
    ) -> List[Dict[str, Any]]:
        """Expand results with related files from dependency graph."""
        if not results or self._graph_builder is None:
            return results
        
        # Get files from top results
        top_files: Set[str] = set()
        for r in results[:5]:
            file_path = r.get("metadata", {}).get("file_path", "")
            if file_path:
                top_files.add(file_path)
        
        if not top_files:
            return results
        
        # Find related files
        related_files: Set[str] = set()
        for file_path in top_files:
            try:
                related = self._graph_builder.get_related_files(file_path, depth=1)
                related_files.update(related)
            except:
                pass
        
        # Remove files already in results
        existing_files = {r.get("metadata", {}).get("file_path", "") for r in results}
        new_files = related_files - existing_files
        
        # Add chunks from related files with lower score
        existing_ids = {r["chunk_id"] for r in results}
        
        for file_path in list(new_files)[:3]:
            if file_path in self._file_to_chunks:
                for chunk_id in self._file_to_chunks[file_path][:2]:
                    if chunk_id not in existing_ids:
                        for chunk in self._chunks:
                            if chunk.chunk_id == chunk_id:
                                results.append({
                                    "chunk_id": chunk_id,
                                    "content": chunk.content,
                                    "metadata": {
                                        "file_path": chunk.file_path,
                                        "chunk_type": chunk.chunk_type,
                                        "name": chunk.name,
                                        "start_line": chunk.start_line,
                                        "end_line": chunk.end_line,
                                        "language": chunk.language,
                                        "from_dependency": True,
                                    },
                                    "score": 0.1,
                                    "from_dependency": True,
                                })
                                existing_ids.add(chunk_id)
                                break
        
        return results
    
    def search_with_context(
        self,
        query: str,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """Search and return results with rich context."""
        results = self.search(query, top_k=top_k)
        
        # Group by file
        files_dict: Dict[str, List] = {}
        for r in results:
            file_path = r.get("metadata", {}).get("file_path", "unknown")
            if file_path not in files_dict:
                files_dict[file_path] = []
            files_dict[file_path].append(r)
        
        # Get dependency info
        dependency_info = {}
        if self._graph_builder is not None:
            for file_path in files_dict.keys():
                try:
                    dependency_info[file_path] = {
                        "imports": self._graph_builder.get_dependencies(file_path),
                        "imported_by": self._graph_builder.get_dependents(file_path),
                    }
                except:
                    pass
        
        return {
            "results": results,
            "files": files_dict,
            "dependencies": dependency_info,
            "total_results": len(results),
        }
