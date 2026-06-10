{%- if cookiecutter.enable_rag and cookiecutter.enable_rag_image_description %}
"""LLM-based image description for RAG document processing.

Uses the configured AI framework (PydanticAI, LangChain, etc.) to describe
images extracted from documents. Descriptions are appended to page content
before chunking, making image content searchable via text embeddings.

Configuration:
    RAG_IMAGE_DESCRIPTION_MODEL — LLM model to use (defaults to AI_MODEL from .env)
"""

import base64
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

IMAGE_DESCRIPTION_PROMPT = (
    "Describe this image in detail. Focus on any text, data, charts, diagrams, "
    "or visual information that would be useful for document search and retrieval. "
    "Be concise but comprehensive."
)


class BaseImageDescriber(ABC):
    """Abstract base for LLM-based image description."""

    @abstractmethod
    async def describe(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """Generate a text description of an image."""


def _b64_encode(image_bytes: bytes) -> str:
    """Base64-encode raw image bytes."""
    return base64.b64encode(image_bytes).decode("utf-8")


{%- if cookiecutter.use_pydantic_ai %}


class PydanticAIImageDescriber(BaseImageDescriber):
    """Image description using PydanticAI (supports all providers)."""

    def __init__(self, model_name: str | None = None):
        from app.core.config import settings
        self.model_name = model_name or getattr(settings, "RAG_IMAGE_DESCRIPTION_MODEL", None) or settings.AI_MODEL

    async def describe(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        try:
            from pydantic_ai import Agent
            from pydantic_ai.messages import BinaryContent

            agent = Agent(self.model_name)
            result = await agent.run(
                [
                    BinaryContent(data=image_bytes, media_type=mime_type),
                    IMAGE_DESCRIPTION_PROMPT,
                ]
            )
            return result.output if hasattr(result, "output") else str(result.data)
        except Exception as e:
            logger.error(f"PydanticAI image description failed: {e}")
            return ""


{%- elif cookiecutter.use_langchain or cookiecutter.use_langgraph %}


class LangChainImageDescriber(BaseImageDescriber):
    """Image description using LangChain ChatModel with vision."""

    def __init__(self, model_name: str | None = None):
        from app.core.config import settings
        self.model_name = model_name or getattr(settings, "RAG_IMAGE_DESCRIPTION_MODEL", None) or settings.AI_MODEL
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
{%- if cookiecutter.use_openai %}
            from langchain_openai import ChatOpenAI
            self._llm = ChatOpenAI(model=self.model_name)
{%- elif cookiecutter.use_anthropic %}
            from langchain_anthropic import ChatAnthropic
            self._llm = ChatAnthropic(model=self.model_name)
{%- elif cookiecutter.use_google %}
            from langchain_google_genai import ChatGoogleGenerativeAI
            self._llm = ChatGoogleGenerativeAI(model=self.model_name)
{%- endif %}
        return self._llm

    async def describe(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        try:
            from langchain_core.messages import HumanMessage

            b64 = _b64_encode(image_bytes)
            llm = self._get_llm()
            message = HumanMessage(
                content=[
                    {"type": "text", "text": IMAGE_DESCRIPTION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{b64}"},
                    },
                ]
            )
            response = await llm.ainvoke([message])
            return response.content if isinstance(response.content, str) else str(response.content)
        except Exception as e:
            logger.error(f"LangChain image description failed: {e}")
            return ""


{%- elif cookiecutter.use_crewai %}


class CrewAIImageDescriber(BaseImageDescriber):
    """Image description using CrewAI (delegates to LLM provider directly)."""

    def __init__(self, model_name: str | None = None):
        from app.core.config import settings
        self.model_name = model_name or getattr(settings, "RAG_IMAGE_DESCRIPTION_MODEL", None) or settings.AI_MODEL

    async def describe(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        try:
{%- if cookiecutter.use_openai %}
            from openai import AsyncOpenAI
            from app.core.config import settings
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            b64 = _b64_encode(image_bytes)
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": IMAGE_DESCRIPTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                ]}],
                max_tokens=500,
            )
            return response.choices[0].message.content or ""
{%- elif cookiecutter.use_anthropic %}
            from anthropic import AsyncAnthropic
            from app.core.config import settings
            client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            b64 = _b64_encode(image_bytes)
            response = await client.messages.create(
                model=self.model_name, max_tokens=500,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64}},
                    {"type": "text", "text": IMAGE_DESCRIPTION_PROMPT},
                ]}],
            )
            return response.content[0].text if response.content else ""
{%- elif cookiecutter.use_google %}
            import asyncio
            from google import genai
            from google.genai import types as genai_types
            from app.core.config import settings
            client = genai.Client(api_key=settings.GOOGLE_API_KEY)
            response = await asyncio.to_thread(
                lambda: client.models.generate_content(
                    model=self.model_name,
                    contents=[genai_types.Part.from_bytes(data=image_bytes, mime_type=mime_type), IMAGE_DESCRIPTION_PROMPT],
                )
            )
            return response.text or ""
{%- endif %}
        except Exception as e:
            logger.error(f"CrewAI image description failed: {e}")
            return ""


{%- elif cookiecutter.use_deepagents %}


class DeepAgentsImageDescriber(BaseImageDescriber):
    """Image description using DeepAgents (delegates to LLM provider directly)."""

    def __init__(self, model_name: str | None = None):
        from app.core.config import settings
        self.model_name = model_name or getattr(settings, "RAG_IMAGE_DESCRIPTION_MODEL", None) or settings.AI_MODEL

    async def describe(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        try:
{%- if cookiecutter.use_openai %}
            from openai import AsyncOpenAI
            from app.core.config import settings
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            b64 = _b64_encode(image_bytes)
            response = await client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": [
                    {"type": "text", "text": IMAGE_DESCRIPTION_PROMPT},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}"}},
                ]}],
                max_tokens=500,
            )
            return response.choices[0].message.content or ""
{%- elif cookiecutter.use_anthropic %}
            from anthropic import AsyncAnthropic
            from app.core.config import settings
            client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            b64 = _b64_encode(image_bytes)
            response = await client.messages.create(
                model=self.model_name, max_tokens=500,
                messages=[{"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": b64}},
                    {"type": "text", "text": IMAGE_DESCRIPTION_PROMPT},
                ]}],
            )
            return response.content[0].text if response.content else ""
{%- endif %}
        except Exception as e:
            logger.error(f"DeepAgents image description failed: {e}")
            return ""
{%- endif %}
{%- endif %}
