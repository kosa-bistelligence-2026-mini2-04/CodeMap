"""Fast embeddings using local SentenceTransformers."""

from typing import List, Union
import numpy as np
from src.utils.logger import logger


class CodeEmbedder:
    """Fast embeddings optimized for free-tier cloud deployment."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedder.
        
        Using MiniLM for speed on CPU-only environments.
        """
        self.model_name = model_name
        self._model = None
        self._dimension = 384
        logger.info(f"Embedder initialized: {self.model_name} ({self._dimension} dim)")
    
    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}...")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded")
        return self._model
    
    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        """Embed text(s) into vectors."""
        if isinstance(texts, str):
            texts = [texts]
        
        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=64,
            show_progress_bar=False,
        )
        
        return np.array(embeddings)
    
    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query."""
        return self.embed(query)[0]
    
    def embed_documents(self, documents: List[str]) -> np.ndarray:
        """Embed multiple documents efficiently."""
        if not documents:
            return np.array([])
        
        embeddings = self.model.encode(
            documents,
            normalize_embeddings=True,
            batch_size=64,
            show_progress_bar=len(documents) > 200,
        )
        
        return np.array(embeddings)
    
    @property
    def dimension(self) -> int:
        """Embedding dimension."""
        return self._dimension
