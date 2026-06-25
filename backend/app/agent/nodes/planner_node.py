"""
Planner Node: LLM-powered query rewrite and access-plan creation.

The planner interprets the user's question and writes a structured access_plan
to CodeMapState. It does not own local I/O tools.
"""

from __future__ import annotations

import json
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.llm_client import create_planner_llm
from app.agent.state import AccessPlanItem, CodeMapState

logger = logging.getLogger(__name__)

_PLANNER_SYSTEM = """
당신은 코드베이스 탐색 전문 Planner입니다.
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


def _strip_json_fence(raw: str) -> str:
    """Remove a simple ```json fenced block if the model returned one."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


async def planner_node(state: CodeMapState) -> dict:
    """
    Planner LLM node.

    Reads state["user_query"] and writes rewritten_query/access_plan.
    """
    logger.info("[Planner] 시작 — query=%r", state["user_query"])

    llm = create_planner_llm()
    messages = [
        SystemMessage(content=_PLANNER_SYSTEM),
        HumanMessage(content=f"사용자 질문: {state['user_query']}"),
    ]

    try:
        response = await llm.ainvoke(messages)
        data = json.loads(_strip_json_fence(str(response.content)))
    except Exception as exc:
        logger.warning("[Planner] LLM 응답 파싱 실패, 기본 plan으로 폴백: %s", exc)
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
    logger.info("[Planner] 완료 — plan 항목 수=%d", len(plan))

    selected_workers = sorted({p.get("tool", "search") for p in plan})
    allowed_paths = sorted({p.get("path") for p in plan if p.get("path")})

    return {
        "rewritten_query": data.get("rewritten_query", state["user_query"]),
        "access_plan": plan,
        "events": [{
            "type": "planner_plan",
            "rewrittenQuery": data.get("rewritten_query", state["user_query"]),
            "selectedWorkers": selected_workers,
            "allowedPaths": allowed_paths,
        }],
    }

