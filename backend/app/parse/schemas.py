"""RAG 파이프라인 공유 DTO (PARSE/EMBED 공용).

PARSE 모듈이 산출하고 EMBED 모듈이 소비하는 데이터 계약을 정의한다.
- 스키마 계약 테스트: tests/unit/test_parse_schemas.py
- 공유 fixture: tests/fixtures/mock_parse_result.py
- 명세: docs/03_Specifications/02_RAG/spec/RAG_PARSE_SPEC.md
         docs/03_Specifications/02_RAG/spec/RAG_EMBED_SPEC.md
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, JsonValue


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
    lines: int = Field(default=0, ge=0, description="전체 라인 수")
    chars: int = Field(default=0, ge=0, description="글자 수 (len(content))")
    size: int = Field(default=0, ge=0, description="파일 크기(bytes)")
    summary: str | None = Field(default=None, description="Bottom-up 요약 (RAG-PARSE-B-209)")
    chunks: list[CodeChunk] = Field(default_factory=list, description="AST 청크 목록")
    imports: list[str] = Field(
        default_factory=list,
        description="import 대상 (저장소 상대 경로로 정규화; RAG-PARSE-B-208)",
    )
    metadata: dict[str, JsonValue] | None = Field(
        default=None, description="부가 메타데이터 (예: is_config; RAG-PARSE-B-204)"
    )

    # RAG-EMBED-B-201: 언어 정보 (임베딩 메타데이터 및 인덱스 필터링용)
    language: str | None = Field(
        default=None,
        description="프로그래밍 언어 (python, typescript 등; RAG-EMBED-B-201 저장 메타데이터)",
    )


class RunCommandSet(BaseModel):
    """설치/실행/빌드 명령 응답 계약 (RAG-PARSE-B-205/API-001)."""

    install: str = Field(default="", description="의존성 설치 명령어")
    run: str = Field(default="", description="프로젝트 실행 명령어")
    build: str | None = Field(default=None, description="빌드 명령어 (없으면 None)")


class TechStackItem(BaseModel):
    """기술 스택 상세 항목 (RAG-PARSE-B-206/API-004)."""

    name: str = Field(description="기술명")
    version: str | None = Field(default=None, description="탐지된 버전")
    category: str = Field(default="library", description="language/framework/database/infra 등")
    source: str | None = Field(default=None, description="탐지 출처 파일 경로")


class LanguageCompositionItem(BaseModel):
    """실제 소스 라인 기준 언어 구성 항목."""

    language: str = Field(description="언어 또는 설정 유형")
    lines: int = Field(default=0, ge=0, description="해당 언어/유형의 총 라인 수")
    percentage: float = Field(default=0.0, ge=0.0, description="전체 라인 대비 비율")


class EntryPointItem(BaseModel):
    """진입점 상세 항목 (RAG-PARSE-B-203/API-003)."""

    path: str = Field(description="진입점 파일 경로")
    type: str | None = Field(default=None, description="backend/frontend/config 등 진입점 유형")
    reason: str | None = Field(default=None, description="진입점으로 판단한 근거")


class FolderSummary(BaseModel):
    """폴더 단위 요약 항목 (RAG-PARSE-B-209/API-006)."""

    path: str = Field(description="폴더 경로")
    summary: str = Field(description="폴더 역할 요약")


class FileSummary(BaseModel):
    """파일 단위 요약 항목 (RAG-PARSE-B-209/API-006)."""

    path: str = Field(description="파일 경로")
    summary: str = Field(description="파일 역할 요약")


class FileMapItem(BaseModel):
    """코드맵 파일 단위 항목 (RAG-PARSE-B-207/208/API-005)."""

    path: str = Field(description="파일 경로")
    language: str | None = Field(default=None, description="프로그래밍 언어")
    chunk_count: int = Field(default=0, ge=0, description="AST 청크 수")
    lines: int = Field(default=0, ge=0, description="전체 라인 수")
    size: int = Field(default=0, ge=0, description="파일 크기(bytes)")
    imports: list[str] = Field(default_factory=list, description="이 파일이 참조하는 파일 경로 목록")
    imported_by: list[str] = Field(default_factory=list, description="이 파일을 참조하는 파일 경로 목록")
    risk_score: int | None = Field(default=None, description="위험도 점수 (0-100)")


class HeatmapItem(BaseModel):
    """복잡도/위험도 히트맵 항목 (RAG-PARSE-API-005)."""

    path: str = Field(description="파일 경로")
    score: int = Field(default=0, ge=0, le=100, description="복잡도/위험도 점수")


class ParseResult(BaseModel):
    """PARSE 파이프라인 최종 산출물 (RAG-PARSE-B-101 응답의 기반)."""

    job_id: UUID = Field(description="분석 작업 ID (= repo_id)")
    repo_name: str = Field(description="저장소 이름")
    owner: str = Field(description="저장소 소유자")
    branch: str = Field(description="분석 대상 브랜치")
    readme_summary: str | None = Field(default=None, description="README 요약 (RAG-PARSE-B-201)")
    tech_stack: list[str] = Field(default_factory=list, description="탐지된 기술 스택 (RAG-PARSE-B-206)")
    tech_stack_details: list[TechStackItem] = Field(
        default_factory=list,
        description="객체형 기술 스택 상세 항목 (RAG-PARSE-API-004)",
    )
    language_composition: list[LanguageCompositionItem] = Field(
        default_factory=list,
        description="실제 소스 라인 기준 언어 구성",
    )
    run_commands: list[str] = Field(default_factory=list, description="실행 명령 (RAG-PARSE-B-205)")
    run_command_details: RunCommandSet = Field(
        default_factory=RunCommandSet,
        description="설치/실행/빌드 명령 구조화 응답",
    )
    entry_points: list[str] = Field(default_factory=list, description="진입점 경로 (RAG-PARSE-B-203)")
    entry_point_details: list[EntryPointItem] = Field(
        default_factory=list,
        description="진입점 상세 항목 (RAG-PARSE-API-003)",
    )
    config_files: list[str] = Field(default_factory=list, description="탐지된 설정 파일 경로 목록")
    master_summary: str | None = Field(default=None, description="프로젝트 전체 요약 (RAG-PARSE-B-209)")
    folder_summaries: list[FolderSummary] = Field(
        default_factory=list,
        description="폴더 단위 요약 목록",
    )
    file_summaries: list[FileSummary] = Field(
        default_factory=list,
        description="파일 단위 요약 목록",
    )
    file_map: list[FileMapItem] = Field(default_factory=list, description="코드맵 파일 단위 항목")
    heatmap: list[HeatmapItem] = Field(default_factory=list, description="코드맵 히트맵 항목")
    directory_tree: str | None = Field(default=None, description="폴더 트리 텍스트")
    files: list[ParsedFile] = Field(default_factory=list, description="파싱된 파일/디렉토리 노드")


# ──────────────────────────────────────────────
# FileContentResponse / FileSymbolItem — G1-A 파일 조회 API 계약
# ──────────────────────────────────────────────
class FileSymbolItem(BaseModel):
    """파일 내 심볼 항목 (함수·클래스·모듈 단위)."""

    name: str = Field(description="심볼명 (함수·클래스·모듈 이름)")
    kind: str = Field(description="심볼 종류 (function/class/module/other)")
    startLine: int = Field(description="시작 라인 (1-base)")
    endLine: int = Field(description="끝 라인 (1-base)")


class FileContentResponse(BaseModel):
    """GET /api/parse/{repo_id}/file 응답 계약 (G1-A)."""

    path: str = Field(description="저장소 루트 기준 상대 경로")
    language: str | None = Field(default=None, description="프로그래밍 언어")
    lineCount: int = Field(description="전체 라인 수")
    content: str = Field(description="파일 원문")
    symbols: list[FileSymbolItem] = Field(
        default_factory=list, description="파일 내 심볼 목록"
    )


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
