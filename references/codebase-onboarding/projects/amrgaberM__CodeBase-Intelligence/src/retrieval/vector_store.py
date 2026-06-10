"""Vector store implementation using ChromaDB."""

from typing import Dict, List, Optional, Any

import chromadb

from src.utils.logger import logger


class VectorStore:
    """Vector store for code chunks using ChromaDB."""
    
    def __init__(
        self,
        collection_name: Optional[str] = None,
        embedder=None,
    ):
        self.collection_name = collection_name or "codebase"
        self._embedder = embedder
        self._client = None
        self._collection = None
        
        logger.info(f"VectorStore initialized: {self.collection_name}")
    
    @property
    def embedder(self):
        if self._embedder is None:
            from src.embeddings import CodeEmbedder
            self._embedder = CodeEmbedder()
        return self._embedder
    
    @property
    def client(self) -> chromadb.ClientAPI:
        if self._client is None:
            self._client = chromadb.EphemeralClient()
        return self._client
    
    @property
    def collection(self) -> chromadb.Collection:
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        return self._collection
    
    def reset(self) -> None:
        """Completely reset the vector store - new client and collection."""
        logger.info("Resetting vector store completely...")
        
        # Force create a brand new client (discards all in-memory data)
        self._client = chromadb.EphemeralClient()
        self._collection = None
        
        logger.info("Vector store reset complete")
    
    def add_chunks(self, chunks: List, batch_size: int = 50) -> None:
        """Add chunks to vector store. Resets existing data first."""
        if not chunks:
            logger.warning("No chunks to add")
            return
        
        # IMPORTANT: Complete reset before adding new chunks
        self.reset()
        
        logger.info(f"Adding {len(chunks)} chunks to vector store")
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            
            ids = [chunk.chunk_id for chunk in batch]
            documents = [chunk.to_embedding_text() for chunk in batch]
            metadatas = [self._prepare_metadata(chunk) for chunk in batch]
            
            embeddings = self.embedder.embed_documents(documents)
            
            self.collection.add(
                ids=ids,
                embeddings=embeddings.tolist(),
                documents=documents,
                metadatas=metadatas,
            )
            
            progress = min(100, int((i + batch_size) / len(chunks) * 100))
            logger.info(f"Indexing progress: {progress}%")
        
        logger.info(f"Successfully added {len(chunks)} chunks")
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        filter_dict: Optional[Dict] = None,
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks."""
        count = self.collection.count()
        if count == 0:
            logger.warning("Collection is empty, no results to return")
            return []
        
        query_embedding = self.embedder.embed_query(query)
        where = filter_dict if filter_dict else None
        
        results = self.collection.query(
            query_embeddings=[query_embedding.tolist()],
            n_results=min(top_k, count),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        
        formatted = []
        if results["ids"] and results["ids"][0]:
            for i in range(len(results["ids"][0])):
                formatted.append({
                    "chunk_id": results["ids"][0][i],
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": 1 - results["distances"][0][i],
                })
        
        return formatted
    
    def delete_collection(self) -> None:
        """Delete the collection and reset state."""
        self.reset()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        return {
            "name": self.collection_name,
            "count": self.collection.count(),
        }
    
    def _prepare_metadata(self, chunk) -> Dict[str, Any]:
        """Prepare metadata for storage in ChromaDB."""
        metadata = {
            "file_path": chunk.file_path,
            "chunk_type": chunk.chunk_type,
            "language": chunk.language,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
        }
        
        if chunk.name:
            metadata["name"] = chunk.name
        if chunk.parent:
            metadata["parent"] = chunk.parent
        if hasattr(chunk, 'metadata'):
            if chunk.metadata.get("repo_name"):
                metadata["repo_name"] = chunk.metadata["repo_name"]
            if chunk.metadata.get("docstring"):
                metadata["docstring"] = chunk.metadata["docstring"][:500]
        if chunk.imports:
            metadata["imports"] = ",".join(chunk.imports[:20])
        
        return metadata
