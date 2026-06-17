from __future__ import annotations

from datetime import datetime
import uuid

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    ForeignKey,
    JSON,
    Index,
    create_engine,
)
from sqlalchemy.dialects.postgresql import UUID, VECTOR
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# ------------------------------------------------------------
# User Table
# ------------------------------------------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    repositories = relationship("Repository", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"

# ------------------------------------------------------------
# Repository Table
# ------------------------------------------------------------
class Repository(Base):
    __tablename__ = "repositories"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    url = Column(Text, nullable=False)
    branch = Column(String(100), nullable=False, server_default="main")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="repositories")
    code_nodes = relationship("CodeNode", back_populates="repository", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Repository id={self.id} url={self.url}>"

# ------------------------------------------------------------
# CodeNode Table – hierarchical tree of files/folders
# ------------------------------------------------------------
class CodeNode(Base):
    __tablename__ = "code_nodes"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("code_nodes.id", ondelete="CASCADE"), nullable=True)
    path = Column(Text, nullable=False)
    type = Column(String(20), nullable=False)  # FILE or DIRECTORY
    depth = Column(Integer, nullable=False, default=0)
    content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    embedding = Column(VECTOR(1536), nullable=True)  # pgvector column
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    repository = relationship("Repository", back_populates="code_nodes")
    children = relationship(
        "CodeNode",
        backref="parent",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    outgoing_dependencies = relationship(
        "Dependency",
        foreign_keys="Dependency.source_id",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    incoming_dependencies = relationship(
        "Dependency",
        foreign_keys="Dependency.target_id",
        back_populates="target",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_code_nodes_repo_path", "repo_id", "path"),
        Index("ix_code_nodes_vector", "embedding", postgresql_using="hnsw"),
    )

    def __repr__(self) -> str:
        return f"<CodeNode id={self.id} path={self.path}>"

# ------------------------------------------------------------
# Dependency Table – many‑to‑many relationship between CodeNode entries
# ------------------------------------------------------------
class Dependency(Base):
    __tablename__ = "dependencies"
    source_id = Column(UUID(as_uuid=True), ForeignKey("code_nodes.id", ondelete="CASCADE"), primary_key=True)
    target_id = Column(UUID(as_uuid=True), ForeignKey("code_nodes.id", ondelete="CASCADE"), primary_key=True)
    type = Column(String(50), nullable=False, server_default="import")

    # Relationships
    source = relationship("CodeNode", foreign_keys=[source_id], back_populates="outgoing_dependencies")
    target = relationship("CodeNode", foreign_keys=[target_id], back_populates="incoming_dependencies")

    __table_args__ = (Index("ix_dependencies_target", "target_id"),)

    def __repr__(self) -> str:
        return f"<Dependency {self.source_id} -> {self.target_id} type={self.type}>"

# ------------------------------------------------------------
# Engine creation helper (example – replace with your config)
# ------------------------------------------------------------
def get_engine(database_url: str = "postgresql+psycopg2://codemap:codemap@kosa165.iptime.org:50004/codemap"):
    """Create a SQLAlchemy engine.
    The default URL points to the remote DB we just configured.
    Adjust as needed for local development.
    """
    return create_engine(database_url, echo=False)

# Export Base for Alembic migrations
__all__ = ["Base", "User", "Repository", "CodeNode", "Dependency", "get_engine"]
