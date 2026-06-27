"""
RAG EMBED 서비스 레이어

RAG_EMBED_SPEC.md (B-201/B-301)에 따라 ParsedFile 목록의
코드 청크를 OpenAI text-embedding-3-large 모델로 임베딩하고
pgvector에 저장하는 비즈니스 로직을 담당한다.

주요 계약 (test_embed_contract.py):
  generate_embeddings(files)     — 청크 텍스트 → 벡터 변환 (배치)
  run_embed_pipeline(db, request) — 전체 파이프라인 오케스트레이션

RAG_EMBED_SPEC.md 구현 노트:
  - 모델: text-embedding-3-large + dimensions=1536
  - 배치 크기: 100개 (EMBEDDING_BATCH_SIZE)
  - 재시도: 지수 백오프 최대 3회 (tenacity)
  - 타이밍 로그: [단계별 소요시간] 형태로 기록
"""

import asyncio
import logging
import time
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.infra.config import get_settings
from app.embed.repository import EmbedRepository
from app.parse.schemas import CodeChunk, EmbedRequest, EmbedResult, ParsedFile

logger = logging.getLogger(__name__)
settings = get_settings()


# ──────────────────────────────────────────────────────────────
# RAG-EMBED-B-201: 임베딩 생성
#
# LangChain OpenAIEmbeddings wrapper 사용
# 100개 단위 배치 API 호출 + tenacity 지수 백오프
# ──────────────────────────────────────────────────────────────

# 재시도 대상 예외: OpenAI API 통신 오류(rate limit, 일시 장애)에만 한정한다.
# 로직 오류(ValueError, KeyError 등)는 재시도 없이 즉시 실패해야 한다.
try:
    from openai import APIError as _OpenAIAPIError
    _RETRYABLE_ERRORS = (_OpenAIAPIError,)
except ImportError:  # openai 미설치 환경 (CI 등)
    _RETRYABLE_ERRORS = (Exception,)  # type: ignore[assignment]


@retry(
    retry=retry_if_exception_type(_RETRYABLE_ERRORS),
    stop=stop_after_attempt(settings.EMBEDDING_MAX_RETRIES),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def _embed_batch(texts: list[str]) -> list[list[float]]:
    """
    단일 배치(100개 이하) 텍스트 → 임베딩 벡터 변환.

    tenacity 데코레이터로 지수 백오프 재시도 적용:
      1회 실패 → 1초, 2회 → 2초, 3회 → 4초 (RAG_EMBED_SPEC.md)
      재시도 대상: openai.APIError (rate limit, 일시 장애) 한정
      로직 오류(ValueError 등)는 즉시 reraise한다.
    """
    from langchain_openai import OpenAIEmbeddings

    embedder = OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,           # text-embedding-3-large
        dimensions=settings.EMBEDDING_DIMENSIONS, # 1536 (마트료시카 축소)
        api_key=settings.OPENAI_API_KEY.get_secret_value(),
    )
    # LangChain의 aembed_documents는 비동기 배치 임베딩을 지원한다.
    return await embedder.aembed_documents(texts)


