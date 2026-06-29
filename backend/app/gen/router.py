"""
DOCS-GEN API 라우터 (DOCS-GEN-API-001~005)

GET  /api/gen/docs/{repo_id}          — 온보딩 가이드북 조회 (API-001)
POST /api/gen/docs/{repo_id}          — 가이드북 생성 트리거 (API-002)
PUT  /api/gen/docs/{repo_id}          — 가이드북 재생성 (API-003)
GET  /api/gen/docs/{repo_id}/download — 가이드북 파일 다운로드 (API-004)
POST /api/gen/docs/{repo_id}/save     — Markdown DB 저장 (API-005, 내부용)
"""

import logging
import re
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.gen.schemas import (
    DocGetMarkdownResponse,
    DocGetJsonResponse,
    DocRebuildRequest,
    DocRebuildData,
    DocRebuildResponse,
    DocSaveRequest,
    DocSaveData,
    DocSaveResponse,
    DocTriggerRequest,
    DocTriggerData,
    DocTriggerResponse,
)
from app.gen.service import (
    get_doc_download_content,
    get_onboarding_doc,
    rebuild_onboarding_doc,
    save_onboarding_doc,
    validate_and_queue_doc_generation,
)
from app.common.exceptions import FileGenerationFailedError
from app.infra.auth import get_current_user
from app.infra.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gen/docs", tags=["DOCS GEN"])


# ──────────────────────────────────────────────────────────────
# DOCS-GEN-API-001: 온보딩 가이드북 조회
# ──────────────────────────────────────────────────────────────
@router.get(
    "/{repo_id}",
    status_code=status.HTTP_200_OK,
    ## response_model을 명시하지 않아 FastAPI smart-union의 잘못된 직렬화 분기를 방지한다.
    ## 두 응답 모델이 동일한 최상위 envelope(code/message/data)를 공유하므로
    ## Union 지정 시 format=json 응답이 DocGetMarkdownResponse로 잘못 검증될 수 있다.
    ## 반환 타입 힌트가 문서화 역할을 대신하며, 실제 직렬화는 Pydantic 인스턴스가 처리한다.
    response_model=None,
    responses={
        200: {
            "description": "format=markdown: Markdown 전문 / format=json: master_report 구조화 JSON",
        }
    },
    summary="온보딩 가이드북 조회 (DOCS-GEN-API-001)",
)
async def get_doc(
    repo_id: UUID,
    _current_user: Annotated[dict, Depends(get_current_user)],
    format: Literal["markdown", "json"] = Query(default="markdown", description="응답 형식"),
    db: AsyncSession = Depends(get_db),
) -> DocGetMarkdownResponse | DocGetJsonResponse:
    '''
    저장된 온보딩 가이드북을 조회한다.

    - format=markdown(기본): Markdown 전문과 메타데이터 반환
    - format=json: master_report 기반 구조화 JSON 반환

    에러 응답:
    - 404 REPO_NOT_FOUND:  저장소 없음
    - 404 DOCS_NOT_FOUND:  가이드북 미생성
    '''
    from app.gen.schemas import DocGetJsonData

    data = await get_onboarding_doc(db=db, repo_id=repo_id, fmt=format)

    if isinstance(data, DocGetJsonData):
        logger.info("[DOCS-GEN-API-001] JSON 응답 | repo_id=%s", repo_id)
        return DocGetJsonResponse(data=data)

    logger.info("[DOCS-GEN-API-001] Markdown 응답 | repo_id=%s", repo_id)
    return DocGetMarkdownResponse(data=data)


