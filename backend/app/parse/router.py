from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repo.repository import AnalysisJobRepository
from app.core.exceptions import RepositoryNotFoundError, ParseResultNotFoundError
from app.parse.manifest import detect_tech_stack_details
from app.parse.schemas import ParsedFile


router = APIRouter(prefix="/api/parse/analysis", tags=["RAG Parse"])


def _build_directory_tree(files: list[dict], repo_name: str) -> str:
    tree_lines = [f"{repo_name}/"]
    paths = sorted([f.get("path") for f in files if isinstance(f, dict) and f.get("path")])
    
    tree_dict = {}
    for p in paths:
        parts = p.split("/")
        current = tree_dict
        for part in parts:
            if part not in current:
                current[part] = {}
            current = current[part]
            
    def render_tree(node, prefix=""):
        lines = []
        keys = list(node.keys())
        for i, key in enumerate(keys):
            is_last = i == len(keys) - 1
            connector = "└── " if is_last else "├── "
            suffix = "/" if node[key] else ""
            lines.append(f"{prefix}{connector}{key}{suffix}")
            
            extension_prefix = "    " if is_last else "│   "
            lines.extend(render_tree(node[key], prefix + extension_prefix))
        return lines
        
    tree_lines.extend(render_tree(tree_dict))
    return "\n".join(tree_lines)


def _report_files_to_parsed(files: list[dict]) -> list[ParsedFile]:
    parsed: list[ParsedFile] = []
    for item in files:
        if not isinstance(item, dict) or not item.get("path"):
            continue
        try:
            parsed.append(
                ParsedFile(
                    path=item["path"],
                    file_type=item.get("file_type") or item.get("fileType") or "FILE",
                    depth=item.get("depth", 0),
                    content=item.get("content"),
                    metadata=item.get("metadata"),
                )
            )
        except (TypeError, ValueError):
            continue
    return parsed


def _run_commands_response(run_cmds: list[str]) -> dict:
    build_cmd = next((cmd for cmd in run_cmds if " build" in cmd or cmd.startswith("docker build")), None)
    return {
        "install": run_cmds[0] if len(run_cmds) > 0 else "",
        "run": run_cmds[1] if len(run_cmds) > 1 else "",
        "build": build_cmd,
    }


async def _get_report_json(repo_id: UUID, db: AsyncSession) -> tuple[AnalysisJobRepository, dict]:
    repo = AnalysisJobRepository(db)
    job = await repo.get_job_by_id(repo_id)
    if not job:
        raise RepositoryNotFoundError()
    if not job.report_json:
        raise ParseResultNotFoundError()
    return job, job.report_json


@router.get("/{repo_id}/stack")
async def get_parse_stack(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    job, rj = await _get_report_json(repo_id, db)
    files = rj.get("files", [])
    parsed_files = _report_files_to_parsed(files if isinstance(files, list) else [])
    tech_stack = await detect_tech_stack_details(parsed_files)

    return {
        "code": 200,
        "message": "success",
        "data": {
            "repoId": job.id,
            "techStack": tech_stack,
            "runCommands": _run_commands_response(rj.get("run_commands", [])),
        },
    }


@router.get("/{repo_id}")
async def get_parse_analysis(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    job, rj = await _get_report_json(repo_id, db)
    files = rj.get("files", [])
    
    config_files = [f.get("path") for f in files if isinstance(f, dict) and f.get("path") and f.get("metadata") and f["metadata"].get("is_config")]
    tree_text = _build_directory_tree(files, job.repo_name)
    
    tech_stack = rj.get("tech_stack", [])
    run_cmds = rj.get("run_commands", [])
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "repoId": job.id,
            "repoName": job.repo_name,
            "techStack": tech_stack,
            "entryPoints": rj.get("entry_points", []),
            "directoryTree": tree_text,
            "runCommands": _run_commands_response(run_cmds),
            "configFiles": config_files,
            "readmeSummary": rj.get("readme_summary") or "",
            "files": files,
            "fileCount": len(files),
            "analyzedAt": job.updated_at.isoformat() if job.updated_at else None
        }
    }
