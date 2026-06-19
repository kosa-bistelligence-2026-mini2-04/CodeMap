"""Repository-grounded conversational service."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID


from sqlalchemy.ext.asyncio import AsyncSession
import asyncio

from app.chat.repository import ChatRepository
from app.chat.schemas import ChatRequest
from app.core.config import get_settings
from app.repo.analyzer import search_repository
from app.repo.repository import AnalysisJobRepository


class RepositoryChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_repository = ChatRepository(db)
        self.job_repository = AnalysisJobRepository(db)
        self.settings = get_settings()

    async def prepare(self, repo_id: UUID, request: ChatRequest):
        job = await self.job_repository.get_job_by_id(repo_id)
        if not job:
            raise ValueError("분석 프로젝트를 찾을 수 없습니다.")
        clone_path = Path(self.settings.CLONE_BASE_DIR) / str(repo_id) / "repo"
        if not clone_path.exists():
            raise ValueError("저장소 스냅샷이 아직 준비되지 않았습니다.")

        thread = await self.chat_repository.get_or_create_thread(
            repo_id,
            request.threadId,
            request.message.strip().replace("\n", " ")[:72],
        )
        mode = "quick" if request.mode == "fast" else request.mode
        await self.chat_repository.add_message(thread, "user", request.message, mode)
        await self.db.commit()
        references = await self._search(clone_path, request, mode)
        return job, thread, mode, references

    async def _search(self, clone_path: Path, request: ChatRequest, mode: str) -> list[dict]:
        query = request.message
        if request.contextFile:
            query = f"{request.contextFile} {query}"
        return await asyncio.to_thread(
            search_repository,
            str(clone_path),
            query,
            10 if mode == "deep" else 5,
        )

    async def answer(self, repo_name: str, request: ChatRequest, references: list[dict], mode: str = "quick") -> str:
        if not references:
            return (
                f"`{repo_name}` 저장소에서 질문과 직접 연결되는 코드 근거를 찾지 못했습니다. "
                "파일명, 함수명 또는 기능 흐름을 조금 더 구체적으로 알려주시면 실제 소스에서 다시 탐색하겠습니다."
            )

        if self.settings.OPENAI_API_KEY.get_secret_value():
            from langchain_openai import ChatOpenAI

            # mode에 따라 실제 모델 분기 적용
            model_name = "gpt-4o" if mode == "deep" else self.settings.OPENAI_MODEL

            context = "\n\n".join(
                f"[{item['file']}:{item['line']}]\n{item['snippet']}" for item in references
            )
            llm = ChatOpenAI(
                model=model_name,
                api_key=self.settings.OPENAI_API_KEY,
                temperature=0.1,
            )
            response = await llm.ainvoke([
                ("system", (
                    "당신은 CodeMap 저장소 분석 도우미입니다. 제공된 실제 코드 근거만 사용하세요. "
                    "추측은 추측이라고 밝히고, 중요한 주장에는 [파일:라인] 형식의 출처를 붙이세요."
                )),
                ("user", f"저장소: {repo_name}\n질문: {request.message}\n\n코드 근거:\n{context}"),
            ])
            return str(response.content)

        bullets = "\n".join(
            f"- `{item['file']}:{item['line']}` — 질문 키워드와 연결되는 코드가 확인됩니다."
            for item in references[:5]
        )
        return (
            f"`{repo_name}`의 실제 저장소 스냅샷에서 관련 파일을 찾았습니다.\n\n{bullets}\n\n"
            "현재 서버에는 생성형 모델 키가 설정되지 않아 코드 근거 목록까지만 제공합니다. "
            "서버에 `OPENAI_API_KEY`를 설정하면 같은 근거를 사용해 상세 설명을 생성합니다."
        )

    async def persist_answer(self, thread, answer: str, mode: str, references: list[dict]) -> None:
        await self.chat_repository.add_message(thread, "assistant", answer, mode, references)
        await self.db.commit()
