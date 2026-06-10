# app/db/models.py
from sqlalchemy import String, Integer, DateTime, Text, func, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.db.database import Base
import uuid
import datetime

class Repo(Base):
    __tablename__ = "repos"

    id:         Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    github_url: Mapped[str]       = mapped_column(String, unique=True, nullable=False)
    status:     Mapped[str]       = mapped_column(String, default="pending")
    indexed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Chunk(Base):
    __tablename__ = "chunks"

    id:             Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    repo_id:        Mapped[uuid.UUID] = mapped_column(ForeignKey("repos.id"), index=True)
    file_path:      Mapped[str]       = mapped_column(Text, nullable=False)
    language:       Mapped[str]       = mapped_column(String(50))
    chunk_type:     Mapped[str]       = mapped_column(String(50))
    name:           Mapped[str]       = mapped_column(Text, nullable=True)
    start_line:     Mapped[int]       = mapped_column(Integer)
    end_line:       Mapped[int]       = mapped_column(Integer)
    content:        Mapped[str]       = mapped_column(Text, nullable=False)
    context_prefix: Mapped[str]       = mapped_column(Text, nullable=False)
    embedding:      Mapped[list[float]] = mapped_column(Vector(1536), nullable=True)
    created_at:     Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("repo_id", "file_path", "start_line", name="uq_chunk_location"),
        {"schema": None},
    )