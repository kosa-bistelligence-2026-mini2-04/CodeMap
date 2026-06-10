{%- if cookiecutter.enable_rag %}
from abc import ABC, abstractmethod

{%- if cookiecutter.use_openai_embeddings %}
from openai import OpenAI
{%- endif %}

{%- if cookiecutter.use_voyage_embeddings %}
from voyageai import Client
{%- endif %}

{%- if cookiecutter.use_sentence_transformers %}
from sentence_transformers import SentenceTransformer
{%- endif %}

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

{%- if cookiecutter.use_openai_embeddings %}
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
        texts = [doc.chunk_content if doc.chunk_content else "" for doc in (document.chunked_pages or [])]
        return self.embed_queries(texts)

    def warmup(self) -> None:
        """Warmup method for OpenAI client.

        OpenAI API is a remote service, so this is a no-op.
        """
        pass
{%- endif %}

{%- if cookiecutter.use_voyage_embeddings %}
class VoyageEmbeddingProvider(BaseEmbeddingProvider):
    """Voyage AI embedding provider using the Voyage API.

    Uses Voyage's embedding models to generate text embeddings.
    """

    def __init__(self, model: str) -> None:
        """Initialize the Voyage AI embedding provider.

        Args:
            model: The Voyage AI model name (e.g., 'voyage-3').
        """
        self.model = model
        self.client = Client()

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        """Embed a list of query texts using Voyage AI.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.
        """
        return self.client.embed(texts, model=self.model, input_type="query").embeddings

    def embed_document(self, document: Document) -> list[list[float]]:
        """Embed all chunks of a document using Voyage AI.

        Args:
            document: Document object containing chunked pages.

        Returns:
            List of embedding vectors for each chunk.
        """
        texts = [doc.chunk_content if doc.chunk_content else "" for doc in (document.chunked_pages or [])]
        return self.client.embed(texts, model=self.model, input_type="document").embeddings

    def warmup(self) -> None:
        """Warmup method for Voyage AI client.

        Voyage AI is a remote service, so this is a no-op.
        """
        pass
{%- endif %}

{%- if cookiecutter.use_gemini_embeddings %}
from google import genai
from google.genai import types as genai_types
{%- endif %}

{%- if cookiecutter.use_gemini_embeddings %}
class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini multimodal embedding provider.

    Supports text, images, and documents in a single embedding space.
    Uses the Gemini Embedding 2 model for natively multimodal embeddings.
    """

    def __init__(self, model: str, api_key: str = "") -> None:
        self.model = model
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        result = self.client.models.embed_content(
            model=self.model,
            contents=texts,
        )
        return [e.values for e in result.embeddings]

    def embed_document(self, document: Document) -> list[list[float]]:
        contents = []
        for chunk in (document.chunked_pages or []):
            contents.append(chunk.chunk_content if chunk.chunk_content else "")
        result = self.client.models.embed_content(
            model=self.model,
            contents=contents,
        )
        return [e.values for e in result.embeddings]

    def embed_image(self, image_bytes: bytes, mime_type: str = "image/png") -> list[float]:
        """Embed an image directly (multimodal).

        Returns a vector in the same space as text embeddings.
        """
        result = self.client.models.embed_content(
            model=self.model,
            contents=[
                genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        )
        return result.embeddings[0].values

    def warmup(self) -> None:
        pass
{%- endif %}

{%- if cookiecutter.use_sentence_transformers %}
from app.core.config import settings as app_settings

class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, model: str) -> None:
        self.model_name = model
        self._model = None

    @property
    def model(self) -> SentenceTransformer:
        """Lazy load model to avoid loading at import time."""
        if self._model is None:
            # Ensure the cache directory exists
            app_settings.MODELS_CACHE_DIR.mkdir(exist_ok=True, parents=True)
            self._model = SentenceTransformer(
                self.model_name,
                cache_folder=str(app_settings.MODELS_CACHE_DIR)
            )
        return self._model

    def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True
            ).tolist()

    def embed_document(self, document: Document) -> list[list[float]]:
        texts = [doc.chunk_content if doc.chunk_content else "" for doc in (document.chunked_pages or [])]
        return self.embed_queries(texts)

    def warmup(self) -> None:
        """Trigger model download and load into memory."""
        _ = self.model
{%- endif %}

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
        {%- if cookiecutter.use_openai_embeddings %}
        self.provider = OpenAIEmbeddingProvider(model=config.model)
        {%- elif cookiecutter.use_voyage_embeddings %}
        self.provider = VoyageEmbeddingProvider(model=config.model)
        {%- elif cookiecutter.use_gemini_embeddings %}
        from app.core.config import settings as app_settings
        self.provider = GeminiEmbeddingProvider(model=config.model, api_key=app_settings.GOOGLE_API_KEY)
        {%- elif cookiecutter.use_sentence_transformers %}
        self.provider = SentenceTransformerEmbeddingProvider(model=config.model)
        {%- endif %}

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

{%- endif %}