# ──────────────────────────────────────────────────────────────
# DOCS-GEN-API-002: 가이드북 생성 트리거
# ──────────────────────────────────────────────────────────────
@router.post(
    "/{repo_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocTriggerResponse,
    summary="온보딩 가이드북 생성 트리거 (DOCS-GEN-API-002)",
)
async def trigger_doc_generation(
    repo_id: UUID,
    body: DocTriggerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> DocTriggerResponse:
    '''
    Map-Reduce 파이프라인으로 온보딩 가이드북 생성을 시작한다.

    즉시 202를 반환하고, 실제 생성 작업은 BackgroundTasks로 비동기 실행한다.

    에러 응답:
    - 404 REPO_NOT_FOUND:            저장소 없음
    - 409 DOCS_ALREADY_EXISTS:       force=false & 기존 가이드북 존재
    - 409 DOCS_GENERATION_IN_PROGRESS: 생성 진행 중
    - 422 ANALYSIS_NOT_COMPLETED:    RAG 파이프라인 미완료
    '''
    job_id, version = await validate_and_queue_doc_generation(
        db=db,
        repo_id=repo_id,
        force=body.force,
        background_tasks=background_tasks,
        model=body.model,
    )

    logger.info(
        "[DOCS-GEN-API-002] 생성 시작 | repo_id=%s job_id=%s version=%d",
        repo_id, job_id, version,
    )

    return DocTriggerResponse(
        data=DocTriggerData(
            jobId=job_id,
            repoId=repo_id,
            status="docs_queued",
            estimatedMinutes=2,
        )
    )


# ──────────────────────────────────────────────────────────────
# DOCS-GEN-API-003: 가이드북 재생성
# ──────────────────────────────────────────────────────────────
@router.put(
    "/{repo_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocRebuildResponse,
    summary="온보딩 가이드북 재생성 (DOCS-GEN-API-003)",
)
async def rebuild_doc(
    repo_id: UUID,
    body: DocRebuildRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> DocRebuildResponse:
    '''
    기존 온보딩 가이드북을 소프트 삭제한 뒤 재생성 파이프라인을 시작한다.

    즉시 202를 반환하고, 실제 재생성 작업은 BackgroundTasks로 비동기 실행한다.

    에러 응답:
    - 404 REPO_NOT_FOUND:  저장소 없음
    - 404 DOCS_NOT_FOUND:  재생성할 기존 가이드북이 없음
    '''
    job_id, previous_version, new_version = await rebuild_onboarding_doc(
        db=db,
        repo_id=repo_id,
        background_tasks=background_tasks,
        model=body.model,
        reason=body.reason,
    )

    logger.info(
        "[DOCS-GEN-API-003] 재생성 시작 | repo_id=%s job_id=%s prev=%d new=%d",
        repo_id, job_id, previous_version, new_version,
    )

    return DocRebuildResponse(
        data=DocRebuildData(
            **{
                "job_id": job_id,
                "repo_id": repo_id,
                "previous_version": previous_version,
                "new_version": new_version,
            }
        )
    )


# ──────────────────────────────────────────────────────────────
# DOCS-GEN-API-004: 가이드북 파일 다운로드
# ──────────────────────────────────────────────────────────────
@router.get(
    "/{repo_id}/download",
    status_code=status.HTTP_200_OK,
    response_class=Response,
    summary="온보딩 가이드북 파일 다운로드 (DOCS-GEN-API-004)",
)
async def download_doc(
    repo_id: UUID,
    _current_user: Annotated[dict, Depends(get_current_user)],
    format: Literal["md", "pdf"] = Query(default="md", description="다운로드 형식"),
    db: AsyncSession = Depends(get_db),
) -> Response:
    '''
    온보딩 가이드북을 파일로 다운로드한다.

    - format=md(기본): Markdown 파일 (.md) 다운로드
    - format=pdf: 현재 미지원 (500 FILE_GENERATION_FAILED)

    에러 응답:
    - 401 UNAUTHORIZED:           인증 필요
    - 404 REPO_NOT_FOUND:         저장소 없음
    - 404 DOCS_NOT_FOUND:         가이드북 미생성
    - 500 FILE_GENERATION_FAILED: 파일 생성 오류 (PDF 미지원 포함)
    '''
    if format == "pdf":
        logger.warning("[DOCS-GEN-API-004] PDF 미지원 | repo_id=%s", repo_id)
        raise FileGenerationFailedError("PDF 다운로드는 현재 지원되지 않습니다.")

    content, repo_name = await get_doc_download_content(db=db, repo_id=repo_id)

    ## 파일명 ASCII 외 문자 제거 (Content-Disposition 헤더는 latin-1만 허용)
    ## flags=re.ASCII 없이는 \w가 한글 등 유니코드 문자도 허용해 인코딩 오류 위험이 있다
    safe_name = re.sub(r"[^\w\-]", "_", repo_name, flags=re.ASCII)
    filename = f"{safe_name}_onboarding.md"

    logger.info(
        "[DOCS-GEN-API-004] 다운로드 응답 | repo_id=%s filename=%s",
        repo_id, filename,
    )

    return Response(
        content=content.encode("utf-8"),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ──────────────────────────────────────────────────────────────
# DOCS-GEN-API-005: Markdown DB 저장
# ──────────────────────────────────────────────────────────────
@router.post(
    "/{repo_id}/save",
    status_code=status.HTTP_201_CREATED,
    response_model=DocSaveResponse,
    summary="온보딩 가이드북 Markdown DB 저장 (DOCS-GEN-API-005)",
)
async def save_doc(
    repo_id: UUID,
    body: DocSaveRequest,
    db: AsyncSession = Depends(get_db),
) -> DocSaveResponse:
    '''
    생성된 Markdown 가이드북을 PostgreSQL docs 테이블에 저장한다.

    내부 파이프라인(DOCS-GEN-B-301)이 호출하는 API로,
    프론트엔드에서 직접 호출하지 않는다.

    - 404: repo_id에 해당하는 저장소가 없을 때 (REPO_NOT_FOUND)
    - 500: DB 저장 중 오류 (DATABASE_SAVE_FAILED)
    '''
    doc = await save_onboarding_doc(
        db=db,
        repo_id=repo_id,
        job_id=body.job_id,
        content=body.content,
        version=body.version,
    )

    logger.info(
        "[DOCS-GEN-API-005] 응답 | doc_id=%s repo_id=%s version=%d",
        doc.id, repo_id, body.version,
    )

    return DocSaveResponse(
        data=DocSaveData(
            docId=doc.id,
            repoId=repo_id,
            version=doc.version,
        )
    )
