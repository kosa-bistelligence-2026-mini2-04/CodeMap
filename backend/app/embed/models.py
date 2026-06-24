"""
RAG EMBED 도메인 데이터베이스 엔티티 모듈

RAG_EMBED_SPEC.md (B-201/B-301)에 따라 코드 청크와 임베딩 벡터를 저장하는
PostgreSQL 테이블을 SQLAlchemy ORM으로 정의한다.

DB 테이블 구성:
  source_files  — 파싱된 원본 파일 메타데이터 (1건 = 1 파일)
  code_chunks   — AST 청킹 결과 + 임베딩 벡터 (1건 = 1 청크)
  file_dependencies — 파일 간 import 관계 그래프

test 계약:
  test_embed_models.py → CodeNode, Dependency 모델 컬럼·타입 검증
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base

try:
    from pgvector.sqlalchemy import Vector  # type: ignore[import]
except ImportError:  # pgvector 패키지 미설치 환경(CI 등)에서는 fallback
    from sqlalchemy import PickleType as Vector  # type: ignore[assignment]


# ──────────────────────────────────────────────────────────────
# CodeNode — source_files + code_chunks 를 단일 ORM 뷰로 추상화
#
# RAG_EMBED_SPEC.md B-301 스키마:
#   source_files: id, repo_id, file_path, raw_code, file_summary
#   code_chunks : id, file_id, chunk_summary, embedding_vector,
#                 start_line, end_line, symbol, language
#
# test_embed_models.py가 요구하는 컬럼:
#   id, job_id, path, type, depth, content, summary, embedding, file_metadata
# ──────────────────────────────────────────────────────────────
class CodeNode(Base):
    """
    코드 청크 + 파일 메타데이터를 통합한 RAG 임베딩 저장 엔티티

    RAG_EMBED_SPEC.md B-201/B-301에 따라:
    - chunk_summary를 OpenAI text-embedding-3-large(dimensions=1536)로 벡터화
    - HNSW 인덱스로 코사인 유사도 검색 지원
    - file_metadata(JSONB)로 start_line, end_line, symbol, language 저장
    """

    __tablename__ = "code_nodes"

    __table_args__ = (
        # 같은 repo·경로·청크 인덱스 조합의 중복 삽입 방지
        UniqueConstraint("job_id", "path", "chunk_index", name="uq_code_nodes_job_path_chunk"),
        Index("idx_code_nodes_job_id", "job_id"),
        Index("idx_code_nodes_language", "language"),
        # RAG EMBED: 코사인 유사도 고속 검색을 위한 HNSW 인덱스 정의
        Index(
            "idx_code_nodes_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    # ── 기본 식별자 ──────────────────────────────────────────
    # 청크 고유 ID
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # 분석 작업 ID (= repo_id, AnalysisJob.id 참조)
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, comment="AnalysisJob.id (분석 작업 식별자)"
    )

    # ── 파일 위치 메타데이터 ──────────────────────────────────
    # 저장소 루트 기준 상대 경로 (예: src/main.py)
    path: Mapped[str] = mapped_column(
        Text, nullable=False, comment="저장소 루트 기준 상대 파일 경로"
    )

    # 노드 타입: FILE | DIRECTORY | CHUNK (AST 청킹 단위)
    type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="CHUNK", comment="FILE / DIRECTORY / CHUNK"
    )

    # 디렉토리 트리 깊이 (루트 = 0)
    depth: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="디렉토리 트리 깊이 (루트=0)"
    )

    # 파일 내 청크 순번 (0-based, AST 청킹 단위)
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="파일 내 청크 순번 (0-based)"
    )

    # ── 청크 원문 및 요약 ───────────────────────────────────
    # 임베딩 대상 원문 텍스트 (AST 청킹 결과)
    content: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="AST 청킹 원문 (임베딩 대상)"
    )

    # LLM이 생성한 청크 요약 또는 원문 그대로 (임베딩 입력으로 사용)
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="임베딩 입력 텍스트 (요약 또는 원문)"
    )

    # ── 임베딩 벡터 ─────────────────────────────────────────
    # text-embedding-3-large, dimensions=1536 (EMBEDDING_MODEL_DECISION.md)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(1536), nullable=True, comment="OpenAI text-embedding-3-large 벡터 (dim=1536)"
    )

    # ── 코드 메타데이터 (JSONB) ─────────────────────────────
    # {start_line, end_line, symbol, language, chunk_type} 등 자유 확장 가능
    file_metadata: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="코드 메타데이터 (start_line, end_line, symbol, language 등)"
    )

    # ── 언어 (인덱스용 별도 컬럼) ───────────────────────────
    language: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="프로그래밍 언어 (python, typescript 등)"
    )

    # ── 타임스탬프 ──────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ──────────────────────────────────────────────────────────────
# Dependency — 파일 간 import 관계 그래프
#
# RAG_EMBED_SPEC.md B-301:
#   file_dependencies: id, source_file_id, target_file_path
#
# test_embed_models.py가 요구하는 복합 PK: source_id, target_id
# ──────────────────────────────────────────────────────────────
class Dependency(Base):
    """
    파일 간 import/의존 관계 엔티티

    source_id → target_id 방향으로 A 파일이 B 파일을 import함을 표현.
    복합 PK(source_id, target_id)로 중복 관계 삽입을 방지한다.
    """

    __tablename__ = "code_dependencies"

    # source_id + target_id 복합 PK (test_embed_models.py 계약)
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_nodes.id", ondelete="CASCADE"),
        primary_key=True,
        comment="import하는 파일의 CodeNode.id",
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("code_nodes.id", ondelete="CASCADE"),
        primary_key=True,
        comment="import되는 파일의 CodeNode.id",
    )

    # 관계 레이블 (예: "import", "dynamic_import", "re_export")
    relation: Mapped[str] = mapped_column(
        String(50), nullable=False, default="import", comment="의존 관계 종류"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
