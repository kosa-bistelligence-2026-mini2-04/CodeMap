from abc import ABC, abstractmethod

from openai import OpenAI

from app.services.rag.config import RAGSettings
from app.services.rag.models import Document


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers.

    Defines the interface that all embedding providers must implement.
    """

    @abstractmethod
    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of query texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors, one for each input text.
        """
        pass

    @abstractmethod
    def embed_document(self, document: Document) -> list[list[float]]:
        """Embed all chunks of a document.

        Args:
            document: Document object containing chunked pages to embed.

        Returns:
            List of embedding vectors, one for each chunk in the document.
        """
        pass

    @abstractmethod
    def warmup(self) -> None:
        """Ensures the model is loaded and ready for inference."""
        pass


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI embedding provider using the OpenAI API.

    Uses OpenAI's embedding models to generate text embeddings.
    """

    def __init__(self, model: str) -> None:
        """Initialize the OpenAI embedding provider.

        Args:
            model: The OpenAI embedding model name (e.g., 'text-embedding-3-small').
        """
        self.model = model
        self.client = OpenAI()

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of query texts using OpenAI.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.
        """
        response = self.client.embeddings.create(model=self.model, input=texts)
        return [data.embedding for data in response.data]

    def embed_document(self, document: Document) -> list[list[float]]:
        """Embed all chunks of a document using OpenAI.

        Args:
            document: Document object containing chunked pages.

        Returns:
            List of embedding vectors for each chunk.
        """
        texts = [
            doc.chunk_content if doc.chunk_content else "" for doc in (document.chunked_pages or [])
        ]
        return self.embed_queries(texts)

    def warmup(self) -> None:
        """Warmup method for OpenAI client.

        OpenAI API is a remote service, so this is a no-op.
        """
        pass


# Embedding orchestrator
class EmbeddingService:
    """Service for managing text embeddings.

    Orchestrates embedding operations using a configured embedding provider.
    Supports multiple backends: OpenAI, Voyage AI, and Sentence Transformers.
    """

    def __init__(self, settings: RAGSettings):
        """Initialize the embedding service.

        Args:
            settings: RAG configuration settings.
        """
        config = settings.embeddings_config
        self.expected_dim = config.dim
        self.provider = OpenAIEmbeddingProvider(model=config.model)

    def embed_query(self, query: str) -> list[float]:
        """Embed a single query text.

        Args:
            query: The text query to embed.

        Returns:
            Embedding vector for the query.
        """
        result = self.provider.embed_queries([query])[0]
        if len(result) != self.expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.expected_dim}, "
                f"got {len(result)}. Check your embedding model configuration."
            )
        return result

    def embed_document(self, document: Document) -> list[list[float]]:
        """Embed all chunks of a document.

        Args:
            document: Document object containing chunked pages.

        Returns:
            List of embedding vectors for each chunk.
        """
        results = self.provider.embed_document(document)
        if results and len(results[0]) != self.expected_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.expected_dim}, "
                f"got {len(results[0])}. Check your embedding model configuration."
            )
        return results

    def warmup(self) -> None:
        """Ensures the provider is ready for usage."""
        self.provider.warmup()
