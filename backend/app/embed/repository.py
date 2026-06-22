"""
RAG EMBED 데이터베이스 저장 레이어

RAG_EMBED_SPEC.md B-301에 따라 임베딩 벡터와 메타데이터를
pgvector(PostgreSQL)에 배치 upsert한다.

주요 계약 (test_embed_contract.py):
  EmbedRepository.save_to_pgvector(self, job_id, files)
"""

import logging
import uuid
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.embed.models import CodeNode, Dependency
from app.parse.schemas import EmbedRequest, ParsedFile

logger = logging.getLogger(__name__)


class EmbedRepository:
    """
    RAG 임베딩 벡터 저장·조회 레포지토리

    모든 DB 작업은 외부에서 주입받은 AsyncSession을 통해 실행한다.
    commit은 호출측(service)에서 담당한다.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ──────────────────────────────────────────────────────────
    # 배치 저장: 청크 목록 → code_nodes 테이블 upsert
    # ──────────────────────────────────────────────────────────
    async def save_to_pgvector(self, job_id: UUID, files: list[ParsedFile]) -> int:
        """
        임베딩이 완료된 ParsedFile 목록을 pgvector에 배치 저장(upsert)한다.

        RAG_EMBED_SPEC.md B-301:
        - 100개 단위 배치 upsert
        - forceReembed 시 기존 청크 삭제 후 재삽입 (호출측에서 삭제 후 호출)
        - HNSW 인덱스는 DDL에 이미 정의되어 있으므로 별도 생성 불필요

        Args:
            job_id: 분석 작업 ID (AnalysisJob.id)
            files:  임베딩이 채워진 ParsedFile 목록

        Returns:
            저장된 CodeNode 행 수
        """
        saved = 0
        nodes_batch: list[CodeNode] = []

        for file in files:
            for chunk in (file.chunks or []):
                metadata = {
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "chunk_type": chunk.chunk_type,
                    "symbol": chunk.symbol,
                }
                node = CodeNode(
                    id=uuid.uuid4(),
                    job_id=job_id,
                    path=file.path,
                    type=file.file_type.value,
                    depth=file.depth,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    summary=chunk.content,          # 현 단계에서는 원문 = 임베딩 입력
                    embedding=chunk.embedding,      # ParsedFile.chunks[*].embedding
                    file_metadata=metadata,
                    language=file.language,
                )
                nodes_batch.append(node)

                # 100개 단위 배치 flush
                if len(nodes_batch) >= 100:
                    self.db.add_all(nodes_batch)
                    await self.db.flush()
                    saved += len(nodes_batch)
                    logger.info(
                        "[임베딩 저장] job=%s | %d개 청크 flush 완료 (누계: %d)",
                        job_id, len(nodes_batch), saved,
                    )
                    nodes_batch = []

        # 잔여 배치 처리
        if nodes_batch:
            self.db.add_all(nodes_batch)
            await self.db.flush()
            saved += len(nodes_batch)
            logger.info(
                "[임베딩 저장] job=%s | 잔여 %d개 청크 flush 완료 (총 %d개)",
                job_id, len(nodes_batch), saved,
            )

        return saved

    # ──────────────────────────────────────────────────────────
    # 기존 임베딩 삭제 (forceReembed=true 시 호출)
    # ──────────────────────────────────────────────────────────
    async def delete_by_job(self, job_id: UUID) -> int:
        """
        특정 분석 작업의 모든 CodeNode(임베딩)를 삭제한다.

        forceReembed=true 시 service에서 먼저 이 메서드를 호출한 뒤
        save_to_pgvector()로 재삽입한다.
        """
        result = await self.db.execute(
            delete(CodeNode).where(CodeNode.job_id == job_id)
        )
        deleted = result.rowcount
        logger.info("[임베딩 삭제] job=%s | %d개 CodeNode 삭제 완료", job_id, deleted)
        return deleted

    # ──────────────────────────────────────────────────────────
    # 임베딩 존재 여부 확인
    # ──────────────────────────────────────────────────────────
    async def exists(self, job_id: UUID) -> bool:
        """특정 job_id의 임베딩이 이미 저장되어 있는지 확인한다."""
        result = await self.db.execute(
            select(CodeNode.id).where(CodeNode.job_id == job_id).limit(1)
        )
        return result.scalar_one_or_none() is not None

    # ──────────────────────────────────────────────────────────
    # 의존성 그래프 저장
    # ──────────────────────────────────────────────────────────
    async def save_dependencies(self, deps: list[tuple[UUID, UUID, str]]) -> int:
        """
        파일 간 import 관계를 code_dependencies 테이블에 저장한다.

        Args:
            deps: (source_id, target_id, relation) 튜플 목록

        Returns:
            저장된 Dependency 행 수
        """
        rows = [
            Dependency(source_id=src, target_id=tgt, relation=rel)
            for src, tgt, rel in deps
        ]
        self.db.add_all(rows)
        await self.db.flush()
        logger.info("[의존성 저장] %d개 Dependency 저장 완료", len(rows))
        return len(rows)