async def generate_embeddings(files: list[ParsedFile]) -> list[ParsedFile]:
    """
    ParsedFile 목록의 모든 CodeChunk에 임베딩 벡터를 채워 반환한다.

    RAG_EMBED_SPEC.md B-201:
      - 배치 크기 EMBEDDING_BATCH_SIZE(기본 100)개 단위로 API 호출
      - 임베딩 결과를 chunk.embedding 필드에 직접 채움 (in-place mutation 아닌 새 객체)
      - OPENAI_API_KEY 미설정 시 빈 벡터([])로 처리 (개발·테스트 환경 대응)

    Args:
        files: ParsedFile 목록 (chunks 포함)

    Returns:
        임베딩이 채워진 ParsedFile 목록
    """
    _t0 = time.perf_counter()
    batch_size = settings.EMBEDDING_BATCH_SIZE

    # ── 1. 배치를 구성하기 위해 (파일 인덱스, 청크 인덱스, 텍스트) 플랫 리스트 생성
    flat: list[tuple[int, int, str]] = []  # (file_idx, chunk_idx, text)
    for fi, file in enumerate(files):
        for ci, chunk in enumerate(file.chunks):
            text = chunk.content or ""
            if text.strip():
                flat.append((fi, ci, text))

    if not flat:
        logger.info("[임베딩 생성] 임베딩 대상 청크 없음 (content 모두 비어있음)")
        return files

    total_chunks = len(flat)
    logger.info("[임베딩 생성] 총 %d개 청크 임베딩 시작 (배치 크기: %d)", total_chunks, batch_size)

    # ── 2. 결과를 담을 가변 구조 준비 (ParsedFile/CodeChunk는 Pydantic 모델이므로 dict 변환)
    files_dict = [file.model_dump() for file in files]

    # ── 3. 100개 단위 배치 처리
    api_key = settings.OPENAI_API_KEY.get_secret_value()
    embedded_count = 0
    failed_count = 0

    for batch_start in range(0, len(flat), batch_size):
        batch = flat[batch_start : batch_start + batch_size]
        texts = [item[2] for item in batch]

        try:
            if not api_key:
                # API 키 없음(개발/CI): 빈 리스트([])는 Vector(1536) 컬럼 저장 시 차원 불일치를
                # 일으키므로 None(컬럼 nullable)으로 둔다. 임베딩 없는 청크로 추적된다.
                vectors = [None for _ in texts]
                logger.debug("[임베딩 생성] OPENAI_API_KEY 미설정 → 임베딩 None 처리")
            else:
                vectors = await _embed_batch(texts)

            # 결과를 files_dict에 반영
            for (fi, ci, _), vector in zip(batch, vectors):
                files_dict[fi]["chunks"][ci]["embedding"] = vector
            embedded_count += len(batch)

            logger.info(
                "[임베딩 생성] 배치 %d/%d 완료 (%d개 청크)",
                batch_start // batch_size + 1,
                (len(flat) - 1) // batch_size + 1,
                len(batch),
            )

        except Exception as exc:
            # 배치 실패 시 해당 청크 embedding=None으로 두고 계속 진행
            logger.warning(
                "[임베딩 생성] 배치 실패 (시작 인덱스=%d, %d개 청크): %s",
                batch_start, len(batch), exc,
            )
            failed_count += len(batch)

    elapsed = time.perf_counter() - _t0
    logger.info(
        "[단계별 소요시간] 임베딩 생성 | 성공 %d개 / 실패 %d개 | 소요시간=%.3f초",
        embedded_count, failed_count, elapsed,
    )

    # ── 4. dict → ParsedFile 재조립
    return [ParsedFile(**fd) for fd in files_dict]


# ──────────────────────────────────────────────────────────────
# RAG-EMBED-B-301: pgvector 저장 파이프라인 오케스트레이터
# ──────────────────────────────────────────────────────────────

