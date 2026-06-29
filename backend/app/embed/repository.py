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

  - Deterministic UUID (uuid5) 정책:
    → CodeNode의 id를 uuid5(job_id, "FILE:{path}") 또는 uuid5(job_id, "CHUNK:{path}:{idx}")
      형태로 결정론적으로 생성한다.
    → 재실행 시 동일 (job_id, path, chunk_index)에 대해 항상 같은 UUID가 생성된다.
    → ON CONFLICT 충돌로 기존 row가 유지될 때 DB의 실제 id == file_node_map의 id가
      항상 일치하므로 _upsert_imports()의 FK 참조가 항상 유효하다.
    → uuid4(랜덤) 방식은 재실행 시 새 UUID를 생성해 file_node_map과 DB id가
      불일치하여 Dependency FK 위반이 발생하는 문제를 완전히 차단한다.

  - 실제 PostgreSQL upsert 사용 (INSERT ... ON CONFLICT DO UPDATE):
    → 같은 (job_id, path, chunk_index) 조합으로 파이프라인을 재실행해도
      IntegrityError 없이 embedding 벡터가 갱신된다.
    → force_reembed=False 상태에서 재시도·재실행이 안전하다.

  - file.file_type은 Enum 또는 str이 모두 올 수 있으므로
    getattr(file.file_type, 'value', file.file_type) 으로 안전하게 처리한다.
