"""
DOCS-GEN 서비스 계층 (DOCS-GEN-B-301, DOCS-GEN-API-001, 002)

- save_onboarding_doc: 생성된 Markdown을 DB에 저장 (B-301)
- get_onboarding_doc: 저장된 가이드북 조회 (API-001)
- validate_and_queue_doc_generation: 가이드북 생성 사전 검증 (API-002)
"""

import logging
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import (
    AnalysisNotCompletedError,
    DatabaseSaveFailedError,
    DocsAlreadyExistsError,
    DocsGenerationInProgressError,
    DocsNotFoundError,
    RepoNotFoundError,
)
from app.gen.models import OnboardingDoc
from app.gen.repository import GenDocRepository
from app.gen.schemas import DocGetJsonData, DocGetMarkdownData
from app.infra.config import get_settings
from app.repo.schemas import JobStatus

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# DOCS-GEN-B-301: Markdown DB 저장
# ──────────────────────────────────────────────────────────────
async def save_onboarding_doc(
    db: AsyncSession,
    repo_id: UUID,
    job_id: UUID,
    content: str,
    version: int,
    report_json: dict | None = None,
) -> OnboardingDoc:
    '''
    온보딩 가이드북 Markdown을 PostgreSQL docs 테이블에 저장한다.

    DOCS-GEN-B-301 구현:
      1. repo_id 존재 여부 확인 (없으면 404 RepoNotFoundError)
      2. OnboardingDoc 레코드 저장
      3. commit 후 저장된 엔티티 반환

    Args:
        db:          AsyncSession (외부 주입)
        repo_id:     대상 저장소 ID (analysis_jobs.id)
        job_id:      문서 생성을 트리거한 분석 작업 ID
        content:     저장할 Markdown 가이드북 전문
        version:     가이드북 버전 번호
        report_json: master_report JSON 원본 (format=json 조회용, 선택)

    Returns:
        저장된 OnboardingDoc 엔티티

    Raises:
        RepoNotFoundError (404):      repo_id에 해당하는 저장소가 없을 때
        DatabaseSaveFailedError (500): DB 저장 중 예외 발생 시
    '''
    repo = GenDocRepository(db)

    ## 1. 저장소 존재 여부 확인
    analysis_job = await repo.get_repo_by_id(repo_id)
    if analysis_job is None:
        logger.warning(
            "[DOCS-GEN-B-301] 저장소 없음 | repo_id=%s", repo_id
        )
        raise RepoNotFoundError()

    ## 2. 문서 저장
    try:
        doc = await repo.save_doc(
            repo_id=repo_id,
            job_id=job_id,
            content=content,
            version=version,
            report_json=report_json,
        )
        await db.commit()
        logger.info(
            "[DOCS-GEN-B-301] 저장 완료 | doc_id=%s repo_id=%s version=%d",
            doc.id, repo_id, version,
        )
        return doc
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception(
            "[DOCS-GEN-B-301] DB 저장 실패 | repo_id=%s version=%d: %s",
            repo_id, version, exc,
        )
        raise DatabaseSaveFailedError() from exc


# ──────────────────────────────────────────────────────────────
# DOCS-GEN-API-001: 온보딩 가이드북 조회
# ──────────────────────────────────────────────────────────────
async def get_onboarding_doc(
    db: AsyncSession,
    repo_id: UUID,
    fmt: str = "markdown",
) -> DocGetMarkdownData | DocGetJsonData:
    '''
    저장된 온보딩 가이드북을 조회하고 format에 따라 응답 데이터를 반환한다.

    DOCS-GEN-B-101 구현:
      1. repo_id 존재 여부 확인 (없으면 404 RepoNotFoundError)
      2. 활성 문서 조회 (없으면 404 DocsNotFoundError)
      3. format=markdown → Markdown 전문 반환
      4. format=json → report_json 기반 구조화 데이터 반환

    Args:
        db:      AsyncSession (외부 주입)
        repo_id: 대상 저장소 ID (analysis_jobs.id)
        fmt:     응답 형식 ("markdown" 또는 "json", 기본값: "markdown")

    Returns:
        DocGetMarkdownData (format=markdown) 또는 DocGetJsonData (format=json)

    Raises:
        RepoNotFoundError (404): repo_id에 해당하는 저장소가 없을 때
        DocsNotFoundError (404): 활성 가이드북이 아직 생성되지 않았을 때
    '''
    repo = GenDocRepository(db)

    ## 1. 저장소 존재 여부 확인
    analysis_job = await repo.get_repo_by_id(repo_id)
    if analysis_job is None:
        logger.warning("[DOCS-GEN-API-001] 저장소 없음 | repo_id=%s", repo_id)
        raise RepoNotFoundError()

    ## 2. 활성 문서 조회
    doc = await repo.get_active_by_repo_id(repo_id)
    if doc is None:
        logger.warning("[DOCS-GEN-API-001] 가이드북 없음 | repo_id=%s", repo_id)
        raise DocsNotFoundError()

    ## 3. format=json: report_json 기반 구조화 데이터 반환
    if fmt == "json":
        report = doc.report_json or {}
        guide = report.get("guide") or {}

        ## stack은 {technologies, primary_language, ...} 형태의 dict — technologies 리스트 추출
        stack_raw = report.get("stack") or {}
        stack_list = (
            stack_raw.get("technologies", [])
            if isinstance(stack_raw, dict)
            else stack_raw
        )

        ## folder_summaries는 file_map 래퍼 내부의 실제 폴더맵
        folder_map = (
            (report.get("file_map") or {}).get("folder_summaries") or {}
        )
        folder_items = [
            {"path": k, "description": v}
            for k, v in folder_map.items()
        ]

        ## core_flow는 guide가 아닌 summary.flow_explanation에 저장됨
        core_flow = (report.get("summary") or {}).get("flow_explanation")

        logger.info(
            "[DOCS-GEN-API-001] JSON 조회 완료 | repo_id=%s version=%d",
            repo_id, doc.version,
        )
        return DocGetJsonData(
            repo_id=repo_id,
            repo_name=getattr(analysis_job, "repo_name", "") or "",
            summary=report.get("summary"),
            stack=stack_list,
            reading_order=guide.get("reading_order") or [],
            danger_files=guide.get("risk_files") or [],
            core_flow=core_flow,
            folder_summaries=folder_items,
            generated_at=doc.created_at,
            version=doc.version,
        )

    ## 4. format=markdown (기본): Markdown 전문 반환
    logger.info(
        "[DOCS-GEN-API-001] Markdown 조회 완료 | repo_id=%s version=%d",
        repo_id, doc.version,
    )
    return DocGetMarkdownData(
        repo_id=repo_id,
        repo_name=getattr(analysis_job, "repo_name", "") or "",
        content=doc.content,
        generated_at=doc.created_at,
        version=doc.version,
    )


