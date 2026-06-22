"""RAG 파이프라인 공유 DTO (PARSE/EMBED 공용).

PARSE 모듈이 산출하고 EMBED 모듈이 소비하는 데이터 계약을 정의한다.
- 스키마 계약 테스트: tests/unit/test_parse_schemas.py
- 공유 fixture: tests/fixtures/mock_parse_result.py
- 명세: docs/03_Specifications/02_RAG/spec/RAG_PARSE_SPEC.md
         docs/03_Specifications/02_RAG/spec/RAG_EMBED_SPEC.md
"""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# AST 기반 청킹 결과 유형 (RAG-PARSE-B-207)
ChunkType = Literal["function", "class", "module", "other"]

# 파일 트리 노드 구분 (RAG-PARSE-B-202)
FileType = Literal["FILE", "DIRECTORY"]


class CodeChunk(BaseModel):
    """AST 청킹 단위. 임베딩 1건에 대응한다 (RAG-PARSE-B-207)."""

    chunk_index: int = Field(description="파일 내 청크 순번 (0부터)")
    content: str = Field(description="청크 원문")
    start_line: int = Field(description="시작 라인 (1-base)")
    end_line: int = Field(description="끝 라인 (1-base, start_line 이상)")
    chunk_type: ChunkType = Field(default="other", description="청크 유형")

    # RAG-EMBED-B-201: 임베딩 생성 후 채워지는 벡터 (dim=1536)
    symbol: str | None = Field(
        default=None,
        description="함수·클래스·모듈 심볼명 (검색 필터링용; RAG-EMBED-B-201)",
    )
    embedding: list[float] | None = Field(
        default=None,
        description="OpenAI text-embedding-3-large 벡터 (dim=1536, 생성 후 채워짐; RAG-EMBED-B-201)",
    )


class ParsedFile(BaseModel):
    """파싱된 파일 또는 디렉토리 노드 (RAG-PARSE-B-202)."""

    path: str = Field(description="저장소 루트 기준 상대 경로")
    file_type: FileType = Field(description="FILE 또는 DIRECTORY")
    depth: int = Field(description="루트로부터의 깊이")
    content: str | None = Field(default=None, description="파일 원문 (디렉토리는 None)")
    summary: str | None = Field(default=None, description="Bottom-up 요약 (RAG-PARSE-B-209)")
    chunks: list[CodeChunk] = Field(default_factory=list, description="AST 청크 목록")
    imports: list[str] = Field(
        default_factory=list,
        description="import 대상 (저장소 상대 경로로 정규화; RAG-PARSE-B-208)",
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="부가 메타데이터 (예: is_config; RAG-PARSE-B-204)"
    )

    # RAG-EMBED-B-201: 언어 정보 (임베딩 메타데이터 및 인덱스 필터링용)
    language: str | None = Field(
        default=None,
        description="프로그래밍 언어 (python, typescript 등; RAG-EMBED-B-201 저장 메타데이터)",
    )


class ParseResult(BaseModel):
    """PARSE 파이프라인 최종 산출물 (RAG-PARSE-B-101 응답의 기반)."""

    job_id: UUID = Field(description="분석 작업 ID (= repo_id)")
    repo_name: str = Field(description="저장소 이름")
    owner: str = Field(description="저장소 소유자")
    branch: str = Field(description="분석 대상 브랜치")
    readme_summary: str | None = Field(default=None, description="README 요약 (RAG-PARSE-B-201)")
    tech_stack: list[str] = Field(default_factory=list, description="탐지된 기술 스택 (RAG-PARSE-B-206)")
    run_commands: list[str] = Field(default_factory=list, description="실행 명령 (RAG-PARSE-B-205)")
    entry_points: list[str] = Field(default_factory=list, description="진입점 경로 (RAG-PARSE-B-203)")
    master_summary: str | None = Field(default=None, description="프로젝트 전체 요약 (RAG-PARSE-B-209)")
    files: list[ParsedFile] = Field(default_factory=list, description="파싱된 파일/디렉토리 노드")


class EmbedRequest(BaseModel):
    """PARSE → EMBED 인계 요청 (RAG-EMBED-B-201)."""

    job_id: UUID = Field(description="분석 작업 ID")
    files: list[ParsedFile] = Field(default_factory=list, description="임베딩 대상 파일/청크")

    # force_reembed=True 시 기존 임베딩 삭제 후 재생성 (RAG_EMBED_SPEC.md)
    force_reembed: bool = Field(
        default=False,
        description="기존 임베딩 삭제 후 재생성 여부 (RAG-EMBED-B-301 forceReembed 파라미터)",
    )


class EmbedResult(BaseModel):
    """EMBED 처리 결과. 부분 실패를 추적한다 (RAG-EMBED-B-301)."""

    job_id: UUID = Field(description="분석 작업 ID")
    total_files: int = Field(default=0, description="처리 대상 파일 수")
    total_chunks: int = Field(default=0, description="임베딩 생성 청크 수")
    saved_chunks: int = Field(default=0, description="pgvector에 저장된 청크 수")
    failed_paths: list[str] = Field(default_factory=list, description="임베딩 실패 파일 경로")
