"""
DOCS-GEN 가이드북 생성 백그라운드 작업 (DOCS-GEN-API-002)

FastAPI BackgroundTasks를 통해 호출되며, GenFormSupervisor 파이프라인을
비동기로 실행한 뒤 결과를 Markdown으로 변환하여 DB에 저장한다.

진행 중인 repo_id를 인메모리 set으로 추적하여
중복 실행을 방지한다.
"""

import asyncio
import logging
from uuid import UUID

from app.infra.database import async_session_factory

logger = logging.getLogger(__name__)

## 가이드북 생성이 현재 진행 중인 repo_id 집합 (인메모리, 단일 프로세스 기준)
_DOCS_GENERATION_IN_PROGRESS: set[str] = set()


# ──────────────────────────────────────────────
# 진행 상태 조회/등록/해제 유틸리티
# ──────────────────────────────────────────────
def is_generation_in_progress(repo_id: UUID) -> bool:
    '''해당 저장소의 가이드북 생성이 현재 진행 중인지 반환한다.'''
    return str(repo_id) in _DOCS_GENERATION_IN_PROGRESS


def _mark_in_progress(repo_id: UUID) -> None:
    _DOCS_GENERATION_IN_PROGRESS.add(str(repo_id))


def _mark_done(repo_id: UUID) -> None:
    _DOCS_GENERATION_IN_PROGRESS.discard(str(repo_id))


# ──────────────────────────────────────────────────────────────
# 가이드북 생성 백그라운드 작업
# ──────────────────────────────────────────────────────────────
async def run_doc_generation(
    repo_id: UUID,
    job_id: UUID,
    analysis_report: dict,
    repo_name: str,
    version: int,
    clone_path: str | None,
    model: str = "gpt-4o-mini",
) -> None:
    '''
    GenFormSupervisor 파이프라인을 실행하고 결과를 DB에 저장하는 백그라운드 코루틴.

    FastAPI BackgroundTasks.add_task(run_doc_generation, ...) 형태로 호출된다.
    진행 중 마킹(_mark_in_progress)은 호출자(validate_and_queue_doc_generation)가
    큐잉 시점에 동기적으로 처리하므로, 이 함수에서는 마킹 해제만 담당한다.

    실행 순서:
      1. GenFormSupervisor 파이프라인 실행
      2. master_report → Markdown 변환 (asyncio.to_thread 격리)
      3. save_onboarding_doc으로 DB 저장
      4. 완료(또는 실패) 후 마킹 해제

    Args:
        repo_id:         대상 저장소 ID
        job_id:          연결된 분석 작업 ID (AnalysisJob.id)
        analysis_report: AnalysisJob.report_json 분석 결과 dict
        repo_name:       저장소 이름 (Markdown 제목용)
        version:         저장할 가이드북 버전 번호
        clone_path:      로컬 클론 경로 (없으면 None → 폴백 처리)
        model:           LLM 모델 식별자 (파이프라인 노드에 전달)
    '''
    try:
        ## 1. GenFormSupervisor 빌드 및 실행
        from app.gen.form.graph import GenFormSupervisor
        from app.gen.form.state import GenFormState

        supervisor = GenFormSupervisor()
        supervisor.build_workflow()

        initial_state: GenFormState = {
            "repo_id": str(repo_id),
            "clone_path": clone_path,
            "analysis_report": analysis_report,
            "llm_model": model,
            "project_intro": None,
            "doc_summary": None,
            "folder_summaries": None,
            "flow_explanation": None,
            "onboarding_guide": None,
            "master_report": None,
            "status": "pending",
            "error": None,
            "timings": {},
        }

        result_state = await supervisor.run(initial_state)

        if result_state.get("status") == "failed":
            logger.error(
                "[DOCS-GEN-BG] 파이프라인 실패 | repo_id=%s error=%s",
                repo_id,
                result_state.get("error"),
            )
            return

        ## 2. master_report → Markdown 변환 (동기 함수를 별도 스레드로 격리)
        from app.gen.markdown import master_report_to_markdown

        master_report = result_state.get("master_report") or {}
        markdown_content = await asyncio.to_thread(
            master_report_to_markdown, master_report, repo_name
        )

        ## 3. DB 저장
        from app.gen.service import save_onboarding_doc

        async with async_session_factory() as db:
            await save_onboarding_doc(
                db=db,
                repo_id=repo_id,
                job_id=job_id,
                content=markdown_content,
                version=version,
                report_json=master_report if master_report else None,
            )

        logger.info(
            "[DOCS-GEN-BG] 완료 | repo_id=%s version=%d", repo_id, version
        )

    except Exception as exc:
        logger.exception(
            "[DOCS-GEN-BG] 예외 발생 | repo_id=%s: %s", repo_id, exc
        )
    finally:
        _mark_done(repo_id)
