"""Notion RAG 인터페이스 명세와 동일한 팀 간 공유 fixture."""

from uuid import UUID


JOB_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def build_mock_parse_result():
    """스키마 구현 후 PARSE → EMBED 통합 테스트에서 사용하는 고정 결과."""
    from app.parse.schemas import (
        CodeChunk,
        EntryPointItem,
        FileSummary,
        FileMapItem,
        HeatmapItem,
        LanguageCompositionItem,
        ParseResult,
        ParsedFile,
        RunCommandSet,
        TechStackItem,
    )

    return ParseResult(
        job_id=JOB_ID,
        repo_name="CodeMap",
        owner="kosa-bistelligence-2026-mini2-04",
        branch="main",
        readme_summary="GitHub 저장소 분석 서비스",
        tech_stack=["FastAPI", "PostgreSQL", "pgvector"],
        tech_stack_details=[
            TechStackItem(
                name="FastAPI",
                version="0.115.0",
                category="framework",
                source="backend/requirements.txt",
            ),
            TechStackItem(name="PostgreSQL", category="database", source="docker-compose.yml"),
        ],
        language_composition=[
            LanguageCompositionItem(language="Python", lines=2, percentage=100.0),
        ],
        run_commands=["uvicorn app.main:app --reload"],
        run_command_details=RunCommandSet(run="uvicorn app.main:app --reload"),
        entry_points=["backend/app/main.py"],
        entry_point_details=[
            EntryPointItem(path="backend/app/main.py", type="backend", reason="FastAPI app module"),
        ],
        config_files=["backend/requirements.txt"],
        master_summary="CodeMap RAG 분석 결과",
        folder_summaries=[
            {"path": "backend/app", "summary": "FastAPI 애플리케이션 코드"},
        ],
        file_summaries=[
            FileSummary(path="backend/app/main.py", summary="FastAPI 앱 진입점"),
        ],
        file_map=[
            FileMapItem(path="backend/app/main.py", language="Python", chunk_count=1),
        ],
        heatmap=[
            HeatmapItem(path="backend/app/main.py", score=12),
        ],
        directory_tree="CodeMap/\n└── backend/",
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
