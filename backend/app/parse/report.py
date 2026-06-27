"""RAG-PARSE report_json contract helpers.

The repository pipeline currently stores report_json from the older
app.repo.analyzer shape, while the RAG-PARSE modules produce ParseResult-shaped
data. These helpers keep read paths tolerant during the migration and provide a
single place for the canonical keys used by future B-210 integration work.
"""

from __future__ import annotations

from typing import Union

JsonDict = dict[str, Union[str, int, float, bool, list, dict, None]]

from app.parse.schemas import RunCommandSet


def normalize_run_commands(value: Union[JsonDict, list[Union[str, int, float, bool, dict, list, None]], None]) -> RunCommandSet:
    """Normalize legacy list or object run command shapes into RunCommandSet."""
    if isinstance(value, dict):
        build_val = value.get("build")
        return RunCommandSet(
            install=str(value.get("install") or ""),
            run=str(value.get("run") or ""),
            build=str(build_val) if build_val is not None else None,
        )
    if isinstance(value, list):
        build_cmd = next(
            (
                str(cmd)
                for cmd in value
                if isinstance(cmd, str) and (" build" in cmd or cmd.startswith("docker build"))
            ),
            None,
        )
        return RunCommandSet(
            install=str(value[0]) if len(value) > 0 else "",
            run=str(value[1]) if len(value) > 1 else "",
            build=build_cmd,
        )
    return RunCommandSet()


def report_files(report_json: JsonDict) -> list[JsonDict]:
    files = report_json.get("files", [])
    if isinstance(files, list):
        return [item for item in files if isinstance(item, dict)]
    return []


def report_tech_stack(report_json: JsonDict) -> list:
    """Read canonical tech_stack, falling back to legacy analyzer stack."""
    stack = report_json.get("tech_stack")
    if stack is None:
        stack = report_json.get("stack", [])
    return stack if isinstance(stack, list) else []


def report_tech_stack_details(report_json: JsonDict) -> list[JsonDict]:
    stack = report_json.get("tech_stack_details")
    if isinstance(stack, list) and stack:
        return [item for item in stack if isinstance(item, dict)]
    return [
        {"name": str(item), "version": None, "category": "library", "source": None}
        for item in report_tech_stack(report_json)
    ]


def report_entry_points(report_json: JsonDict) -> list:
    """Read canonical entry_points, falling back to legacy analyzer entrypoints."""
    entry_points = report_json.get("entry_points")
    if entry_points is None:
        entry_points = report_json.get("entrypoints", [])
    return entry_points if isinstance(entry_points, list) else []


def report_entry_point_details(report_json: JsonDict) -> list[JsonDict]:
    entry_points = report_json.get("entry_point_details")
    if isinstance(entry_points, list) and entry_points:
        return [item for item in entry_points if isinstance(item, dict)]
    return [
        {"path": str(path), "type": None, "reason": None}
        for path in report_entry_points(report_json)
    ]


def report_readme_summary(report_json: JsonDict) -> str:
    readme = report_json.get("readme_summary")
    if readme is None:
        readme = report_json.get("executive_summary", "")
    return str(readme or "")


def report_master_summary(report_json: JsonDict) -> str:
    master = report_json.get("master_summary")
    if master is None:
        master = report_json.get("executive_summary", "")
    return str(master or "")


def report_config_files(files: list[JsonDict]) -> list[str]:
    result: list[str] = []
    for item in files:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if not path:
            continue
        metadata = item.get("metadata")
        if isinstance(metadata, dict) and metadata.get("is_config"):
            result.append(str(path))
    return result


def report_directory_tree(report_json: JsonDict) -> str | None:
    tree = report_json.get("directory_tree")
    return str(tree) if tree is not None else None


def report_file_map(report_json: JsonDict) -> list[JsonDict]:
    file_map = report_json.get("file_map", [])
    if isinstance(file_map, list):
        return [item for item in file_map if isinstance(item, dict)]
    return []


def report_heatmap(report_json: JsonDict) -> list[JsonDict]:
    heatmap = report_json.get("heatmap", [])
    if isinstance(heatmap, list):
        return [item for item in heatmap if isinstance(item, dict)]
    return []


def report_folder_summaries(report_json: JsonDict) -> list[JsonDict]:
    summaries = report_json.get("folder_summaries", [])
    if isinstance(summaries, list):
        return [item for item in summaries if isinstance(item, dict)]
    return []


def report_file_summaries(report_json: JsonDict) -> list[JsonDict]:
    summaries = report_json.get("file_summaries", [])
    if isinstance(summaries, list) and summaries:
        return [item for item in summaries if isinstance(item, dict)]

    result: list[JsonDict] = []
    for item in report_files(report_json):
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        summary = item.get("summary")
        if path and summary:
            result.append({"path": path, "summary": summary or ""})
    return result
