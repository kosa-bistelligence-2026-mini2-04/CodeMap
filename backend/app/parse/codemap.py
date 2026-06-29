"""RAG-PARSE API-005 Code Map 품질 보강 유틸리티.

AST 청킹(B-207)과 import 분석(B-208)이 채운 ParsedFile 목록을 바탕으로
파일 단위 map, fan-in(imported_by), risk score, heatmap 입력을 만든다.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.parse.schemas import FileMapItem, HeatmapItem, ParsedFile

_LANG_BY_EXT = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".java": "Java",
    ".go": "Go",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".kt": "Kotlin",
    ".dart": "Dart",
    ".php": "PHP",
    ".cs": "C#",
    ".sql": "SQL",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".json": "JSON",
    ".md": "Markdown",
}

_RISK_KEYWORDS = (
    "auth",
    "token",
    "secret",
    "password",
    "credential",
    "payment",
    "billing",
    "migration",
    "security",
    "permission",
    "admin",
    "external api",
    "webhook",
)
_RISK_PATTERNS = tuple(
    re.compile(rf"(?<!\w){re.escape(keyword)}(?!\w)", re.IGNORECASE)
    for keyword in _RISK_KEYWORDS
)


def _line_count(node: ParsedFile) -> int:
    return node.lines or len((node.content or "").splitlines())


def _has_risk_keyword(*values: str) -> bool:
    text = "\n".join(values)
    return any(pattern.search(text) for pattern in _RISK_PATTERNS)


def _language_for(node: ParsedFile) -> str | None:
    if node.language:
        return node.language
    return _LANG_BY_EXT.get(Path(node.path).suffix.lower())


def _risk_score(node: ParsedFile, imported_by: list[str]) -> int:
    """파일 크기, import 수, fan-in, config/위험 키워드 기반 점수."""
    content = (node.content or "").lower()
    path = node.path.lower()
    score = 0
    score += min(_line_count(node) // 20, 25)
    score += min(len(node.imports) * 8, 25)
    score += min(len(imported_by) * 10, 25)
    score += min(len(node.chunks) * 4, 15)
    if (node.metadata or {}).get("is_config"):
        score += 10
    if _has_risk_keyword(path, content):
        score += 20
    return min(score, 100)


def _imported_by_index(files: list[ParsedFile]) -> dict[str, list[str]]:
    paths = {node.path for node in files if node.file_type == "FILE"}
    index = {path: [] for path in paths}
    for node in files:
        if node.file_type != "FILE":
            continue
        for target in node.imports:
            if target in index and node.path not in index[target]:
                index[target].append(node.path)
    for value in index.values():
        value.sort()
    return index


async def build_file_map(files: list[ParsedFile]) -> list[FileMapItem]:
    """ParsedFile 목록에서 API-005 fileMap 계약을 생성한다."""
    imported_by = _imported_by_index(files)
    items: list[FileMapItem] = []
    for node in files:
        if node.file_type != "FILE":
            continue
        fan_in = imported_by.get(node.path, [])
        items.append(
            FileMapItem(
                path=node.path,
                language=_language_for(node),
                chunk_count=len(node.chunks),
                lines=_line_count(node),
                bytes=node.size,
                imports=list(node.imports),
                imported_by=fan_in,
                risk_score=_risk_score(node, fan_in),
            )
        )
    return items


async def build_heatmap(files: list[ParsedFile], file_map: list[FileMapItem] | None = None) -> list[HeatmapItem]:
    """fileMap risk score를 heatmap 입력 형태로 변환한다."""
    if file_map is None:
        file_map = await build_file_map(files)
    heatmap = [
        HeatmapItem(path=item.path, score=item.risk_score or 0)
        for item in file_map
        if (item.risk_score or 0) > 0
    ]
    heatmap.sort(key=lambda item: (-item.score, item.path))
    return heatmap