"""

import logging
import uuid
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
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
    # 배치 upsert: 파일 대표 노드 + 청크 노드 → code_nodes 테이블
    # ──────────────────────────────────────────────────────────
    async def save_to_pgvector(self, job_id: UUID, files: list[ParsedFile]) -> int:
        """
        임베딩이 완료된 ParsedFile 목록을 pgvector에 배치 upsert한다.

        PostgreSQL INSERT ... ON CONFLICT DO UPDATE 를 사용하므로
        동일 (job_id, path, chunk_index) 조합으로 파이프라인을 재실행해도
        IntegrityError 없이 embedding 벡터가 최신 값으로 갱신된다.

        저장 순서 (FK 참조 순서 유지):
          1. 파일당 대표 CodeNode(type="FILE", chunk_index=-1) upsert — FILE 노드 보장
          2. CHUNK CodeNode 100개 단위 배치 upsert
          3. ParsedFile.imports → FILE 노드 ID 간 Dependency upsert

        Args:
            job_id: 분석 작업 ID (AnalysisJob.id)
            files:  임베딩이 채워진 ParsedFile 목록

        Returns:
            upsert된 CHUNK CodeNode 행 수 (FILE 대표 노드 제외)
        """
        # ── 1단계: 파일 대표 노드 upsert + path→id 맵 구성
        #
        # [Deterministic UUID 정책]
        # uuid5(job_id, "FILE:{path}")로 ID를 결정론적으로 생성한다.
        # 재실행 시 동일 job_id + path에 대해 항상 같은 UUID가 생성되므로
        # ON CONFLICT 후 DB에 남는 id == file_node_map의 id가 항상 일치한다.
        # (uuid4 랜덤 방식은 재실행 시 file_node_map의 UUID ≠ DB id → FK 위반 발생)
        file_node_map: dict[str, UUID] = {}  # path → CodeNode.id

        file_node_rows: list[dict] = []
        for file in files:
            file_type_value = getattr(file.file_type, "value", file.file_type)
            # uuid5: 같은 (job_id, path)이면 재실행해도 항상 동일한 UUID 반환
            file_node_id = uuid.uuid5(job_id, f"FILE:{file.path}")
            file_node_map[file.path] = file_node_id
            file_node_rows.append({
                "id": file_node_id,
                "job_id": job_id,
                "path": file.path,
                "type": file_type_value,
                "depth": file.depth,
                "chunk_index": -1,              # -1: 대표 파일 노드 구분자
                "content": None,
                "summary": file.summary,
                "embedding": None,              # 파일 대표 노드는 임베딩 없음
                # parse 단계 metadata(is_config 등)를 보존한 채 파일 노드 표식 및 메타데이터를 덧붙인다.
                "file_metadata": {
                    **(file.metadata or {}),
                    "is_file_node": True,
                    "lines": file.lines,
                    "chars": file.chars,
                    "size": file.size,
                },
                "language": file.language,
            })

        if file_node_rows:
            await self._upsert_nodes(file_node_rows, conflict_update_cols=["summary", "language", "file_metadata"])
            logger.info(
                "[임베딩 저장] job=%s | 파일 대표 노드 %d개 upsert 완료",
                job_id, len(file_node_rows),
            )

        # ── 2단계: CHUNK 노드 100개 단위 배치 upsert
        saved = 0
        chunk_batch: list[dict] = []

        for file in files:
            for chunk in (file.chunks or []):
                # CHUNK 노드도 deterministic UUID: 재실행 시 동일 row를 upsert
                chunk_node_id = uuid.uuid5(
                    job_id, f"CHUNK:{file.path}:{chunk.chunk_index}"
                )
                chunk_batch.append({
                    "id": chunk_node_id,
                    "job_id": job_id,
                    "path": file.path,
                    "type": "CHUNK",
                    "depth": file.depth,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "summary": chunk.content,        # 현 단계에서는 원문 = 임베딩 입력
                    "embedding": chunk.embedding,    # generate_embeddings() 후 채워짐
                    "file_metadata": {
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "chunk_type": chunk.chunk_type,
                        "symbol": chunk.symbol,
                    },
                    "language": file.language,
                })

                if len(chunk_batch) >= 100:
                    await self._upsert_nodes(
                        chunk_batch,
                        conflict_update_cols=["embedding", "content", "summary", "file_metadata"],
                    )
                    saved += len(chunk_batch)
                    logger.info(
                        "[임베딩 저장] job=%s | %d개 청크 upsert 완료 (누계: %d)",
                        job_id, len(chunk_batch), saved,
                    )
                    chunk_batch = []

        if chunk_batch:
            await self._upsert_nodes(
                chunk_batch,
                conflict_update_cols=["embedding", "content", "summary", "file_metadata"],
            )
            saved += len(chunk_batch)
            logger.info(
                "[임베딩 저장] job=%s | 잔여 %d개 청크 upsert 완료 (총 %d개 청크)",
                job_id, len(chunk_batch), saved,
            )

        # ── 3단계: import 관계(Dependency) upsert
        await self._upsert_imports(job_id, files, file_node_map)

        return saved

    async def _upsert_nodes(
        self,
        rows: list[dict],
        conflict_update_cols: list[str],
    ) -> None:
        """
        code_nodes 테이블에 PostgreSQL upsert를 수행한다.

        충돌 기준: UNIQUE (job_id, path, chunk_index)
        충돌 시: conflict_update_cols의 컬럼만 최신 값으로 갱신한다.
        """
        stmt = pg_insert(CodeNode).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_code_nodes_job_path_chunk",
            set_={col: stmt.excluded[col] for col in conflict_update_cols},
        )
        await self.db.execute(stmt)
        await self.db.flush()

    async def _upsert_imports(
        self,
        job_id: UUID,
        files: list[ParsedFile],
        file_node_map: dict[str, UUID],
    ) -> int:
        """
        ParsedFile.imports를 code_dependencies 테이블에 upsert한다.

        FILE 대표 노드 ID 간에 관계를 맺는다.
        import 대상이 file_node_map에 없는 경우(외부 패키지 등)는 건너뛴다.
        """
        dep_rows: list[dict] = []
        skipped = 0

        for file in files:
            source_id = file_node_map.get(file.path)
            if source_id is None:
                continue

            for import_path in (file.imports or []):
                target_id = file_node_map.get(import_path)
                if target_id is None:
                    skipped += 1
                    continue
                if source_id == target_id:
                    continue  # 자기 자신 참조 방지

                dep_rows.append({
                    "source_id": source_id,
                    "target_id": target_id,
                    "relation": "import",
                })

        if dep_rows:
            stmt = pg_insert(Dependency).values(dep_rows)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["source_id", "target_id"],
            )
            await self.db.execute(stmt)
            await self.db.flush()

        logger.info(
            "[의존성 저장] job=%s | %d개 Dependency upsert (외부 참조 %d건 스킵)",
            job_id, len(dep_rows), skipped,
        )
        return len(dep_rows)

    # ──────────────────────────────────────────────────────────
    # 기존 임베딩 삭제 (force_reembed=True 시 호출)
    # ──────────────────────────────────────────────────────────
    async def delete_by_job(self, job_id: UUID) -> int:
        """
        특정 분석 작업의 모든 CodeNode(임베딩)를 삭제한다.

        force_reembed=True 시 service에서 먼저 이 메서드를 호출한 뒤
        save_to_pgvector()로 재삽입한다.
        ON DELETE CASCADE 설정으로 code_dependencies도 연쇄 삭제된다.

        Note: force_reembed=False 재실행 시에도 save_to_pgvector의 upsert가
              충돌 없이 동작하므로 반드시 이 메서드를 호출할 필요는 없다.
        """
        result = await self.db.execute(
            delete(CodeNode).where(CodeNode.job_id == job_id)
        )
        deleted = int(getattr(result, "rowcount", 0))
        logger.info(
            "[임베딩 삭제] job=%s | %d개 CodeNode 삭제 완료 (Dependency 연쇄 삭제 포함)",
            job_id, deleted,
        )
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
    # 벡터 검색 (RAG 답변용)
    # ──────────────────────────────────────────────────────────
    async def has_embeddings(self, job_id: UUID) -> bool:
        """벡터 검색이 가능한 상태인지 — 임베딩이 채워진 CHUNK 노드가 있는지 확인한다."""
        result = await self.db.execute(
            select(CodeNode.id)
            .where(
                CodeNode.job_id == job_id,
                CodeNode.type == "CHUNK",
                CodeNode.embedding.is_not(None),
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def similarity_search(
        self, job_id: UUID, query_vector: list[float], k: int = 5
    ) -> list[tuple[CodeNode, float]]:
        """job 범위 내 CHUNK 노드를 쿼리 벡터와 코사인 유사도 순으로 k개 반환한다.

        반환: (CodeNode, distance) 튜플 목록. distance가 작을수록 유사하다.
        """
        distance = CodeNode.embedding.cosine_distance(query_vector)
        result = await self.db.execute(
            select(CodeNode, distance.label("distance"))
            .where(
                CodeNode.job_id == job_id,
                CodeNode.type == "CHUNK",
                CodeNode.embedding.is_not(None),
            )
            .order_by(distance)
            .limit(k)
        )
        return [(row[0], float(row[1])) for row in result.all()]

    # ──────────────────────────────────────────────────────────
    # 외부 호출용 의존성 직접 저장
    # ──────────────────────────────────────────────────────────
    async def save_dependencies(self, deps: list[tuple[UUID, UUID, str]]) -> int:
        """
        파일 간 import 관계를 code_dependencies 테이블에 직접 저장한다.

        Note: 일반적으로 save_to_pgvector()가 내부적으로 import 관계를 처리하므로
              이 메서드는 외부에서 ID 쌍을 직접 알고 있는 경우에만 사용한다.
        """
        if not deps:
            return 0
        rows = [
            {"source_id": src, "target_id": tgt, "relation": rel}
            for src, tgt, rel in deps
        ]
        stmt = pg_insert(Dependency).values(rows)
        stmt = stmt.on_conflict_do_nothing(index_elements=["source_id", "target_id"])
        await self.db.execute(stmt)
        await self.db.flush()
        logger.info("[의존성 저장] %d개 Dependency upsert 완료 (직접 호출)", len(rows))
        return len(rows)

    # ──────────────────────────────────────────────────────────
    # 파일 컨텐츠 복구 조회 (Issue #226: 로컬 FS 누락 시 DB fallback)
    # ──────────────────────────────────────────────────────────
    async def get_file_content(self, job_id: UUID, path: str) -> str | None:
        """
        로컬 워크스페이스에서 파일을 읽지 못했을 때 사용하는 DB 기반 복구 조회.

        우선순위:
          1. FILE 대표 노드(chunk_index=-1)의 content가 존재하면 그대로 반환한다.
          2. FILE content가 None이면 CHUNK 노드들의 content를 chunk_index 순으로
             이어 붙여 best-effort로 재구성한다. (AST 청크 기반이라 원본과
             완전히 동일하지 않을 수 있으나, 404 대신 부분 복구로 가용성을 높인다.)

        하나도 없으면 None을 반환한다.
        """
        ## 1차: FILE 대표 노드 content
        file_stmt = select(CodeNode.content).where(
            CodeNode.job_id == job_id,
            CodeNode.path == path,
            CodeNode.type == "FILE",
        )
        file_result = await self.db.execute(file_stmt)
        file_content = file_result.scalars().first()
        if file_content is not None:
            return file_content

        ## 2차: CHUNK 노드 content를 순서대로 재구성
        chunk_stmt = (
            select(CodeNode.content)
            .where(
                CodeNode.job_id == job_id,
                CodeNode.path == path,
                CodeNode.type == "CHUNK",
            )
            .order_by(CodeNode.chunk_index)
        )
        chunk_result = await self.db.execute(chunk_stmt)
        chunks = [c for c in chunk_result.scalars().all() if c]
        if chunks:
            return "\n\n".join(chunks)

        return None
