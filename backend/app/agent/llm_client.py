"""
OpenAI API 호출 및 에이전트 프롬프트 캡슐화를 전담하는 LLM 클라이언트.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator

from langchain_openai import ChatOpenAI

from app.infra.config import get_settings

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# CodeMap LLM 클라이언트 클래스
# ──────────────────────────────────────────────
class CodeMapLLMClient:
    '''
    OpenAI 모델 호출을 전담하여 API 키 설정 및 예외 안전성을 보장합니다.
    '''

    def __init__(self, mode: str = "quick"):
        ## settings 로드
        self.settings = get_settings()
        self.mode = mode
        self.model_name = (
            "gpt-4o" if mode == "deep" else self.settings.OPENAI_MODEL
        )
        self.client = self._init_client()

    # ──────────────────────────────────────────────
    # ChatOpenAI 클라이언트 초기화 메서드
    # ──────────────────────────────────────────────
    def _init_client(self) -> ChatOpenAI:
        '''
        LangChain의 ChatOpenAI 인스턴스를 생성하여 반환합니다.
        '''
        api_key = self.settings.OPENAI_API_KEY.get_secret_value()
        return ChatOpenAI(
            model=self.model_name,
            api_key=api_key,
            temperature=0.1,
            streaming=True,
        )

    # ──────────────────────────────────────────────
    # 메시지 스트리밍 메서드
    # ──────────────────────────────────────────────
    async def astream_messages(self, messages: list) -> AsyncIterator[dict]:
        '''
        주어진 메시지 목록을 바탕으로 스트리밍 응답을 생성합니다.
        '''
        async for chunk in self.client.astream(messages):
            yield chunk