async def run_embed_pipeline(db: AsyncSession, request: EmbedRequest) -> EmbedResult:
    """
    임베딩 생성 + pgvector 저장 전체 파이프라인을 실행한다.

    RAG_EMBED_SPEC.md B-201 + B-301:
      1. force_reembed=True 시 기존 임베딩 삭제
      2. generate_embeddings()로 배치 임베딩 생성
      3. EmbedRepository.save_to_pgvector()로 배치 저장
      4. commit은 이 함수에서 담당

    Args:
        db:      AsyncSession (외부 주입)
        request: EmbedRequest (job_id, files, force_reembed)

    Returns:
        EmbedResult (총 파일 수, 청크 수, 저장 수, 실패 경로 목록)
    """
    _t0 = time.perf_counter()
    repo = EmbedRepository(db)
    job_id: UUID = request.job_id

    logger.info(
        "[임베딩 파이프라인 시작] job=%s | 파일 수=%d | force_reembed=%s",
        job_id, len(request.files), request.force_reembed,
    )

    # ── 1. 기존 임베딩 삭제 (force_reembed 옵션)
    if request.force_reembed:
        deleted = await repo.delete_by_job(job_id)
        logger.info("[임베딩 파이프라인] 기존 임베딩 %d개 삭제 완료", deleted)

    # ── 2. 임베딩 생성 (배치 API 호출)
    failed_paths: list[str] = []
    try:
        embedded_files = await generate_embeddings(request.files)
    except Exception as exc:
        logger.exception("[임베딩 파이프라인] generate_embeddings 전체 실패: %s", exc)
        embedded_files = request.files
        failed_paths = [f.path for f in request.files]

    # 임베딩이 채워지지 않은 파일 경로 추적
    if not failed_paths:
        for file in embedded_files:
            file_failed = any(c.embedding is None for c in file.chunks if c.content)
            if file_failed:
                failed_paths.append(file.path)

    # ── 3. pgvector 저장
    total_files = len(embedded_files)
    total_chunks = sum(len(f.chunks) for f in embedded_files)

    try:
        save_result = await repo.save_to_pgvector(job_id, embedded_files)
        await db.commit()

        # 테스트 목(mock)은 EmbedResult 객체를 반환할 수 있으므로 타입 확인
        if isinstance(save_result, EmbedResult):
            elapsed = time.perf_counter() - _t0
            logger.info(
                "[단계별 소요시간] 임베딩 파이프라인(생성+저장) | job=%s | 소요시간=%.3f초",
                job_id, elapsed,
            )
            return save_result

        saved_chunks = int(save_result)
    except Exception as exc:
        logger.exception("[임베딩 파이프라인] save_to_pgvector 실패: %s", exc)
        await db.rollback()
        saved_chunks = 0
        failed_paths = list({f.path for f in request.files})

    elapsed = time.perf_counter() - _t0
    logger.info(
        "[단계별 소요시간] 임베딩 파이프라인(생성+저장) | job=%s | "
        "파일=%d 청크=%d 저장=%d 실패=%d | 소요시간=%.3f초",
        job_id, total_files, total_chunks, saved_chunks, len(failed_paths), elapsed,
    )

    return EmbedResult(
        job_id=job_id,
        total_files=total_files,
        total_chunks=total_chunks,
        saved_chunks=saved_chunks,
        failed_paths=failed_paths,
    )


# ──────────────────────────────────────────────────────────────
# RAG 검색: 벡터 유사도 기반 코드 청크 검색 (답변용)
#
# 팀 orchestrator search 도구(mcp_tools/search.py)와 chat 폴백 분기가 호출하는 계약.
# 임베딩 인덱스가 준비됐으면 vector_search로, 아니면 호출측이 키워드 검색으로 폴백한다.
# ──────────────────────────────────────────────────────────────

async def embed_ready(db: AsyncSession, repo_id: UUID) -> bool:
    """해당 저장소의 임베딩 인덱스가 검색 가능한 상태인지 확인한다.

    채팅/오케스트레이터가 "벡터 검색 ↔ 키워드 폴백" 분기에 사용한다.
    """
    return await EmbedRepository(db).has_embeddings(repo_id)


async def vector_search(
    db: AsyncSession, repo_id: UUID, query: str, k: int = 5
) -> list[dict]:
    """질문을 임베딩해 pgvector에서 관련 코드 청크를 유사도 순으로 검색한다.

    반환: [{"file", "line", "snippet", "score"}] 목록.
      - score = 1 - 코사인거리 (높을수록 유사)
    API 키 미설정이거나 인덱스가 비어 있으면 빈 목록을 반환한다(호출측이 폴백).
    """
    if not query or not query.strip():
        return []
    if not settings.OPENAI_API_KEY.get_secret_value():
        return []

    vectors = await _embed_batch([query])
    if not vectors or not vectors[0]:
        return []
    query_vector = vectors[0]

    rows = await EmbedRepository(db).similarity_search(repo_id, query_vector, k)
    results: list[dict] = []
    for node, distance in rows:
        meta = node.file_metadata or {}
        results.append({
            "file": node.path,
            "line": meta.get("start_line"),
            "snippet": node.content or "",
            "score": round(1.0 - distance, 4),
        })
    return results
