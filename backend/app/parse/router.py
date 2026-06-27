from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.database import get_db
from app.infra.auth import get_current_user_optional
from app.common.access import can_access_job
from app.common.exceptions import ParseResultNotFoundError, RepositoryNotFoundError, JobNotFoundError
from app.embed.models import CodeNode
from app.parse.report import (
    normalize_run_commands,
    report_config_files,
    report_directory_tree,
    report_entry_point_details,
    report_entry_points,
    report_file_map,
    report_file_summaries,
    report_files,
    report_folder_summaries,
    report_heatmap,
    report_master_summary,
    report_readme_summary,
    report_tech_stack,
    report_tech_stack_details,
)
from app.parse.schemas import FileContentResponse, FileSymbolItem
from app.repo.repository import AnalysisJobRepository


router = APIRouter(prefix="/api/parse/analysis", tags=["RAG Parse"])


# ──────────────────────────────────────────────
# file_router — G1-A: 파일 원문 + 심볼 조회 API
# ──────────────────────────────────────────────
file_router = APIRouter(prefix="/api/parse", tags=["RAG Parse"])


def _build_directory_tree(files: list[dict], repo_name: str) -> str:
    tree_lines = [f"{repo_name}/"]
    paths = sorted([item.get("path") for item in files if isinstance(item, dict) and item.get("path")])

    tree_dict = {}
    for path in paths:
        current = tree_dict
        for part in path.split("/"):
            current = current.setdefault(part, {})

    def render_tree(node, prefix=""):
        lines = []
        keys = list(node.keys())
        for index, key in enumerate(keys):
            is_last = index == len(keys) - 1
            connector = "└── " if is_last else "├── "
            suffix = "/" if node[key] else ""
            lines.append(f"{prefix}{connector}{key}{suffix}")

            extension_prefix = "    " if is_last else "│   "
            lines.extend(render_tree(node[key], prefix + extension_prefix))
        return lines

    tree_lines.extend(render_tree(tree_dict))
    return "\n".join(tree_lines)





async def _get_report_json(repo_id: UUID, db: AsyncSession) -> tuple[object, dict]:
    repo = AnalysisJobRepository(db)
    job = await repo.get_job_by_id(repo_id)
    if not job:
        raise RepositoryNotFoundError()
    if not job.report_json:
        raise ParseResultNotFoundError()
    return job, job.report_json


def _camel_file_map(items: list[dict]) -> list[dict]:
    return [
        {
            "path": item.get("path"),
            "language": item.get("language"),
            "chunkCount": item.get("chunk_count", item.get("chunkCount", 0)),
            "lines": item.get("lines", 0),
            "size": item.get("size", 0),
            "imports": item.get("imports", []),
            "importedBy": item.get("imported_by", item.get("importedBy", [])),
            "riskScore": item.get("risk_score", item.get("riskScore")),
        }
        for item in items
        if item.get("path")
    ]


