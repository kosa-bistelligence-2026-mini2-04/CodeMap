"""
Evaluator Node: deterministic evidence aggregation for Phase 1.

Phase 1 evaluates evidence by deduplicating, grouping, and compacting it into
compact_context. Phase 2 can add LLM sufficiency decisions on top of this node.
"""

from __future__ import annotations

import logging
import json
from collections import defaultdict
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.state import CodeMapState, EvaluatorDecision, WorkerResult

logger = logging.getLogger(__name__)

_TOKEN_BUDGET = 12_000

EVALUATOR_DECISION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "required": ["sufficient", "missingInfo", "nextPlanHint", "reason", "confidence"],
    "properties": {
        "sufficient": {
            "type": "boolean",
            "description": "현재 compact_context만으로 사용자 질문에 근거 기반 답변이 가능한지 여부",
        },
        "missingInfo": {
            "type": "array",
            "items": {"type": "string"},
            "description": "부족한 파일, 함수, 정책, 실행 흐름 등 추가 탐색이 필요한 정보",
        },
        "nextPlanHint": {
            "type": ["string", "null"],
            "description": "re-plan이 필요할 때 Planner가 참고할 다음 탐색 힌트",
        },
        "reason": {
            "type": "string",
            "description": "충분/부족 판단의 짧은 근거",
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "판단 신뢰도",
        },
    },
}

_EVALUATOR_SYSTEM_PROMPT = """
당신은 CodeMap Evaluator입니다.
worker_results에서 압축된 compact_context가 사용자 질문에 답하기 충분한지 판단하십시오.

반드시 아래 JSON 스키마에 맞춰 JSON만 반환하십시오.

{
  "sufficient": true,
  "missingInfo": [],
  "nextPlanHint": null,
  "reason": "충분/부족 판단 근거",
  "confidence": 0.0
}

판단 기준:
- sufficient=true: 파일 경로와 snippet 근거가 질문의 핵심에 직접 대응한다.
- sufficient=false: 근거가 없거나, 경로만 있고 질문의 핵심 동작/정책/흐름을 확인할 수 없다.
- missingInfo에는 추가로 필요한 구체 정보를 짧게 적는다.
- nextPlanHint에는 Planner가 바로 검색/읽기 계획으로 바꿀 수 있는 힌트를 적는다.
"""


def _deduplicate(results: list[WorkerResult]) -> list[WorkerResult]:
    """Remove duplicate evidence by file path and snippet prefix."""
    seen: set[tuple] = set()
    deduped: list[WorkerResult] = []
    for result in results:
        key = (result.get("path"), result.get("snippet", "")[:200])
        if key not in seen:
            seen.add(key)
            deduped.append(result)
    return deduped


def build_evaluator_messages(user_query: str, compact_context: dict[str, Any]) -> list[SystemMessage | HumanMessage]:
    """Build the LLM judge prompt for Phase 2 evidence sufficiency decisions."""
    return [
        SystemMessage(content=_EVALUATOR_SYSTEM_PROMPT),
        HumanMessage(content=json.dumps({
            "userQuery": user_query,
            "compactContext": compact_context,
            "responseSchema": EVALUATOR_DECISION_SCHEMA,
        }, ensure_ascii=False)),
    ]


def _fallback_evaluator_decision(user_query: str, compact_context: dict[str, Any]) -> EvaluatorDecision:
    """Deterministic decision used until the LLM judge is wired into the graph loop."""
    selected_count = int(compact_context.get("selectedEvidenceCount") or 0)
    grouped_by_file = compact_context.get("groupedByFile") or {}
    has_file_evidence = bool(grouped_by_file)
    if selected_count > 0 and has_file_evidence:
        return {
            "sufficient": True,
            "missingInfo": [],
            "nextPlanHint": None,
            "reason": "파일 경로와 snippet 근거가 compact_context에 포함되어 있습니다.",
            "confidence": 0.72,
        }

    return {
        "sufficient": False,
        "missingInfo": ["질문에 직접 대응하는 파일 근거 또는 코드 snippet"],
        "nextPlanHint": f"{user_query}와 관련된 파일을 search/grep/read 순서로 다시 탐색",
        "reason": "compact_context에 답변 가능한 파일 근거가 부족합니다.",
        "confidence": 0.38,
    }


