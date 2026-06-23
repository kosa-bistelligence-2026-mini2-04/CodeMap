from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import ChatMessage, Conversation
from app.chat.schemas import ChatContextResult
from app.embed.models import CodeNode


class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_thread(self, repo_id: UUID, thread_id: UUID | None, title: str) -> Conversation:
        if thread_id:
            result = await self.db.execute(select(Conversation).where(
                Conversation.id == thread_id,
                Conversation.repo_id == repo_id,
            ))
            thread = result.scalar_one_or_none()
            if thread:
                return thread
        thread = Conversation(repo_id=repo_id, title=title[:160] or "새 대화")
        self.db.add(thread)
        await self.db.flush()
        await self.db.refresh(thread)
        return thread

    async def add_message(
        self,
        thread: Conversation,
        role: str,
        content: str,
        mode: str,
        references: list[dict] | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            conversation_id=thread.id,
            role=role,
            content=content,
            mode=mode,
            references=references or [],
        )
        thread.updated_at = datetime.now(timezone.utc)
        self.db.add(message)
        await self.db.flush()
        return message

    async def list_threads(self, repo_id: UUID) -> list[Conversation]:
        result = await self.db.execute(
            select(Conversation).where(Conversation.repo_id == repo_id).order_by(Conversation.updated_at.desc()).limit(30)
        )
        return list(result.scalars())

    async def list_messages(self, repo_id: UUID, thread_id: UUID) -> list[ChatMessage]:
        thread_result = await self.db.execute(select(Conversation.id).where(
            Conversation.id == thread_id,
            Conversation.repo_id == repo_id,
        ))
        if thread_result.scalar_one_or_none() is None:
            return []
        result = await self.db.execute(
            select(ChatMessage).where(ChatMessage.conversation_id == thread_id).order_by(ChatMessage.created_at.asc())
        )
        return list(result.scalars())

    # ──────────────────────────────────────────────
    # AGENT-CHAT-API-002: 코드 컨텍스트 벡터 검색
    # code_nodes 청크 조회
    # ──────────────────────────────────────────────
    async def search_context_chunks(
        self,
        repo_id: UUID,
        query_embedding: list[float],
        top_k: int,
        threshold: float,
    ) -> list[ChatContextResult]:
        """
        질문 임베딩과 유사한 코드 청크를 pgvector 코사인 거리로 조회합니다.

        저장된 CodeNode 청크 중 job_id가 일치하고 임베딩이 존재하는 데이터만 대상으로
        유사도 기준을 넘는 결과를 가까운 순서대로 반환합니다.
        """
        distance = CodeNode.embedding.cosine_distance(query_embedding)
        similarity = (1 - distance).label("similarity")

        result = await self.db.execute(
            select(CodeNode, similarity)
            .where(
                CodeNode.job_id == repo_id,
                CodeNode.type == "CHUNK",
                CodeNode.embedding.is_not(None),
                (1 - distance) >= threshold,
            )
            .order_by(distance.asc())
            .limit(top_k)
        )

        return [
            self._to_context_result(node, float(score or 0.0))
            for node, score in result.all()
        ]

    def _to_context_result(self, node: CodeNode, similarity: float) -> ChatContextResult:
        """
        CodeNode 엔티티를 코드 컨텍스트 검색 응답 DTO로 변환합니다.

        파싱 단계에서 저장된 메타데이터의 라인 정보를 읽어
        API 명세의 filePath, startLine, endLine 형식에 맞춥니다.
        """
        metadata = node.file_metadata or {}
        start_line = self._metadata_int(metadata, "start_line", "startLine", default=1)
        end_line = self._metadata_int(metadata, "end_line", "endLine", default=start_line)
        language = node.language or metadata.get("language")

        return ChatContextResult(
            filePath=node.path,
            startLine=start_line,
            endLine=end_line,
            content=node.content or "",
            similarity=round(similarity, 4),
            language=language,
        )

    def _metadata_int(self, metadata: dict, snake_key: str, camel_key: str, default: int) -> int:
        """
        메타데이터의 라인 값을 정수로 안전하게 변환합니다.

        저장 형식이 snake_case 또는 camelCase 중 어느 쪽이어도
        동일하게 읽을 수 있도록 보정합니다.
        """
        value = metadata.get(snake_key, metadata.get(camel_key, default))
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
