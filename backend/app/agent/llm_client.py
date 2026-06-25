"""
LLM provider/factory helpers for agent nodes.

This module owns model construction only. Planner/Evaluator behavior stays in
LangGraph nodes so provider wiring does not absorb workflow responsibilities.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from app.infra.config import get_settings


def create_planner_llm() -> ChatOpenAI:
    """Create the deterministic planner model used for access planning."""
    settings = get_settings()
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY.get_secret_value(),
        temperature=0,
    )


def create_evaluator_llm() -> ChatOpenAI:
    """Create the deterministic evaluator judge model used for evidence sufficiency."""
    settings = get_settings()
    return ChatOpenAI(
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY.get_secret_value(),
        temperature=0,
    )


def create_final_answer_llm(*, mode: str = "quick", streaming: bool = True) -> ChatOpenAI:
    """Create the final-answer model used by the chat application layer."""
    settings = get_settings()
    model_name = "gpt-4o" if mode == "deep" else settings.OPENAI_MODEL
    return ChatOpenAI(
        model=model_name,
        api_key=settings.OPENAI_API_KEY.get_secret_value(),
        temperature=0.1,
        streaming=streaming,
    )
