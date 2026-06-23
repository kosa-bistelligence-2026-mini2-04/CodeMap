from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# AGENT-CHAT-API-001: Repo Chat 요청 DTO
# POST /api/chat/{repo_id}
# ──────────────────────────────────────────────
class ChatRequest(BaseModel):
    """
    Repo Chat SSE 요청 DTO입니다.

    현재 구현은 기존 채팅 화면 연동을 위해 message, mode, threadId, contextFile을 사용합니다.
    """

    message: str = Field(min_length=1, max_length=8000)
    mode: Literal["quick", "deep", "fast"] = "quick"
    threadId: UUID | None = None
    contextFile: str | None = Field(default=None, max_length=1000)


# ──────────────────────────────────────────────
# AGENT-CHAT-API-002: 코드 컨텍스트 검색 DTO
# POST /api/chat/{repo_id}/context
# ──────────────────────────────────────────────
class ChatContextRequest(BaseModel):
    """
    코드 컨텍스트 검색 요청 DTO입니다.

    자연어 질문과 검색 개수, 최소 유사도 기준을 받아
    임베딩 기반 코드 청크 검색 조건으로 사용합니다.
    """

    question: str = Field(min_length=1, max_length=8000, description="코드 컨텍스트를 검색할 자연어 질문")
    topK: int = Field(default=5, ge=1, le=20, description="반환할 최대 코드 청크 수")
    threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="검색 결과로 인정할 최소 유사도")


class ChatContextResult(BaseModel):
    """
    검색된 코드 청크 단위 응답 DTO입니다.

    파일 경로, 라인 범위, 코드 본문, 유사도, 언어 정보를
    클라이언트가 바로 컨텍스트로 사용할 수 있는 형태로 반환합니다.
    """

    filePath: str = Field(description="검색된 코드 파일 경로")
    startLine: int = Field(description="코드 청크 시작 라인")
    endLine: int = Field(description="코드 청크 종료 라인")
    content: str = Field(description="코드 청크 본문")
    similarity: float = Field(description="질문과 코드 청크의 코사인 유사도")
    language: str | None = Field(default=None, description="코드 언어")


class ChatContextData(BaseModel):
    """
    코드 컨텍스트 검색 성공 응답의 data DTO입니다.

    원본 질문과 해당 질문에 대해 검색된 코드 청크 목록을 담습니다.
    """

    question: str
    results: list[ChatContextResult]


class ChatContextResponse(BaseModel):
    """
    코드 컨텍스트 검색 성공 응답 DTO입니다.

    공통 성공 응답 형식인 code, message, data 구조를 따릅니다.
    """

    code: int = Field(default=200, description="HTTP 상태 코드")
    message: str = Field(default="success", description="처리 결과 메시지")
    data: ChatContextData


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
