"""Deterministic repository inspection used by analysis and repository chat.

The scanner intentionally works without an LLM.  It produces grounded structural
facts first; an optional model may enrich those facts later, but never replaces
them with unverified content.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Union


IGNORED_DIRS = {
    ".git", ".next", ".turbo", ".venv", "venv", "node_modules",
    "dist", "build", "coverage", "__pycache__", ".idea", ".vscode",
}
LANGUAGE_BY_SUFFIX = {
    ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".js": "JavaScript", ".jsx": "JavaScript", ".java": "Java",
    ".kt": "Kotlin", ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
    ".php": "PHP", ".cs": "C#", ".c": "C", ".h": "C/C++",
    ".cpp": "C++", ".hpp": "C++", ".swift": "Swift", ".vue": "Vue",
    ".svelte": "Svelte", ".sql": "SQL", ".sh": "Shell",
    ".md": "Markdown", ".json": "JSON", ".yml": "YAML", ".yaml": "YAML",
}
TEXT_SUFFIXES = set(LANGUAGE_BY_SUFFIX) | {
    ".toml", ".ini", ".cfg", ".conf", ".xml", ".html", ".css", ".scss",
    ".env.example", ".properties", ".gradle",
}
ENTRYPOINT_NAMES = {
    "main.py", "app.py", "manage.py", "main.ts", "main.tsx", "index.ts",
    "index.tsx", "app.tsx", "page.tsx", "server.ts", "server.js", "main.go",
    "main.rs", "pom.xml", "build.gradle", "docker-compose.yml", "docker-compose.yaml",
}
STACK_SIGNALS = {
    "package.json": "Node.js", "next.config.ts": "Next.js", "next.config.js": "Next.js",
    "vite.config.ts": "Vite", "vite.config.js": "Vite", "requirements.txt": "Python",
    "pyproject.toml": "Python", "manage.py": "Django", "pom.xml": "Spring/Java",
    "build.gradle": "Gradle/Java", "go.mod": "Go", "Cargo.toml": "Rust",
    "docker-compose.yml": "Docker", "docker-compose.yaml": "Docker",
}
TOKEN_RE = re.compile(r"[\w][\w./-]{1,}", re.UNICODE)


def _iter_files(root: Path, limit: int = 1200):
    root = root.resolve()
    count = 0
    for path in root.rglob("*"):
        if count >= limit:
            break
        if path.is_symlink():
            continue
        if not path.is_file() or any(part in IGNORED_DIRS for part in path.parts):
            continue
        # resolved path가 workspace 내부인지 검증 (symlink 경유 탈출 방지)
        try:
            path.resolve().relative_to(root)
        except ValueError:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in STACK_SIGNALS:
            continue
        count += 1
        yield path


def _read_text(path: Path, limit: int = 160_000, root: Path | None = None) -> str:
    if path.is_symlink():
        return ""
    if root is not None:
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            return ""
    try:
        raw = path.read_bytes()[:limit]
        if b"\x00" in raw:
            return ""
        return raw.decode("utf-8", errors="replace")
    except OSError:
        return ""


def scan_repository(root_path: str, repo_name: str) -> dict[str, Union[str, int, list, dict]]:
    from app.tool.dir_scan import list_repository_files
    from app.tool.file_read import extract_file_static_metadata
    from app.tool.grep_scan import count_todo_annotations
    from app.tool.env_validation import verify_build_environment
    from app.tool.ast_quality import calculate_code_complexity

    root = Path(root_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Repository snapshot is unavailable: {root}")

    file_paths = list_repository_files(root)
    file_meta = extract_file_static_metadata(file_paths, root)

    from collections import Counter
    languages = Counter()
    total_lines = 0
    total_bytes = 0
    test_files = 0

    for f in file_meta:
        total_lines += f["lines"]
        total_bytes += f["bytes"]
        languages[f["language"]] += f["lines"]
        if "test" in f["name"].lower() or "test" in f["path"].lower():
            test_files += 1

    primary_language = (
        languages.most_common(1)[0][0] if languages else "Unknown"
    )
    test_ratio = test_files / max(len(file_meta), 1)

    todo_res = count_todo_annotations(file_paths)
    env_res = verify_build_environment(file_paths, primary_language, root)
    ast_res = calculate_code_complexity(file_paths)

    health_score = 84
    if test_ratio < 0.05:
        health_score -= 10
    if ast_res["oversized_files"]:
        health_score -= min(8, len(ast_res["oversized_files"]) * 2)
    if todo_res["total_todos"] > 20:
        health_score -= 5
    health_score = max(35, min(96, health_score))

    strengths = [
        f"{len(file_meta):,}개 텍스트 파일과 {total_lines:,}줄을 "
        "실제 저장소 스냅샷에서 확인했습니다.",
        f"주요 언어는 {primary_language}이며 {len(languages)}개 언어·설정 "
        "유형이 감지되었습니다.",
    ]
    if env_res["detected_stack"]:
        joined_stack = ", ".join(sorted(env_res["detected_stack"]))
        strengths.append(
            f"{joined_stack} 기반의 실행 구성이 명확하게 감지됩니다."
        )
    if test_ratio >= 0.08:
        strengths.append(
            f"테스트 관련 파일 {test_files}개가 있어 변경 검증 기반이 "
            "마련되어 있습니다."
        )

    risks = []
    if test_ratio < 0.05:
        risks.append(
            "감지된 테스트 파일 비율이 낮아 핵심 흐름의 회귀 테스트 "
            "범위를 확인해야 합니다."
        )
    if ast_res["oversized_files"]:
        cnt = len(ast_res["oversized_files"])
        risks.append(
            f"700줄을 넘는 대형 파일 {cnt}개가 있어 책임 분리 "
            "검토가 필요합니다."
        )
    if todo_res["total_todos"]:
        cnt = todo_res["total_todos"]
        risks.append(
            f"TODO/FIXME/HACK 표식 {cnt}개가 남아 있어 "
            "기술 부채 우선순위를 정해야 합니다."
        )
    if not risks:
        risks.append(
            "정적 구조상 즉시 드러나는 고위험 신호는 적지만 런타임·권한 "
            "경계 검증은 별도로 필요합니다."
        )

    recommendations = []
    if test_ratio < 0.05:
        recommendations.append({
            "title": "핵심 사용자 흐름에 회귀 테스트 추가",
            "detail": (
                "진입점과 API 경계를 중심으로 최소 통합 테스트를 "
                "먼저 추가하세요."
            ),
            "affected_files": env_res["entrypoints"][:4], "priority": "high",
        })
    if ast_res["oversized_files"]:
        recommendations.append({
            "title": "대형 모듈의 책임 경계 점검",
            "detail": (
                "변경 빈도가 높은 대형 파일부터 UI·도메인·인프라 "
                "책임을 분리하세요."
            ),
            "affected_files": ast_res["oversized_files"][:5],
            "priority": "medium",
        })
    recommendations.append({
        "title": "분석 결과를 대화형 검증으로 연결",
        "detail": (
            "리포트의 각 근거 파일을 채팅에서 재질문하고 "
            "코드 인용으로 확인하세요."
        ),
        "affected_files": env_res["entrypoints"][:3], "priority": "medium",
    })

    files = []
    for f in file_meta:
        files.append({
            "path": f["path"],
            "name": f["name"],
            "language": f["language"],
            "lines": f["lines"],
            "size": f["bytes"],
            "kind": "test" if (
                "test" in f["name"].lower() or "test" in f["path"].lower()
            ) else "source",
        })

    files.sort(key=lambda item: (item["path"].count("/"), item["path"]))

    return {
        "repository": {"name": repo_name, "root": str(root)},
        "stats": {
            "files": len(files), "lines": total_lines, "bytes": total_bytes,
            "tests": test_files, "todos": todo_res["total_todos"],
            "primary_language": primary_language,
        },
        "languages": [
            {"name": name, "lines": lines}
            for name, lines in languages.most_common(8)
        ],
        "stack": env_res["detected_stack"],
        "entrypoints": env_res["entrypoints"][:12],
        "files": files,
        "health_score": health_score,
        "executive_summary": (
            f"{repo_name}은(는) {primary_language} 중심의 "
            "코드베이스입니다. 실제 파일 구조, 진입점, 구성 파일과 "
            "유지보수 신호를 기준으로 분석했습니다."
        ),
        "key_strengths": strengths,
        "key_risks": risks,
        "recommendations": recommendations,
        "conflicts_resolved": [],
    }


def search_repository(root_path: str, query: str, limit: int = 6) -> list[dict[str, Union[str, int]]]:
    root = Path(root_path).resolve()
    terms = {token.lower() for token in TOKEN_RE.findall(query) if len(token) > 2}
    results: list[tuple[int, dict[str, Union[str, int]]]] = []
    for path in _iter_files(root, limit=900):
        relative = path.relative_to(root).as_posix()
        text = _read_text(path, limit=100_000)
        haystack = f"{relative}\n{text}".lower()
        score = sum(haystack.count(term) for term in terms)
        if not score:
            continue
        lines = text.splitlines()
        match_index = next(
            (i for i, line in enumerate(lines) if any(term in line.lower() for term in terms)),
            0,
        )
        start = max(0, match_index - 2)
        snippet = "\n".join(lines[start : start + 7])[:1200]
        results.append((score, {
            "file": relative, "line": start + 1, "snippet": snippet,
            "language": LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "text"),
        }))
    results.sort(key=lambda item: (-item[0], len(item[1]["file"])))
    return [item for _, item in results[:limit]]