# ──────────────────────────────────────────────────────────────
# DOCS-GEN-API-002: 가이드북 생성 사전 검증 및 백그라운드 큐잉
# ──────────────────────────────────────────────────────────────
async def validate_and_queue_doc_generation(
    db: AsyncSession,
    repo_id: UUID,
    force: bool,
    background_tasks: BackgroundTasks,
    model: str = "gpt-4o-mini",
) -> tuple[UUID, int]:
    '''
    가이드북 생성 트리거(API-002) 사전 검증 후 백그라운드 작업을 등록한다.

    검증 순서:
      1. repo_id 존재 여부 (404 REPO_NOT_FOUND)
      2. 가이드북 생성 중복 실행 검사 (409 DOCS_GENERATION_IN_PROGRESS)
      3. 기존 문서 존재 여부 + force 플래그 검사 (409 DOCS_ALREADY_EXISTS)
      4. RAG 파이프라인 완료 여부 (422 ANALYSIS_NOT_COMPLETED)

    Args:
        db:               AsyncSession
        repo_id:          대상 저장소 ID
        force:            기존 가이드북 덮어쓰기 여부
        background_tasks: FastAPI BackgroundTasks 인스턴스
        model:            가이드북 생성에 사용할 LLM 모델 식별자

    Returns:
        (job_id, next_version) 튜플 — 202 응답에 사용

    Raises:
        RepoNotFoundError (404)
        DocsGenerationInProgressError (409)
        DocsAlreadyExistsError (409)
        AnalysisNotCompletedError (422)
    '''
    from app.gen.background import (
        _mark_in_progress,
        is_generation_in_progress,
        run_doc_generation,
    )

    repo = GenDocRepository(db)
    settings = get_settings()

    ## 1. 저장소 존재 여부 확인
    analysis_job = await repo.get_repo_by_id(repo_id)
    if analysis_job is None:
        logger.warning("[DOCS-GEN-API-002] 저장소 없음 | repo_id=%s", repo_id)
        raise RepoNotFoundError()

    ## 2. 가이드북 생성 중복 실행 검사
    if is_generation_in_progress(repo_id):
        logger.warning("[DOCS-GEN-API-002] 생성 진행 중 | repo_id=%s", repo_id)
        raise DocsGenerationInProgressError()

    ## 3. 기존 문서 존재 여부 검사 (force=false 이면 409)
    latest_version = await repo.get_latest_version(repo_id)
    if latest_version > 0 and not force:
        logger.warning(
            "[DOCS-GEN-API-002] 이미 존재 | repo_id=%s version=%d",
            repo_id, latest_version,
        )
        raise DocsAlreadyExistsError()

    ## 4. RAG 파이프라인 완료 여부 확인
    if analysis_job.status != JobStatus.COMPLETED.value:
        logger.warning(
            "[DOCS-GEN-API-002] 분석 미완료 | repo_id=%s status=%s",
            repo_id, analysis_job.status,
        )
        raise AnalysisNotCompletedError()

    ## 5. 백그라운드 등록 전 동기적으로 진행 중 마킹하여 Race Condition 방지
    ## (BackgroundTask 내부에서 마킹하면 HTTP 응답 반환 후에야 set에 추가되어,
    ##  연속 요청 2건이 동시에 검사를 통과하는 경쟁 조건이 발생함)
    next_version = latest_version + 1
    clone_path = f"{settings.CLONE_BASE_DIR}/{repo_id}/repo"

    _mark_in_progress(repo_id)
    background_tasks.add_task(
        run_doc_generation,
        repo_id=repo_id,
        job_id=analysis_job.id,
        analysis_report=analysis_job.report_json or {},
        repo_name=analysis_job.repo_name,
        version=next_version,
        clone_path=clone_path,
        model=model,
    )

    logger.info(
        "[DOCS-GEN-API-002] 큐잉 완료 | repo_id=%s version=%d", repo_id, next_version
    )
    return analysis_job.id, next_version