@router.get("/{repo_id}")
async def get_parse_analysis(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    job, rj = await _get_report_json(repo_id, db)
    files = report_files(rj)
    run_commands = normalize_run_commands(rj.get("run_command_details") or rj.get("run_commands"))

    return {
        "code": 200,
        "message": "success",
        "data": {
            "repoId": job.id,
            "repoName": job.repo_name,
            "techStack": report_tech_stack(rj),
            "entryPoints": report_entry_points(rj),
            "directoryTree": report_directory_tree(rj) or _build_directory_tree(files, job.repo_name),
            "runCommands": run_commands.model_dump(),
            "configFiles": report_config_files(files),
            "readmeSummary": report_readme_summary(rj),
            "files": files,
            "fileCount": len(files),
            "analyzedAt": job.updated_at.isoformat() if job.updated_at else None,
        },
    }


@router.get("/{repo_id}/readme")
async def get_parse_readme(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    job, rj = await _get_report_json(repo_id, db)
    summary = report_readme_summary(rj)
    return {
        "code": 200,
        "message": "success",
        "data": {
            "repoId": job.id,
            "projectPurpose": summary,
            "coreFeatures": rj.get("core_features", []),
            "targetAudience": rj.get("target_audience", ""),
            "rawReadme": rj.get("raw_readme", ""),
        },
    }


@router.get("/{repo_id}/tree")
async def get_parse_tree(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    job, rj = await _get_report_json(repo_id, db)
    files = report_files(rj)
    return {
        "code": 200,
        "message": "success",
        "data": {
            "repoId": job.id,
            "directoryTree": report_directory_tree(rj) or _build_directory_tree(files, job.repo_name),
            "entryPoints": report_entry_point_details(rj),
            "configFiles": report_config_files(files),
            "totalFiles": len(files),
        },
    }


@router.get("/{repo_id}/stack")
async def get_parse_stack(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    job, rj = await _get_report_json(repo_id, db)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "repoId": job.id,
            "techStack": report_tech_stack_details(rj),
            "languageComposition": rj.get("language_composition") or [],
            "runCommands": normalize_run_commands(
                rj.get("run_command_details") or rj.get("run_commands")
            ).model_dump(),
        },
    }


@router.get("/{repo_id}/codemap")
async def get_parse_codemap(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    job, rj = await _get_report_json(repo_id, db)
    return {
        "code": 200,
        "message": "success",
        "data": {
            "repoId": job.id,
            "fileMap": _camel_file_map(report_file_map(rj)),
            "heatmap": report_heatmap(rj),
        },
    }


@router.get("/{repo_id}/summary")
async def get_parse_summary(
    repo_id: UUID,
    level: str = "all",
    db: AsyncSession = Depends(get_db),
):
    job, rj = await _get_report_json(repo_id, db)
    include_project = level in {"all", "project"}
    include_folder = level in {"all", "folder"}
    include_file = level in {"all", "file"}
    return {
        "code": 200,
        "message": "success",
        "data": {
            "repoId": job.id,
            "projectSummary": report_master_summary(rj) if include_project else "",
            "folderSummaries": report_folder_summaries(rj) if include_folder else [],
            "fileSummaries": report_file_summaries(rj) if include_file else [],
        },
    }


@file_router.get("/{repo_id}/file", response_model=FileContentResponse)
async def get_file_content(
    repo_id: UUID,
    path: str = Query(..., description="저장소 루트 기준 상대 경로"),
    current_user: Annotated[dict | None, Depends(get_current_user_optional)] = None,
    db: AsyncSession = Depends(get_db),
) -> FileContentResponse:
    """파일 원문과 심볼 목록을 반환한다 (G1-A).

    - 접근 제어: can_access_job 통과 못 하면 404 은닉.
    - 파일 원문: type='FILE' CodeNode의 content.
    - 심볼: type='CHUNK' CodeNode의 file_metadata에서 추출.
    - 디스크 접근 없음 — DB content만 사용.
    """
    job_repo = AnalysisJobRepository(db)
    job = await job_repo.get_job_by_id(repo_id)

    current_user_id = UUID(current_user["sub"]) if current_user and "sub" in current_user else None
    if not job or not await can_access_job(db, job, current_user_id):
        raise JobNotFoundError()

    ## FILE 노드에서 원문·언어 조회
    file_result = await db.execute(
        select(CodeNode).where(
            CodeNode.job_id == repo_id,
            CodeNode.path == path,
            CodeNode.type == "FILE",
        )
    )
    file_node = file_result.scalar_one_or_none()
    if file_node is None or file_node.content is None:
        raise JobNotFoundError(f"파일을 찾을 수 없습니다: {path}")

    content: str = file_node.content
    language: str | None = file_node.language or (
        (file_node.file_metadata or {}).get("language")
    )
    line_count: int = content.count("\n") + 1

    ## CHUNK 노드에서 심볼 목록 조회
    chunks_result = await db.execute(
        select(CodeNode)
        .where(
            CodeNode.job_id == repo_id,
            CodeNode.path == path,
            CodeNode.type == "CHUNK",
        )
        .order_by(CodeNode.chunk_index)
    )
    chunk_nodes = chunks_result.scalars().all()

    symbols: list[FileSymbolItem] = []
    for node in chunk_nodes:
        meta = node.file_metadata or {}
        symbol_name: str | None = meta.get("symbol")
        ## symbol 없는 청크는 건너뜀 (익명 모듈 블록 등)
        if not symbol_name:
            continue
        chunk_type: str = meta.get("chunk_type") or "other"
        start_line: int | None = meta.get("start_line")
        end_line: int | None = meta.get("end_line")
        if start_line is None or end_line is None:
            continue
        symbols.append(
            FileSymbolItem(
                name=symbol_name,
                kind=chunk_type,
                startLine=start_line,
                endLine=end_line,
            )
        )

    return FileContentResponse(
        path=path,
        language=language,
        lineCount=line_count,
        content=content,
        symbols=symbols,
    )
