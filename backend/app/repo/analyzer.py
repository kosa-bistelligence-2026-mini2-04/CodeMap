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
CODE_SUFFIXES = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".kt", ".go", ".rs",
    ".rb", ".php", ".cs", ".c", ".h", ".cpp", ".hpp", ".swift", ".vue",
    ".svelte", ".sql", ".sh",
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


def _normalized_code_lines(text: str) -> list[str]:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if len(stripped) < 16:
            continue
        if stripped.startswith(("#", "//", "/*", "*", "--")):
            continue
        if stripped.startswith(("import ", "from ")):
            continue
        lines.append(re.sub(r"\s+", " ", stripped))
    return lines


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
    root = Path(root_path).resolve()
    if not root.exists():
        raise FileNotFoundError(f"Repository snapshot is unavailable: {root}")

    files: list[dict[str, Union[str, int]]] = []
    languages: Counter[str] = Counter()
    stack: set[str] = set()
    entrypoints: list[str] = []
    todo_count = 0
    total_lines = 0
    total_bytes = 0
    test_files = 0
    oversized: list[str] = []
    code_line_files: dict[str, set[str]] = {}
    significant_code_lines = 0

    for path in _iter_files(root):
        relative = path.relative_to(root).as_posix()
        text = _read_text(path)
        line_count = text.count("\n") + (1 if text else 0)
        size = path.stat().st_size
        language = LANGUAGE_BY_SUFFIX.get(path.suffix.lower(), "Config")
        languages[language] += line_count or 1
        total_lines += line_count
        total_bytes += size
        todo_count += len(re.findall(r"\b(?:TODO|FIXME|HACK)\b", text, re.IGNORECASE))
        if "test" in path.name.lower() or "tests" in path.parts:
            test_files += 1
        if line_count > 700:
            oversized.append(relative)
        if path.name.lower() in ENTRYPOINT_NAMES:
            entrypoints.append(relative)
        if path.name in STACK_SIGNALS:
            stack.add(STACK_SIGNALS[path.name])

        if path.suffix.lower() in CODE_SUFFIXES:
            normalized_lines = _normalized_code_lines(text)
            significant_code_lines += len(normalized_lines)
            for normalized_line in set(normalized_lines):
                code_line_files.setdefault(normalized_line, set()).add(relative)

        files.append({
            "path": relative,
            "name": path.name,
            "language": language,
            "lines": line_count,
            "size": size,
            "kind": "test" if ("test" in path.name.lower() or "tests" in path.parts) else "source",
        })

    primary_language = languages.most_common(1)[0][0] if languages else "Unknown"
    test_ratio = test_files / max(len(files), 1)
    total = max(1, len(files))
    test_ratio = test_files / total
    todo_ratio = todo_count / total
    oversized_ratio = len(oversized) / total
    duplicate_code_lines = sum(
        len(paths) - 1
        for paths in code_line_files.values()
        if len(paths) > 1
    )
    duplicate_code_ratio = duplicate_code_lines / max(significant_code_lines, 1)
    duplicate_files = sorted({
        path
        for paths in code_line_files.values()
        if len(paths) > 1
        for path in paths
    })

    score = 100
    score -= min(30, int(oversized_ratio * 100))
    score -= min(20, int(todo_ratio * 50))
    score -= min(25, int(duplicate_code_ratio * 100))

    health_score = max(35, min(100, score))
    health_metrics = {
        "score": health_score,
        "test_ratio": round(test_ratio, 3),
        "todo_ratio": round(todo_ratio, 3),
        "oversized_ratio": round(oversized_ratio, 3),
        "duplicate_code_ratio": round(duplicate_code_ratio, 3),
    }

    strengths = [
        f"{len(files):,}개 텍스트 파일과 {total_lines:,}줄을 실제 저장소 스냅샷에서 확인했습니다.",
        f"주요 언어는 {primary_language}이며 {len(languages)}개 언어·설정 유형이 감지되었습니다.",
    ]
    if stack:
        strengths.append(f"{', '.join(sorted(stack))} 기반의 실행 구성이 명확하게 감지됩니다.")
    if duplicate_code_ratio < 0.03:
        strengths.append("중복 코드 신호가 낮아 공통 로직 재사용 상태가 양호합니다.")

    risks: list[str] = []
    if oversized:
        risks.append(f"700줄을 넘는 대형 파일 {len(oversized)}개가 있어 책임 분리 검토가 필요합니다.")
    if todo_count:
        risks.append(f"TODO/FIXME/HACK 표식 {todo_count}개가 남아 있어 기술 부채 우선순위를 정해야 합니다.")
    if duplicate_code_ratio >= 0.08:
        risks.append("여러 파일에 반복되는 코드 패턴이 감지되어 공통 모듈 추출 검토가 필요합니다.")
    if not risks:
        risks.append("정적 구조상 즉시 드러나는 고위험 신호는 적지만 런타임·권한 경계 검증은 별도로 필요합니다.")

    recommendations = []
    if duplicate_code_ratio >= 0.08:
        recommendations.append({
            "title": "반복 코드 공통화",
            "detail": "여러 파일에 반복되는 구현 패턴을 공통 함수나 모듈로 추출하세요.",
            "affected_files": duplicate_files[:5], "priority": "high",
        })
    if oversized:
        recommendations.append({
            "title": "대형 모듈의 책임 경계 점검",
            "detail": "변경 빈도가 높은 대형 파일부터 UI·도메인·인프라 책임을 분리하세요.",
            "affected_files": oversized[:5], "priority": "medium",
        })
    recommendations.append({
        "title": "분석 결과를 대화형 검증으로 연결",
        "detail": "리포트의 각 근거 파일을 채팅에서 재질문하고 코드 인용으로 확인하세요.",
        "affected_files": entrypoints[:3], "priority": "medium",
    })

    files.sort(key=lambda item: (item["path"].count("/"), item["path"]))
    # [TODO] Git Commit Log 분석을 통한 Contributor 통계 추출 로직 추가
    # 대시보드 시각화(기여자 비율, 파이/도넛 차트) 및 코드 변경 빈도(Churn) 히트맵을 위해
    # 분석 시점에 로컬 .git 로그나 GitHub API를 연동하여 기여자 메타데이터를 수집하는 범위 확정이 필요합니다.
    return {
        "repository": {"name": repo_name, "root": str(root)},
        "stats": {
            "files": len(files), "lines": total_lines, "bytes": total_bytes,
            "tests": test_files, "todos": todo_count, "primary_language": primary_language,
        },
        "languages": [{"name": name, "lines": lines} for name, lines in languages.most_common(8)],
        "stack": sorted(stack),
        "entrypoints": entrypoints[:12],
        "files": files,
        "health_score": health_score,
        "health_metrics": health_metrics,
        "executive_summary": (
            f"{repo_name}은(는) {primary_language} 중심의 코드베이스입니다. "
            f"실제 파일 구조, 진입점, 구성 파일과 유지보수 신호를 기준으로 분석했습니다."
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