def evaluator_node(state: CodeMapState) -> dict[str, Any]:
    """Build compact_context from raw worker_results."""
    raw_results: list[WorkerResult] = state.get("worker_results", [])
    logger.info("[Evaluator] 시작 — 원본 결과 수=%d", len(raw_results))

    deduped = _deduplicate(raw_results)
    grouped: dict[str, list[WorkerResult]] = defaultdict(list)
    no_path: list[WorkerResult] = []
    for result in deduped:
        if result.get("path"):
            grouped[result["path"]].append(result)
        else:
            no_path.append(result)

    grouped_by_file: dict[str, list[dict]] = defaultdict(list)
    total_chars = 0
    selected_count = 0
    budget_exceeded = False

    for file_path, items in sorted(grouped.items()):
        for item in items:
            snippet = item.get("snippet", "")
            if total_chars + len(snippet) > _TOKEN_BUDGET:
                available = _TOKEN_BUDGET - total_chars
                if available > 100:
                    snippet = snippet[:available] + "\n... (budget 초과로 잘림)"
                    budget_exceeded = True
                else:
                    budget_exceeded = True
                    break

            grouped_by_file[file_path].append({
                "id": item.get("id"),
                "lineStart": item.get("lineStart"),
                "lineEnd": item.get("lineEnd"),
                "score": item.get("score"),
                "snippet": snippet,
                "metadata": item.get("metadata", {}),
            })
            total_chars += len(snippet)
            selected_count += 1
            if budget_exceeded:
                break
        if budget_exceeded:
            break

    if no_path and not budget_exceeded:
        for item in no_path:
            snippet = item.get("snippet", "")
            if total_chars + len(snippet) > _TOKEN_BUDGET:
                available = _TOKEN_BUDGET - total_chars
                if available > 100:
                    snippet = snippet[:available] + "\n... (budget 초과로 잘림)"
                    budget_exceeded = True
                else:
                    break

            grouped_by_file["no_path"].append({
                "id": item.get("id"),
                "lineStart": item.get("lineStart"),
                "lineEnd": item.get("lineEnd"),
                "score": item.get("score"),
                "snippet": snippet,
                "metadata": item.get("metadata", {}),
            })
            total_chars += len(snippet)
            selected_count += 1
            if budget_exceeded:
                break

    compact_context = {
        "selectedEvidenceCount": selected_count,
        "tokenBudget": _TOKEN_BUDGET,
        "usedTokens": total_chars // 4,
        "groupedByFile": dict(grouped_by_file),
    }
    evaluator_decision = _fallback_evaluator_decision(state["user_query"], compact_context)
    replan_count = int(state.get("replan_count") or 0)
    max_replans = int(state.get("max_replans") or 0)
    should_replan = (not evaluator_decision["sufficient"]) and replan_count < max_replans

    # 동일 시그니처 0건 반환 시 재시도 완전 차단
    approved_plans = state.get("security_result", {}).get("approved", [])
    if should_replan and state.get("access_plan") and not approved_plans:
        logger.info("[Evaluator] 새로운 유효 탐색(승인된 plan)이 없어 재시도(replan)를 중단합니다.")
        should_replan = False
        evaluator_decision["reason"] += " (중복/0건 탐색 반복으로 중단됨)"

    compact_context["evaluatorDecision"] = evaluator_decision

    events = [{
        "type": "evidence_compacted",
        "evidenceCount": selected_count,
        "compactContextReady": True,
    }, {
        "type": "evaluator_decision",
        **evaluator_decision,
    }]
    if should_replan:
        events.append({
            "type": "replan_started",
            "missingInfo": evaluator_decision["missingInfo"],
            "nextPlanHint": evaluator_decision["nextPlanHint"],
            "iteration": replan_count + 1,
            "maxIterations": max_replans,
        })

    logger.info("[Evaluator] 완료 — 스니펫=%d chars=%d", selected_count, total_chars)
    return {
        "compact_context": compact_context,
        "evaluator_decision": evaluator_decision,
        "replan_count": replan_count + 1 if should_replan else replan_count,
        "replan_hint": evaluator_decision["nextPlanHint"] if should_replan else None,
        "events": events,
    }
