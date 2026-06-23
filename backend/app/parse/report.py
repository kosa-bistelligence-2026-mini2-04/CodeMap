"""RAG-PARSE report_json contract helpers.

The repository pipeline currently stores report_json from the older
app.repo.analyzer shape, while the RAG-PARSE modules produce ParseResult-shaped
data. These helpers keep read paths tolerant during the migration and provide a
single place for the canonical keys used by future B-210 integration work.
"""

from __future__ import annotations

from typing import Any

from app.parse.schemas import RunCommandSet


def normalize_run_commands(value: Any) -> RunCommandSet:
    """Normalize legacy list or object run command shapes into RunCommandSet."""
    if isinstance(value, dict):
        return RunCommandSet(
            install=str(value.get("install") or ""),
            run=str(value.get("run") or ""),
            build=value.get("build"),
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


def report_files(report_json: dict[str, Any]) -> list[dict[str, Any]]:
    files = report_json.get("files", [])
    return files if isinstance(files, list) else []


def report_tech_stack(report_json: dict[str, Any]) -> list:
    """Read canonical tech_stack, falling back to legacy analyzer stack."""
    stack = report_json.get("tech_stack")
    if stack is None:
        stack = report_json.get("stack", [])
    return stack if isinstance(stack, list) else []


def report_tech_stack_details(report_json: dict[str, Any]) -> list[dict[str, Any]]:
    stack = report_json.get("tech_stack_details")
    if isinstance(stack, list) and stack:
        return [item for item in stack if isinstance(item, dict)]
    return [
        {"name": str(item), "version": None, "category": "library", "source": None}
        for item in report_tech_stack(report_json)
    ]


def report_entry_points(report_json: dict[str, Any]) -> list:
    """Read canonical entry_points, falling back to legacy analyzer entrypoints."""
    entry_points = report_json.get("entry_points")
    if entry_points is None:
        entry_points = report_json.get("entrypoints", [])
    return entry_points if isinstance(entry_points, list) else []


def report_entry_point_details(report_json: dict[str, Any]) -> list[dict[str, Any]]:
    entry_points = report_json.get("entry_point_details")
    if isinstance(entry_points, list) and entry_points:
        return [item for item in entry_points if isinstance(item, dict)]
    return [
        {"path": str(path), "type": None, "reason": None}
        for path in report_entry_points(report_json)
    ]


def report_readme_summary(report_json: dict[str, Any]) -> str:
    readme = report_json.get("readme_summary")
    if readme is None:
        readme = report_json.get("executive_summary", "")
    return str(readme or "")


def report_master_summary(report_json: dict[str, Any]) -> str:
    master = report_json.get("master_summary")
    if master is None:
        master = report_json.get("executive_summary", "")
    return str(master or "")


def report_config_files(files: list[dict[str, Any]]) -> list[str]:
    return [
        item["path"]
        for item in files
        if (
            isinstance(item, dict)
            and item.get("path")
            and isinstance(item.get("metadata"), dict)
            and item["metadata"].get("is_config")
        )
    ]


def report_directory_tree(report_json: dict[str, Any]) -> str | None:
    tree = report_json.get("directory_tree")
    return str(tree) if tree else None


def report_file_map(report_json: dict[str, Any]) -> list[dict[str, Any]]:
    file_map = report_json.get("file_map", [])
    return [item for item in file_map if isinstance(item, dict)] if isinstance(file_map, list) else []


def report_heatmap(report_json: dict[str, Any]) -> list[dict[str, Any]]:
    heatmap = report_json.get("heatmap", [])
    return [item for item in heatmap if isinstance(item, dict)] if isinstance(heatmap, list) else []


def report_folder_summaries(report_json: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = report_json.get("folder_summaries", [])
    return [item for item in summaries if isinstance(item, dict)] if isinstance(summaries, list) else []


def report_file_summaries(report_json: dict[str, Any]) -> list[dict[str, Any]]:
    summaries = report_json.get("file_summaries", [])
    if isinstance(summaries, list) and summaries:
        return [item for item in summaries if isinstance(item, dict)]
    return [
        {"path": item["path"], "summary": item.get("summary") or ""}
        for item in report_files(report_json)
        if isinstance(item, dict) and item.get("path") and item.get("summary")
    ]
