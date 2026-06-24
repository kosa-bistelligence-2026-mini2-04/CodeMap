from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRunRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8000)
    sessionId: UUID | None = None
    mode: Literal["lite", "standard", "deep"] = "standard"
    includeEvidence: bool = True
    maxToolCalls: int = Field(default=8, ge=1, le=20)
    timeoutSeconds: int = Field(default=30, ge=5, le=120)


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
