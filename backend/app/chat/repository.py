from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import ChatMessage, Conversation


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
