"""
DOCS-GEN 서비스 계층 (DOCS-GEN-B-301, DOCS-GEN-API-001~004)

- save_onboarding_doc: 생성된 Markdown을 DB에 저장 (B-301)
- get_onboarding_doc: 저장된 가이드북 조회 (API-001)
- validate_and_queue_doc_generation: 가이드북 생성 사전 검증 (API-002)
- rebuild_onboarding_doc: 기존 문서 소프트 삭제 후 재생성 큐잉 (API-003)
- get_doc_download_content: 다운로드용 Markdown 내용 조회 (API-004)
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
from app.gen.schemas import (
    DocDangerFileItem,
    DocFolderSummaryItem,
    DocGetJsonData,
    DocGetMarkdownData,
    DocReadingOrderItem,
)
from app.infra.config import get_settings
from app.repo.schemas import JobStatus

logger = logging.getLogger(__name__)


def _normalize_summary(summary: object) -> str | None:
    """Convert master_report.summary to the DOCS_API_SPEC string contract."""
    if summary is None:
        return None
    if isinstance(summary, str):
        return summary
    if not isinstance(summary, dict):
        return str(summary)

    preferred_keys = ("purpose", "overview", "summary", "description")
    for key in preferred_keys:
        value = summary.get(key)
        if isinstance(value, str) and value.strip():
            return value

    text_parts = [
        value.strip()
        for value in summary.values()
        if isinstance(value, str) and value.strip()
    ]
    return "\n".join(text_parts) if text_parts else None


def _normalize_stack(stack: object) -> list[str]:
    if isinstance(stack, dict):
        stack = stack.get("technologies") or []
    if not isinstance(stack, list):
        return []
    return [str(item) for item in stack if item]


def _normalize_reading_order(reading_order: object) -> list[DocReadingOrderItem]:
    if not isinstance(reading_order, list):
        return []

    items: list[DocReadingOrderItem] = []
    for index, item in enumerate(reading_order, start=1):
        if isinstance(item, str):
            path = item
            rank = index
            reason = ""
        elif isinstance(item, dict):
            path = item.get("path") or item.get("file") or ""
            rank = item.get("rank") or index
            reason = item.get("reason") or item.get("description") or ""
        else:
            continue

        if path:
            try:
                rank_value = int(rank)
            except (TypeError, ValueError):
                rank_value = index
            items.append(
                DocReadingOrderItem(
                    rank=rank_value,
                    path=str(path),
                    reason=str(reason),
                )
            )
    return items


def _normalize_danger_files(danger_files: object) -> list[DocDangerFileItem]:
    if not isinstance(danger_files, list):
        return []

    items: list[DocDangerFileItem] = []
    for item in danger_files:
        if isinstance(item, str):
            path = item
            reason = ""
        elif isinstance(item, dict):
            path = item.get("path") or item.get("file") or ""
            reason = item.get("reason") or item.get("description") or ""
        else:
            continue

        if path:
            items.append(DocDangerFileItem(path=str(path), reason=str(reason)))
    return items


def _normalize_folder_summaries(file_map: object) -> list[DocFolderSummaryItem]:
    if not isinstance(file_map, dict):
        return []

    folder_map = file_map.get("folder_summaries") or file_map
    if not isinstance(folder_map, dict):
        return []

    return [
        DocFolderSummaryItem(path=str(path), description=str(description))
        for path, description in folder_map.items()
        if path
    ]


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

        summary_raw = report.get("summary")
        core_flow_raw = (
            summary_raw.get("flow_explanation")
            if isinstance(summary_raw, dict)
            else None
        )
        core_flow = (
            core_flow_raw
            if isinstance(core_flow_raw, str) or core_flow_raw is None
            else str(core_flow_raw)
        )

        logger.info(
            "[DOCS-GEN-API-001] JSON 조회 완료 | repo_id=%s version=%d",
            repo_id, doc.version,
        )
        return DocGetJsonData(
            repoId=repo_id,
            repoName=getattr(analysis_job, "repo_name", "") or "",
            summary=_normalize_summary(summary_raw),
            stack=_normalize_stack(report.get("stack")),
            readingOrder=_normalize_reading_order(guide.get("reading_order")),
            dangerFiles=_normalize_danger_files(guide.get("risk_files")),
            coreFlow=core_flow,
            folderSummaries=_normalize_folder_summaries(report.get("file_map")),
            generatedAt=doc.created_at,
            version=doc.version,
        )

    ## 4. format=markdown (기본): Markdown 전문 반환
    logger.info(
        "[DOCS-GEN-API-001] Markdown 조회 완료 | repo_id=%s version=%d",
        repo_id, doc.version,
    )
    return DocGetMarkdownData(
        repoId=repo_id,
        repoName=getattr(analysis_job, "repo_name", "") or "",
        content=doc.content,
        generatedAt=doc.created_at,
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


# ──────────────────────────────────────────────────────────────
# DOCS-GEN-API-003: 가이드북 재생성 (B-207)
# ──────────────────────────────────────────────────────────────
async def rebuild_onboarding_doc(
    db: AsyncSession,
    repo_id: UUID,
    background_tasks: BackgroundTasks,
    model: str = "gpt-4o-mini",
    reason: str | None = None,
) -> tuple[UUID, int, int]:
    '''
    기존 온보딩 가이드북을 소프트 삭제한 뒤 최신 분석 기반으로 재생성을 큐잉한다.

    DOCS-GEN-B-207 구현:
      1. repo_id 존재 여부 확인 (404 REPO_NOT_FOUND)
      2. 활성 문서 조회 → 없으면 404 DOCS_NOT_FOUND
      3. 활성 문서 소프트 삭제 (is_active=False)
      4. BackgroundTask로 재생성 파이프라인 큐잉
      5. (job_id, previous_version, new_version) 반환

    Args:
        db:               AsyncSession
        repo_id:          대상 저장소 ID
        background_tasks: FastAPI BackgroundTasks 인스턴스
        model:            LLM 모델명 (기본: "gpt-4o-mini")
        reason:           재생성 요청 사유 (로그용, 선택)

    Returns:
        (job_id, previous_version, new_version) 튜플

    Raises:
        RepoNotFoundError (404):  저장소가 없을 때
        DocsNotFoundError (404):  재생성할 기존 가이드북이 없을 때
    '''
    from app.gen.background import run_doc_generation

    repo = GenDocRepository(db)
    settings = get_settings()

    ## 1. 저장소 존재 여부 확인
    analysis_job = await repo.get_repo_by_id(repo_id)
    if analysis_job is None:
        logger.warning("[DOCS-GEN-API-003] 저장소 없음 | repo_id=%s", repo_id)
        raise RepoNotFoundError()

    ## 2. 재생성 대상 활성 문서 조회
    active_doc = await repo.get_active_by_repo_id(repo_id)
    if active_doc is None:
        logger.warning("[DOCS-GEN-API-003] 재생성 대상 없음 | repo_id=%s", repo_id)
        raise DocsNotFoundError("재생성할 온보딩 가이드북이 아직 생성되지 않았습니다.")

    previous_version = active_doc.version
    new_version = previous_version + 1

    ## 3. 기존 활성 문서 소프트 삭제
    try:
        await repo.soft_delete_active_docs(repo_id)
        await db.commit()
        logger.info(
            "[DOCS-GEN-API-003] 소프트 삭제 완료 | repo_id=%s version=%d",
            repo_id, previous_version,
        )
    except Exception as exc:
        await db.rollback()
        logger.exception(
            "[DOCS-GEN-API-003] 소프트 삭제 실패 | repo_id=%s: %s", repo_id, exc
        )
        raise DatabaseSaveFailedError() from exc

    ## 4. 재생성 백그라운드 작업 등록
    ## 프로젝트 표준 클론 경로: {CLONE_BASE_DIR}/{repo_id}/repo
    clone_path = f"{settings.CLONE_BASE_DIR}/{repo_id}/repo"
    if reason:
        logger.info(
            "[DOCS-GEN-API-003] 재생성 사유 | repo_id=%s reason=%s",
            repo_id, reason,
        )

    background_tasks.add_task(
        run_doc_generation,
        repo_id=repo_id,
        job_id=analysis_job.id,
        analysis_report=analysis_job.report_json or {},
        repo_name=analysis_job.repo_name,
        version=new_version,
        clone_path=clone_path,
        model=model,
    )

    logger.info(
        "[DOCS-GEN-API-003] 재생성 큐잉 완료 | repo_id=%s prev=%d new=%d",
        repo_id, previous_version, new_version,
    )
    return analysis_job.id, previous_version, new_version


# ──────────────────────────────────────────────────────────────
# DOCS-GEN-API-004: 가이드북 파일 다운로드 (F-201)
# ──────────────────────────────────────────────────────────────
async def get_doc_download_content(
    db: AsyncSession,
    repo_id: UUID,
) -> tuple[str, str]:
    '''
    다운로드용 온보딩 가이드북 Markdown 내용과 저장소 이름을 반환한다.

    DOCS-GEN-F-201 구현:
      1. repo_id 존재 여부 확인 (404 REPO_NOT_FOUND)
      2. 활성 문서 조회 (404 DOCS_NOT_FOUND)
      3. (markdown_content, repo_name) 튜플 반환

    Args:
        db:      AsyncSession (외부 주입)
        repo_id: 대상 저장소 ID

    Returns:
        (content, repo_name) 튜플

    Raises:
        RepoNotFoundError (404):  저장소가 없을 때
        DocsNotFoundError (404):  활성 가이드북이 없을 때
    '''
    repo = GenDocRepository(db)

    ## 1. 저장소 존재 여부 확인
    analysis_job = await repo.get_repo_by_id(repo_id)
    if analysis_job is None:
        logger.warning("[DOCS-GEN-API-004] 저장소 없음 | repo_id=%s", repo_id)
        raise RepoNotFoundError()

    ## 2. 활성 문서 조회
    doc = await repo.get_active_by_repo_id(repo_id)
    if doc is None:
        logger.warning("[DOCS-GEN-API-004] 가이드북 없음 | repo_id=%s", repo_id)
        raise DocsNotFoundError()

    repo_name = getattr(analysis_job, "repo_name", "") or "onboarding"
    logger.info(
        "[DOCS-GEN-API-004] 다운로드 준비 | repo_id=%s version=%d",
        repo_id, doc.version,
    )
    return doc.content, repo_name
