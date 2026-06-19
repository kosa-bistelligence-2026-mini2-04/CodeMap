"""Notion RAG 인터페이스 명세와 동일한 팀 간 공유 fixture."""

from uuid import UUID


JOB_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def build_mock_parse_result():
    """스키마 구현 후 PARSE → EMBED 통합 테스트에서 사용하는 고정 결과."""
    from app.parse.schemas import CodeChunk, ParsedFile, ParseResult

    return ParseResult(
        job_id=JOB_ID,
        repo_name="CodeMap",
        owner="kosa-bistelligence-2026-mini2-04",
        branch="main",
        readme_summary="GitHub 저장소 분석 서비스",
        tech_stack=["FastAPI", "PostgreSQL", "pgvector"],
        run_commands=["uvicorn app.main:app --reload"],
        entry_points=["backend/app/main.py"],
        master_summary="CodeMap RAG 분석 결과",
        files=[
            ParsedFile(
                path="backend/app/main.py",
                file_type="FILE",
                depth=2,
                content="from fastapi import FastAPI\napp = FastAPI()",
                summary="FastAPI 앱 진입점",
                chunks=[
                    CodeChunk(
                        chunk_index=0,
                        content="from fastapi import FastAPI\napp = FastAPI()",
                        start_line=1,
                        end_line=2,
                        chunk_type="module",
                    )
                ],
                imports=[],
                metadata={"is_config": False},
            )
        ],
    )
