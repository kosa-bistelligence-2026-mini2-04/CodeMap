"""
문서 생성 파이프라인 LangGraph 공유 상태 정의

DOCS-GEN 모듈의 내부 파이프라인(순서 1~6)이 공유하는 상태를 정의한다.
B-205 → B-201 → B-203 → B-206 → B-202 → B-204 순서로 실행된다.
"""

from typing import Any, Optional
from typing_extensions import TypedDict


# ──────────────────────────────────────────────
# GenFormState: 문서 생성 파이프라인 공유 상태
# ──────────────────────────────────────────────
class GenFormState(TypedDict):
    '''
    DOCS-GEN 내부 파이프라인 전 구간에 걸쳐 공유되는 상태

    입력 필드(파이프라인 시작 전 설정):
      repo_id       — 분석 대상 저장소 ID
      clone_path    — 로컬 클론 경로 (RAG 파이프라인 완료 후 설정)
      analysis_report — Parse/Embed 파이프라인 결과 (repo 분석 리포트)

    중간 결과 필드(각 노드가 채움):
      project_intro   — B-205: README 기반 프로젝트 소개 텍스트
      doc_summary     — B-201: 문서 요약 결과 (purpose, key_features, tech_context)
      folder_summaries — B-203: 폴더별 요약 맵 (path → summary)
      flow_explanation — B-206: 핵심 실행 플로우 설명 텍스트
      onboarding_guide — B-202: 온보딩 가이드 (reading_order, risk_files, first_tasks)
      master_report   — B-204: 최종 마스터 리포트 통합 결과

    파이프라인 제어 필드:
      status  — 파이프라인 현재 상태 (running / completed / failed)
      error   — 실패 시 오류 메시지
      timings — 단계별 소요시간 (초, perf_counter 기준)
    '''

    ## 입력 필드
    repo_id: str
    clone_path: Optional[str]
    analysis_report: Optional[dict[str, Any]]
    llm_model: Optional[str]

    ## 중간 결과 필드
    project_intro: Optional[str]
    doc_summary: Optional[dict[str, Any]]
    folder_summaries: Optional[dict[str, str]]
    flow_explanation: Optional[str]
    onboarding_guide: Optional[dict[str, Any]]
    master_report: Optional[dict[str, Any]]

    ## 파이프라인 제어 필드
    status: str
    error: Optional[str]
    timings: dict[str, float]
