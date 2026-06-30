"""
Planner Node: LLM-powered query rewrite and access-plan creation.

The planner interprets the user's question and writes a structured access_plan
to CodeMapState. It does not own local I/O tools.
"""

from __future__ import annotations

import json
import logging
from typing import Union

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
- 질문의 성격에 따라 다음 기준에 맞게 Tool을 선택하십시오:
  * `search` : 특정 기능, 개념, 비즈니스 로직에 대한 의미론적 검색 (단순 QA)
  * `dir` : 프로젝트 전체 아키텍처, 폴더/파일 트리 구조, 모듈 구성을 파악할 때 반드시 사용 (전체 구조 파악 시 path는 "." 사용)
  * `grep` : 특정 클래스명, 함수명, 변수명이 쓰인 정확한 위치(라인)를 찾을 때 사용
  * `read` : 분석에 필수적인 핵심 파일(README.md, package.json 등)의 전체 내용을 읽을 때 사용
- [중요] 재계획(Re-plan) 시: 이전 탐색(예: search)이 실패했다면, 이전 plan/evidence와 중복되는 탐색을 피하고 반드시 다른 Tool(예: dir, grep)을 선택하여 탐색 전략을 완전히 변경하십시오.
- 사용자가 targetFile을 명시했다면, 반드시 해당 파일 경로를 대상으로 `read` 또는 `grep` 도구를 plan의 첫 번째 항목으로 포함하십시오.
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


def _content_to_text(content: Union[str, list, dict]) -> str:
    """Normalize LangChain string or multimodal list content into parseable text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for block in content:
            if isinstance(block, str):
                chunks.append(block)
            elif isinstance(block, dict) and block.get("type") in {None, "text"}:
                text = block.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        return "\n".join(chunks)
    return str(content)


def _summarize_prior_evidence(state: CodeMapState) -> list[dict]:
    """Build a compact evidence summary for re-planning without sending raw snippets."""
    summaries: list[dict] = []
    for result in state.get("worker_results", [])[:8]:
        summaries.append({
            "path": result.get("path"),
            "worker": result.get("metadata", {}).get("worker"),
            "tool": result.get("metadata", {}).get("tool"),
            "query": result.get("metadata", {}).get("query"),
        })
    return summaries


def _with_target_file_plan(
    plan: list[AccessPlanItem],
    target_file: str | None,
) -> list[AccessPlanItem]:
    """Ensure a selected file is read before broader search plans run."""
    if not target_file:
        return plan

    normalized_target = target_file.strip().replace("\\", "/")
    if not normalized_target:
        return plan

    target_read: AccessPlanItem = {
        "tool": "read",
        "path": normalized_target,
        "query": normalized_target,
        "scope": "file",
    }
    remaining = [
        item
        for item in plan
        if not (
            item.get("tool") == "read"
            and (item.get("path") or "").strip().replace("\\", "/") == normalized_target
        )
    ]
    return [target_read, *remaining][:4]


def build_planner_messages(state: CodeMapState) -> list[SystemMessage | HumanMessage]:
    """Build Planner prompt messages for both initial planning and Evaluator re-planning."""
    user_query = state["user_query"]
    replan_hint = state.get("replan_hint")
    evaluator_decision = state.get("evaluator_decision") or {}
    memory_context = state.get("memory_context") or {}
    payload = {
        "userQuestion": user_query,
        "plannerQuery": replan_hint or user_query,
        "sessionMemory": memory_context,
        "replan": bool(replan_hint),
        "replanCount": state.get("replan_count", 0),
        "targetFile": state.get("target_file"),
        "evaluatorFeedback": {
            "missingInfo": evaluator_decision.get("missingInfo", []),
            "nextPlanHint": replan_hint or evaluator_decision.get("nextPlanHint"),
            "reason": evaluator_decision.get("reason"),
        },
        "previousPlan": state.get("access_plan", []),
        "priorEvidence": _summarize_prior_evidence(state),
    }
    return [
        SystemMessage(content=_PLANNER_SYSTEM),
        HumanMessage(content=json.dumps(payload, ensure_ascii=False)),
    ]


async def planner_node(state: CodeMapState) -> dict[str, Union[str, list, dict]]:
    """
    Planner LLM node.

    Reads state["user_query"] and writes rewritten_query/access_plan.
    """
    planner_query = state.get("replan_hint") or state["user_query"]
    logger.info("[Planner] 시작 — query=%r", planner_query)

    try:
        llm = create_planner_llm()
        messages = build_planner_messages(state)
        response = await llm.ainvoke(messages)
        data = json.loads(_strip_json_fence(_content_to_text(response.content)))
    except Exception as exc:
        logger.warning("[Planner] LLM 응답 파싱 실패, 기본 plan으로 폴백: %s", exc)
        data = {
            "rewritten_query": planner_query,
            "access_plan": [
                {
                    "tool": "search",
                    "path": None,
                    "query": planner_query,
                    "scope": "chunk",
                }
            ],
        }

    raw_plan = data.get("access_plan", [])
    plan: list[AccessPlanItem] = raw_plan if isinstance(raw_plan, list) else []
    plan = _with_target_file_plan(plan, state.get("target_file"))
    logger.info("[Planner] 완료 — plan 항목 수=%d", len(plan))

    selected_workers = sorted({p.get("tool", "search") for p in plan})
    allowed_paths = sorted({str(p.get("path")) for p in plan if p.get("path")})

    return {
        "rewritten_query": data.get("rewritten_query", planner_query),
        "access_plan": plan,
        "events": [{
            "type": "planner_plan",
            "rewrittenQuery": data.get("rewritten_query", planner_query),
            "selectedWorkers": selected_workers,
            "allowedPaths": allowed_paths,
        }],
    }
