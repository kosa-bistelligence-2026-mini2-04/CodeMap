"""
Supervisor Agent: 사용자 의도 분석 및 access_plan 수립.

- LLM 기반 에이전트 (오타 교정, 쿼리 재작성, 도구 사용 계획 생성)
- 로컬 I/O 도구는 보유하지 않음 (보안 원칙)
- 출력: rewritten_query + access_plan → State에 저장
"""

from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agent_graph.state import AccessPlanItem, CodeMapState

logger = logging.getLogger(__name__)

_SUPERVISOR_SYSTEM = """
당신은 코드베이스 탐색 전문 Supervisor입니다.
사용자의 질문을 분석하여 아래 JSON 형식으로 응답하십시오.

{
  "rewritten_query": "오타 교정 및 의도를 명확히 한 검색 쿼리",
  "access_plan": [
    {
      "tool": "search|dir|grep|read",
      "path": "탐색 경로 (dir/grep/read 전용, search는 null)",
      "query": "검색 쿼리 또는 grep 패턴",
      "scope": "chunk|file|directory"
    }
  ]
}

규칙:
- 최대 4개의 plan 항목을 수립하십시오.
- path는 반드시 저장소 내 상대 경로만 허용합니다 (절대 경로 및 ../ 금지).
- 답변은 반드시 JSON만 출력하십시오.
"""


async def supervisor_node(state: CodeMapState) -> dict:
    """
    Supervisor Agent 노드.

    state["user_query"]를 읽어 rewritten_query와 access_plan을 생성합니다.
    """
    logger.info("[Supervisor] 시작 — query=%r", state["user_query"])

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    messages = [
        SystemMessage(content=_SUPERVISOR_SYSTEM),
        HumanMessage(content=f"사용자 질문: {state['user_query']}"),
    ]

    try:
        response = await llm.ainvoke(messages)
        raw = response.content.strip()
        # JSON 코드 블록이 있으면 제거
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)
    except Exception as exc:
        logger.warning("[Supervisor] LLM 응답 파싱 실패, 기본 plan으로 폴백: %s", exc)
        data = {
            "rewritten_query": state["user_query"],
            "access_plan": [
                {
                    "tool": "search",
                    "path": None,
                    "query": state["user_query"],
                    "scope": "chunk",
                }
            ],
        }

    plan: list[AccessPlanItem] = data.get("access_plan", [])
    logger.info("[Supervisor] 완료 — plan 항목 수=%d", len(plan))

    return {
        "rewritten_query": data.get("rewritten_query", state["user_query"]),
        "access_plan": plan,
    }
