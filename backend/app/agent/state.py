"""
CodeMapState: LangGraph 전체 워크플로우에서 에이전트 간에 공유되는 상태 스키마.

- 모든 노드는 이 State를 읽고 씁니다.
- 중간 요약 없이 원본 데이터를 worker_results에 직접 누적합니다.
  (정보 유실 방지, Final Answer Agent가 원본 근거를 직접 참조)
"""

from __future__ import annotations

from typing import Annotated, TypedDict, Any
import operator


class WorkerResult(TypedDict):
    """단일 Worker가 수집한 원본 결과 (명세 반영)."""
    id: str              # e.g., "ev_001"
    path: str | None     # 파일 경로
    lineStart: int | None # 시작 줄
    lineEnd: int | None   # 끝 줄
    score: float | None   # 검색 스코어 등
    snippet: str         # 코드 스니펫
    metadata: dict[str, Any]       # worker, tool, query 등 부가 정보


class AccessPlanItem(TypedDict):
    """Planner Node가 수립한 단일 도구 사용 계획."""
    tool: str            # "search" | "dir" | "grep" | "read"
    path: str | None     # 대상 경로 (dir/grep/read 전용)
    query: str           # 검색 쿼리 또는 grep 패턴
    scope: str           # "chunk" | "file" | "directory"


class SecurityResult(TypedDict):
    """Dispatcher Node의 보안 검증 결과."""
    approved: list[AccessPlanItem]   # 승인된 계획
    rejected: list[AccessPlanItem]   # 거부된 계획 (path traversal 등)


class EvaluatorDecision(TypedDict):
    """Evaluator Node의 근거 충분성 판단 결과."""
    sufficient: bool
    missingInfo: list[str]
    nextPlanHint: str | None
    reason: str
    confidence: float


class CodeMapState(TypedDict):
    """
    LangGraph 공유 상태 (메모리).

    worker_results는 Annotated[list, operator.add]로 선언하여
    병렬 Worker들이 Send API로 결과를 자동 병합(fan-in)합니다.
    """
    # ── 입력 ──────────────────────────────────────────
    user_query: str                   # 사용자 원본 질문
    repo_id: str                      # 분석 대상 저장소 ID
    clone_path: str                   # 로컬 clone 경로
    run_id: str                       # Agent Run ID
    session_id: str | None            # Chat session / LangGraph thread_id 매핑값
    memory_context: dict[str, Any]              # DB에서 복원한 최근 대화 맥락

    # ── Planner Node 출력 ──────────────────────────────
    rewritten_query: str              # 오타 교정 및 의도 분석된 검색 쿼리
    access_plan: list[AccessPlanItem] # Planner Node가 수립한 도구 사용 계획

    # ── Dispatcher Node 출력 ─────────────────────────
    security_result: SecurityResult   # 보안 검증 결과 (allowlist 통과 여부)

    # ── Worker 출력 (fan-in: 병렬 병합) ───────────────
    worker_results: Annotated[list[WorkerResult], operator.add]
    events: Annotated[list[dict[str, Any]], operator.add]  # SSE 스트리밍을 위한 발생 이벤트 목록
    errors: list[str]                 # 발생한 에러 메시지 목록
    durations: dict[str, float]                   # 각 단계별 소요 시간

    # ── Evaluator 출력 ───────────────────────────────
    compact_context: dict[str, Any]             # token budget 내로 압축된 근거 묶음
    evaluator_decision: EvaluatorDecision | None
    replan_count: int                 # Evaluator re-plan 반복 횟수
    max_replans: int                  # re-plan 최대 반복 횟수
    replan_hint: str | None           # Planner가 다음 탐색에 사용할 힌트

    # ── 최종 출력 ─────────────────────────────────────
    final_answer: str | None          # Final Answer Agent가 생성한 최종 응답

    # ── 내부 상태 ─────────────────────────────────────
    _plan_item: AccessPlanItem | None # Send API로 워커에 전달되는 개별 계획 (fan-out용)
