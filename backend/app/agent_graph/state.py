"""
CodeMapState: LangGraph 전체 워크플로우에서 에이전트 간에 공유되는 상태 스키마.

- 모든 노드는 이 State를 읽고 씁니다.
- 중간 요약 없이 원본 데이터를 worker_results에 직접 누적합니다.
  (정보 유실 방지, Final Answer Agent가 원본 근거를 직접 참조)
"""

from __future__ import annotations

from typing import Annotated, TypedDict
import operator


class WorkerResult(TypedDict):
    """단일 Worker가 수집한 원본 결과."""
    worker: str          # "search" | "dir" | "grep" | "read"
    tool: str            # 실행한 도구명
    query: str           # 사용한 검색/탐색 쿼리
    content: str         # 도구 실행 결과 (raw, 요약 없음)
    file_path: str | None  # 해당 파일 경로 (있는 경우)


class AccessPlanItem(TypedDict):
    """Supervisor가 수립한 단일 도구 사용 계획."""
    tool: str            # "search" | "dir" | "grep" | "read"
    path: str | None     # 대상 경로 (dir/grep/read 전용)
    query: str           # 검색 쿼리 또는 grep 패턴
    scope: str           # "chunk" | "file" | "directory"


class SecurityResult(TypedDict):
    """Route Node의 보안 검증 결과."""
    approved: list[AccessPlanItem]   # 승인된 계획
    rejected: list[AccessPlanItem]   # 거부된 계획 (path traversal 등)


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

    # ── Supervisor 출력 ────────────────────────────────
    rewritten_query: str              # 오타 교정 및 의도 분석된 검색 쿼리
    access_plan: list[AccessPlanItem] # Supervisor가 수립한 도구 사용 계획

    # ── Route Node 출력 ───────────────────────────────
    security_result: SecurityResult   # 보안 검증 결과 (allowlist 통과 여부)

    # ── Worker 출력 (fan-in: 병렬 병합) ───────────────
    worker_results: Annotated[list[WorkerResult], operator.add]

    # ── Evidence Aggregator 출력 ──────────────────────
    compact_context: dict             # token budget 내로 압축된 근거 묶음

    # ── 최종 출력 ─────────────────────────────────────
    final_answer: str | None          # Final Answer Agent가 생성한 최종 응답
