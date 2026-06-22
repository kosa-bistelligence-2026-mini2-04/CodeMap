"""
RAG EMBED 데이터베이스 저장 레이어

RAG_EMBED_SPEC.md B-301에 따라 임베딩 벡터와 메타데이터를
pgvector(PostgreSQL)에 배치 upsert한다.

주요 계약 (test_embed_contract.py):
  EmbedRepository.save_to_pgvector(self, job_id, files)

설계 원칙:
  - 각 파일(ParsedFile)마다 type="FILE" 대표 CodeNode를 먼저 삽입한다.
    → chunks가 없는 빈 파일(__init__.py 등)도 노드가 생성되므로
      Dependency FK 제약 위반(ForeignKeyViolation) 없이 import 관계를 저장할 수 있다.
    → Dependency는 FILE 노드들의 ID 간에 관계를 맺는 것이 정석이다.
  - CHUNK 노드는 FILE 대표 노드 생성 후에 삽입한다.
  - file.file_type은 Enum 또는 str이 모두 올 수 있으므로
    getattr(file.file_type, 'value', file.file_type) 으로 안전하게 처리한다.
"""

import logging
import uuid
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.embed.models import CodeNode, Dependency
from app.parse.schemas import ParsedFile

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
    # 배치 저장: 파일 대표 노드 + 청크 노드 → code_nodes 테이블 upsert
    # ──────────────────────────────────────────────────────────
    async def save_to_pgvector(self, job_id: UUID, files: list[ParsedFile]) -> int:
        """
        임베딩이 완료된 ParsedFile 목록을 pgvector에 배치 저장(upsert)한다.

        저장 순서 (중요):
          1. 파일당 대표 CodeNode(type="FILE") 1개 먼저 삽입
             → chunks가 없는 빈 파일도 노드 생성 보장
             → Dependency FK 참조 시 항상 대상 레코드가 존재함
          2. 각 파일의 CHUNK 노드들을 100개 단위 배치 삽입

        Args:
            job_id: 분석 작업 ID (AnalysisJob.id)
            files:  임베딩이 채워진 ParsedFile 목록

        Returns:
            저장된 CHUNK CodeNode 행 수 (FILE 대표 노드는 별도 계산)
        """
        # ── 1단계: 파일 대표 노드 선 삽입 + path→file_node_id 맵 구성
        # Dependency 저장 시 source/target을 FILE 노드로 참조하기 위해 맵을 보존한다.
        file_node_map: dict[str, UUID] = {}  # path → CodeNode.id

        file_nodes: list[CodeNode] = []
        for file in files:
            # file_type은 Enum 인스턴스 또는 직렬화된 str이 모두 올 수 있으므로
            # getattr로 안전하게 값을 추출한다. (AttributeError 방지)
            file_type_value = getattr(file.file_type, "value", file.file_type)

            file_node_id = uuid.uuid4()
            file_node_map[file.path] = file_node_id
            file_nodes.append(
                CodeNode(
                    id=file_node_id,
                    job_id=job_id,
                    path=file.path,
                    type=file_type_value,   # "FILE" or "DIRECTORY"
                    depth=file.depth,
                    chunk_index=-1,         # -1: 대표 파일 노드임을 구분
                    content=None,
                    summary=file.summary,
                    embedding=None,         # 파일 대표 노드는 임베딩 없음
                    file_metadata={"is_file_node": True},
                    language=file.language,
                )
            )

        if file_nodes:
            self.db.add_all(file_nodes)
            await self.db.flush()
            logger.info(
                "[임베딩 저장] job=%s | 파일 대표 노드 %d개 삽입 완료",
                job_id, len(file_nodes),
            )

        # ── 2단계: CHUNK 노드 100개 단위 배치 삽입
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
                    type="CHUNK",
                    depth=file.depth,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    summary=chunk.content,      # 현 단계에서는 원문 = 임베딩 입력
                    embedding=chunk.embedding,  # generate_embeddings() 후 채워짐
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
                "[임베딩 저장] job=%s | 잔여 %d개 청크 flush 완료 (총 %d개 청크)",
                job_id, len(nodes_batch), saved,
            )

        # ── 3단계: import 관계(Dependency) 저장
        # ParsedFile.imports 목록을 FILE 대표 노드 ID 간 관계로 변환한다.
        await self._save_imports_as_dependencies(job_id, files, file_node_map)

        return saved

    async def _save_imports_as_dependencies(
        self,
        job_id: UUID,
        files: list[ParsedFile],
        file_node_map: dict[str, UUID],
    ) -> int:
        """
        ParsedFile.imports 목록을 code_dependencies 테이블에 저장한다.

        FILE 대표 노드(type="FILE") 간에 관계를 맺는다.
        import 대상이 file_node_map에 없는 경우(외부 패키지 등)는 건너뛴다.

        Args:
            job_id:        분석 작업 ID (로그용)
            files:         ParsedFile 목록
            file_node_map: path → CodeNode.id 맵 (FILE 대표 노드)

        Returns:
            저장된 Dependency 행 수
        """
        dep_rows: list[Dependency] = []
        skipped = 0

        for file in files:
            source_id = file_node_map.get(file.path)
            if source_id is None:
                continue  # 대표 노드가 없는 경우는 건너뜀 (방어 코드)

            for import_path in (file.imports or []):
                target_id = file_node_map.get(import_path)
                if target_id is None:
                    # 저장소 외부 패키지나 아직 파싱되지 않은 파일 → 건너뜀
                    skipped += 1
                    continue
                if source_id == target_id:
                    continue  # 자기 자신 참조 방지

                dep_rows.append(
                    Dependency(source_id=source_id, target_id=target_id, relation="import")
                )

        if dep_rows:
            self.db.add_all(dep_rows)
            await self.db.flush()

        logger.info(
            "[의존성 저장] job=%s | %d개 Dependency 저장 (외부 참조 %d건 스킵)",
            job_id, len(dep_rows), skipped,
        )
        return len(dep_rows)

    # ──────────────────────────────────────────────────────────
    # 기존 임베딩 삭제 (forceReembed=true 시 호출)
    # ──────────────────────────────────────────────────────────
    async def delete_by_job(self, job_id: UUID) -> int:
        """
        특정 분석 작업의 모든 CodeNode(임베딩)를 삭제한다.

        forceReembed=true 시 service에서 먼저 이 메서드를 호출한 뒤
        save_to_pgvector()로 재삽입한다.
        CASCADE 설정으로 code_dependencies도 연쇄 삭제된다.
        """
        result = await self.db.execute(
            delete(CodeNode).where(CodeNode.job_id == job_id)
        )
        deleted = result.rowcount
        logger.info("[임베딩 삭제] job=%s | %d개 CodeNode 삭제 완료 (Dependency 연쇄 삭제 포함)", job_id, deleted)
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
    # 외부 호출용 의존성 저장 (직접 ID 쌍을 아는 경우)
    # ──────────────────────────────────────────────────────────
    async def save_dependencies(self, deps: list[tuple[UUID, UUID, str]]) -> int:
        """
        파일 간 import 관계를 code_dependencies 테이블에 직접 저장한다.

        Note: 일반적으로 save_to_pgvector()가 내부적으로 import 관계를 처리하므로
              이 메서드는 외부에서 ID 쌍을 직접 알고 있는 경우에만 사용한다.

        Args:
            deps: (source_id, target_id, relation) 튜플 목록
        """
        rows = [
            Dependency(source_id=src, target_id=tgt, relation=rel)
            for src, tgt, rel in deps
        ]
        if rows:
            self.db.add_all(rows)
            await self.db.flush()
        logger.info("[의존성 저장] %d개 Dependency 저장 완료 (직접 호출)", len(rows))
        return len(rows)
