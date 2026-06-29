"""Grep/regex scan tool used by LangGraph workers and future MCP jobs."""

from __future__ import annotations

import re
from pathlib import Path

_MAX_FILE_SIZE = 50_000
_MAX_GREP_RESULTS = 30
_MAX_PATTERN_LENGTH = 128
_NESTED_QUANTIFIER = re.compile(r"\([^)]*[+*][^)]*\)\s*[+*?{]")


def _is_safe_pattern(pattern: str) -> bool:
    """Reject empty or high-risk regex patterns before scanning repository files."""
    if not pattern or not pattern.strip():
        return False
    if len(pattern) > _MAX_PATTERN_LENGTH:
        return False
    if _NESTED_QUANTIFIER.search(pattern):
        return False
    return True


def grep_repository_path(clone_path: str, rel_path: str | None, pattern: str) -> str:
    """Search a repository-relative path with a bounded regex scan."""
    if not _is_safe_pattern(pattern):
        return ""

    base = (Path(clone_path) / (rel_path or "")).resolve()
    root = Path(clone_path).resolve()
    try:
        base.relative_to(root)
    except ValueError:
        return ""

    matches: list[str] = []
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
        count = 0
        candidates = [base] if base.is_file() else sorted(base.rglob("*"))
        for file_path in candidates:
            if not file_path.is_file() or file_path.stat().st_size > _MAX_FILE_SIZE:
                continue
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
                for lineno, line in enumerate(text.splitlines(), 1):
                    if compiled.search(line):
                        rel = file_path.relative_to(root)
                        matches.append(f"{rel}:{lineno}: {line.strip()}")
                        count += 1
                        if count >= _MAX_GREP_RESULTS:
                            break
            except Exception:
                continue
            if count >= _MAX_GREP_RESULTS:
                break
    except re.error as exc:
        return f"정규식 오류: {exc}"

    return "\n".join(matches) or "(결과 없음)"


# ──────────────────────────────────────────────
# count_todo_annotations
# ──────────────────────────────────────────────
def count_todo_annotations(file_paths: list[Path]) -> dict:
    '''
    제시된 파일 리스트 내의 TODO/FIXME/HACK 주석 개수를 집계합니다.
    '''
    todo_re = re.compile(
        r"\b(?:TODO|FIXME|HACK)\b", re.IGNORECASE
    )
    total_count = 0

    for path in file_paths:
        try:
            raw_bytes = path.read_bytes()[:160_000]
            if b"\x00" in raw_bytes:
                continue
            text = raw_bytes.decode("utf-8", errors="replace")
        except OSError:
            continue

        matches = todo_re.findall(text)
        total_count += len(matches)

    return {"total_todos": total_count}
