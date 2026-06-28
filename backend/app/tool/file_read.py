"""Repository-bounded file read tool used by workers and future MCP jobs."""

from __future__ import annotations

from pathlib import Path

_MAX_FILE_SIZE = 50_000


def read_repository_file(clone_path: str, rel_path: str | None) -> str:
    """Read a bounded repository-relative file as UTF-8 text."""
    target = (Path(clone_path) / (rel_path or "")).resolve()
    root = Path(clone_path).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return ""

    try:
        text = target.read_text(encoding="utf-8", errors="ignore")
        if len(text) > _MAX_FILE_SIZE:
            text = text[:_MAX_FILE_SIZE] + f"\n... (파일 크기 초과, {_MAX_FILE_SIZE}자까지만 표시)"
        return text
    except Exception as exc:
        return f"파일 읽기 실패: {exc}"


# ──────────────────────────────────────────────
# extract_file_static_metadata
# ──────────────────────────────────────────────
def extract_file_static_metadata(
    file_paths: list[Path], root_path: Path
) -> list[dict]:
    '''
    파일 리스트의 크기, 줄 수, 글자 수, 언어 등 정적 메타데이터를 일괄 추출합니다.
    '''
    language_map = {
        ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript",
        ".js": "JavaScript", ".jsx": "JavaScript", ".java": "Java",
        ".kt": "Kotlin", ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
        ".php": "PHP", ".cs": "C#", ".c": "C", ".h": "C/C++",
        ".cpp": "C++", ".hpp": "C++", ".swift": "Swift", ".vue": "Vue",
        ".svelte": "Svelte", ".sql": "SQL", ".sh": "Shell",
        ".md": "Markdown", ".json": "JSON", ".yml": "YAML", ".yaml": "YAML",
    }

    metadata = []
    for path in file_paths:
        try:
            rel_path = path.relative_to(root_path).as_posix()
        except ValueError:
            continue

        try:
            raw_bytes = path.read_bytes()[:160_000]
            if b"\x00" in raw_bytes:
                ## 바이너리 파일 스킵
                continue
            text = raw_bytes.decode("utf-8", errors="replace")
        except OSError:
            continue

        line_count = text.count("\n") + (1 if text else 0)
        char_count = len(text)
        size = path.stat().st_size
        suffix = path.suffix.lower()

        is_config = suffix in {
            ".toml", ".ini", ".cfg", ".conf", ".xml", ".html",
            ".css", ".scss", ".env.example", ".properties", ".gradle"
        }
        language = language_map.get(
            suffix, "Config" if is_config else "Unknown"
        )

        metadata.append({
            "path": rel_path,
            "name": path.name,
            "lines": line_count,
            "bytes": size,
            "chars": char_count,
            "language": language,
        })

    return metadata
