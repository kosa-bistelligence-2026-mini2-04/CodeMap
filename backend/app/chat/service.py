"""저장소 기반 채팅 서비스 모듈입니다."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repository import ChatRepository
from app.chat.schemas import (
    ChatContextData,
    ChatContextRequest,
    ChatContextResponse,
    ChatRequest,
)
from app.core.config import get_settings
from app.core.exceptions import CodeMapException
from app.repo.analyzer import search_repository
from app.repo.repository import AnalysisJobRepository

logger = logging.getLogger(__name__)


class RepositoryChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_repository = ChatRepository(db)
        self.job_repository = AnalysisJobRepository(db)
        self.settings = get_settings()

    # ──────────────────────────────────────────────
    # AGENT-CHAT-API-001: Repo Chat SSE 준비
    # POST /api/chat/{repo_id}
    # ──────────────────────────────────────────────
    async def prepare(self, repo_id: UUID, request: ChatRequest):
        """
        Repo Chat 스트리밍 답변 생성을 위한 사전 데이터를 준비합니다.

        분석 작업과 저장소 스냅샷을 확인하고, 대화 스레드 및 사용자 메시지를 저장한 뒤
        답변 생성에 사용할 코드 참조 목록을 조회합니다.
        """
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
        """
        저장소 스냅샷에서 질문과 관련된 코드 참조를 검색합니다.

        기존 Repo Chat API는 로컬 저장소 검색기를 사용하며,
        deep 모드에서는 더 많은 후보 파일을 조회합니다.
        """
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
        """
        검색된 코드 참조를 기반으로 Repo Chat 답변을 생성합니다.

        OpenAI API 키가 설정되어 있으면 LLM 답변을 생성하고,
        설정되어 있지 않으면 검색된 코드 근거 목록 중심의 안내 문구를 반환합니다.
        """
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
        """
        Repo Chat에서 생성된 assistant 답변을 대화 이력에 저장합니다.

        사용자 메시지와 같은 스레드에 답변, 모드, 참조 정보를 함께 기록합니다.
        """
        await self.chat_repository.add_message(thread, "assistant", answer, mode, references)
        await self.db.commit()

    # ──────────────────────────────────────────────
    # AGENT-CHAT-API-002: 코드 컨텍스트 검색
    # POST /api/chat/{repo_id}/context
    # ──────────────────────────────────────────────
    async def get_context(self, repo_id: UUID, request: ChatContextRequest) -> ChatContextResponse:
        """
        질문 기반 코드 컨텍스트 검색 결과를 반환합니다.

        분석 작업 존재 여부를 확인한 뒤 질문을 임베딩으로 변환하고,
        저장된 코드 청크 중 유사도 기준을 만족하는 컨텍스트를 조회합니다.
        """
        job = await self.job_repository.get_job_by_id(repo_id)
        if not job:
            raise CodeMapException(404, "REPO_NOT_FOUND", "저장소를 찾을 수 없습니다.")

        try:
            query_embedding = await self._embed_question(request.question)
            results = await self.chat_repository.search_context_chunks(
                repo_id=repo_id,
                query_embedding=query_embedding,
                top_k=request.topK,
                threshold=request.threshold,
            )
        except CodeMapException:
            raise
        except Exception as exc:
            logger.exception("[채팅 컨텍스트 검색] 벡터 검색 실패: %s", exc)
            raise CodeMapException(500, "VECTOR_SEARCH_FAILED", "코드 컨텍스트 검색 중 오류가 발생했습니다.") from exc

        return ChatContextResponse(
            data=ChatContextData(
                question=request.question,
                results=results,
            )
        )

    async def _embed_question(self, question: str) -> list[float]:
        """
        자연어 질문을 코드 청크 검색용 임베딩 벡터로 변환합니다.

        AGENT-CHAT-API-002는 저장된 코드 임베딩과 같은 모델 차원을 사용해야 하므로
        공통 설정의 임베딩 모델과 차원 값을 그대로 사용합니다.
        """
        api_key = self.settings.OPENAI_API_KEY.get_secret_value()
        if not api_key:
            raise CodeMapException(500, "VECTOR_SEARCH_FAILED", "임베딩 API 키가 설정되지 않았습니다.")

        from langchain_openai import OpenAIEmbeddings

        embedder = OpenAIEmbeddings(
            model=self.settings.EMBEDDING_MODEL,
            dimensions=self.settings.EMBEDDING_DIMENSIONS,
            api_key=api_key,
        )
        return await embedder.aembed_query(question)
