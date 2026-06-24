from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.database import get_db
from app.common.exceptions import ParseResultNotFoundError, RepositoryNotFoundError
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
from app.repo.repository import AnalysisJobRepository


router = APIRouter(prefix="/api/parse/analysis", tags=["RAG Parse"])


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
