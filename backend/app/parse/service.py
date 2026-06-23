"""RAG-PARSE 서비스 진입점.

각 기능은 app/parse/<module>.py에 구현하고 여기서 re-export한다.
(테스트가 app.parse.service 기준으로 함수를 참조/patch하므로 모듈 속성으로 노출해야 한다.)

작업 단위별로 아래 import에 한 줄씩 추가된다:
  directory : analyze_directory, find_entry_points         (B-202/203)  ← 구현됨
  manifest  : tag_config_files, extract_run_commands, extract_run_command_details,
              detect_tech_stack (B-204/205/206)
  readme    : parse_readme                                  (B-201)
  chunking  : chunk_by_ast                                  (B-207)
  imports   : analyze_imports                               (B-208)
  codemap   : build_file_map, build_heatmap                  (API-005)
  summary   : build_hierarchical_summary, build_file_summaries,
              build_folder_summaries, run_structure_agent (B-209/210)
  run_parse_pipeline : 오케스트레이터                        (통합)
"""

from uuid import UUID

from app.parse.directory import analyze_directory, find_entry_points
from app.parse.chunking import chunk_by_ast
from app.parse.manifest import (
    tag_config_files,
    extract_run_commands,
    extract_run_command_details,
    detect_tech_stack,
    detect_tech_stack_details,
)
from app.parse.imports import analyze_imports
from app.parse.codemap import build_file_map, build_heatmap
from app.parse.readme import parse_readme
from app.parse.language import analyze_language_composition
from app.parse.summary import (
    build_file_summaries,
    build_folder_summaries,
    build_hierarchical_summary,
)
from app.parse.schemas import (
    ParseResult,
    ParsedFile,
    TechStackItem,
    LanguageCompositionItem,
    EntryPointItem,
)


def _directory_tree(files: list[ParsedFile], repo_name: str) -> str:
    tree_lines = [f"{repo_name}/"]
    paths = sorted(node.path for node in files if node.path)

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
            if node[key]:
                extension = "    " if is_last else "│   "
                lines.extend(render_tree(node[key], prefix + extension))
        return lines

    tree_lines.extend(render_tree(tree_dict))
    return "\n".join(tree_lines)


async def run_structure_agent(files: list[ParsedFile]) -> list[ParsedFile]:
    """B-210 구조 분석 agent hook.

    현재는 앞선 deterministic parse 단계들이 이미 채운 ParsedFile 목록을 그대로
    반환한다. 추후 LLM 기반 구조 agent가 필요해지면 이 함수 안에서만 교체한다.
    """
    return files


async def run_parse_pipeline(
    *,
    job_id: UUID,
    repo_name: str,
    owner: str,
    branch: str,
    clone_path: str,
) -> ParseResult:
    """RAG-PARSE B-210 통합 파이프라인을 실행해 ParseResult를 반환한다."""
    readme_summary = await parse_readme(clone_path)
    files = await analyze_directory(clone_path)
    entry_points = await find_entry_points(files)
    files = await tag_config_files(files)

    run_commands = await extract_run_commands(files)
    run_command_details = await extract_run_command_details(files)
    
    tech_stack_details_raw = await detect_tech_stack_details(files)
    tech_stack_details = [TechStackItem(**i) for i in tech_stack_details_raw]
    tech_stack = sorted(list({str(i.name) for i in tech_stack_details}))

    language_composition_raw = analyze_language_composition(files)
    language_composition = [LanguageCompositionItem(**i) for i in language_composition_raw]

    files = await chunk_by_ast(files)
    files = await analyze_imports(files)
    files = await run_structure_agent(files)

    files, master_summary = await build_hierarchical_summary(files)
    file_map = await build_file_map(files)
    heatmap = await build_heatmap(files, file_map=file_map)
    file_summaries = await build_file_summaries(files)
    folder_summaries = await build_folder_summaries(files)
    config_files = [
        node.path
        for node in files
        if node.file_type == "FILE" and (node.metadata or {}).get("is_config")
    ]
    entry_point_details = [EntryPointItem(path=p, type="auto", reason="파이프라인 휴리스틱 추출") for p in entry_points]

    return ParseResult(
        job_id=job_id,
        repo_name=repo_name,
        owner=owner,
        branch=branch,
        readme_summary=readme_summary,
        tech_stack=tech_stack,
        tech_stack_details=tech_stack_details,
        language_composition=language_composition,
        run_commands=run_commands,
        run_command_details=run_command_details,
        entry_points=entry_points,
        entry_point_details=entry_point_details,
        config_files=config_files,
        master_summary=master_summary,
        folder_summaries=folder_summaries,
        file_summaries=file_summaries,
        file_map=file_map,
        heatmap=heatmap,
        directory_tree=_directory_tree(files, repo_name),
        files=files,
    )

__all__ = [
    "analyze_directory",
    "find_entry_points",
    "chunk_by_ast",
    "tag_config_files",
    "extract_run_commands",
    "extract_run_command_details",
    "detect_tech_stack",
    "detect_tech_stack_details",
    "analyze_imports",
    "build_file_map",
    "build_heatmap",
    "parse_readme",
    "analyze_language_composition",
    "build_file_summaries",
    "build_folder_summaries",
    "build_hierarchical_summary",
    "run_structure_agent",
    "run_parse_pipeline",
]
