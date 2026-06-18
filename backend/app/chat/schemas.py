from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    mode: Literal["quick", "deep", "fast"] = "quick"
    threadId: UUID | None = None
    contextFile: str | None = Field(default=None, max_length=1000)


class ThreadSummary(BaseModel):
    id: UUID
    repoId: UUID
    title: str
    createdAt: str
    updatedAt: str


class StoredMessage(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    mode: str
    references: list[dict]
    createdAt: str
