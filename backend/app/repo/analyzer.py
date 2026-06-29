"""
저장소 분석(Repository Analysis) 라이브러리 (레거시/하위호환 Proxy)

실제 파이프라인(nodes.py)은 AnalysisService를 호출하나,
테스트 및 하위 엔드포인트 호환성을 위해 본 인터페이스를 유지합니다.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Union

from app.tool.dir_scan import list_repository_files
from app.tool.file_read import extract_file_static_metadata
from app.tool.grep_scan import count_todo_annotations
from app.tool.env_validation import verify_build_environment
from app.tool.ast_quality import (
    calculate_code_complexity,
    calculate_module_coupling,
)

# ──────────────────────────────────────────────
# 상수 정의
# ──────────────────────────────────────────────
CODE_SUFFIXES = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".cpp", ".c",
    ".h", ".cs", ".rb", ".php", ".rs", ".kt", ".swift", ".scala",
}

LANGUAGE_BY_SUFFIX = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript React", ".jsx": "JavaScript React",
    ".go": "Go", ".java": "Java", ".cpp": "C++", ".c": "C",
    ".h": "C Header", ".cs": "C#", ".rb": "Ruby", ".php": "PHP",
    ".rs": "Rust", ".kt": "Kotlin", ".swift": "Swift",
    ".scala": "Scala", ".sh": "Shell", ".bash": "Shell",
    ".md": "Markdown", ".json": "JSON", ".yaml": "YAML",
    ".yml": "YAML", ".xml": "XML", ".html": "HTML", ".css": "CSS",
}

TOKEN_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")


def _read_text(path: Path, limit: int = 100_000) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read(limit)
    except Exception:
        return ""


def _iter_files(root: Path, limit: int = 900) -> list[Path]:
    results = []
    for p in root.rglob("*"):
        if len(results) >= limit:
            break
        if p.is_file() and not p.is_symlink():
            if ".git" not in p.parts and "node_modules" not in p.parts:
                results.append(p)
    return results


def _normalized_code_lines(text: str) -> list[str]:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith(("#", "//", "/*", "*")):
            lines.append(re.sub(r"\s+", "", stripped))
    return lines


# ──────────────────────────────────────────────
# scan_repository (원격 main의 중복도 검출 병합 및 bytes 통일)
# ──────────────────────────────────────────────
def scan_repository(root_path: str, repo_name: str) -> dict:
    """
    저장소 내 소스 파일들을 분석하여 구조 지표와 메타데이터 리포트를 생성합니다.
    """
    root = Path(root_path).resolve()

    file_paths = list_repository_files(root)
    file_meta = extract_file_static_metadata(file_paths, root)

    from collections import Counter
    languages = Counter()
    total_lines = 0
    total_bytes = 0
    test_files = 0

    oversized: list[str] = []
    code_line_files: dict[str, set[str]] = {}
    significant_code_lines = 0

    for f in file_meta:
        total_lines += f["lines"]
        total_bytes += f["bytes"]
        languages[f["language"]] += f["lines"]
        
        path_str = f["path"]
        name_str = f["name"]
        
        if "test" in name_str.lower() or "test" in path_str.lower():
            test_files += 1

        # 중복도 계산을 위해 파일 텍스트 실시간 검출 적용
        full_path = root / path_str
        suffix = full_path.suffix.lower()
        if suffix in CODE_SUFFIXES:
            text = _read_text(full_path, limit=100_000)
            normalized_lines = _normalized_code_lines(text)
            significant_code_lines += len(normalized_lines)
            for normalized_line in set(normalized_lines):
                code_line_files.setdefault(normalized_line, set()).add(path_str)
            
            if f["lines"] > 700:
                oversized.append(path_str)

    primary_language = (
        languages.most_common(1)[0][0] if languages else "Unknown"
    )
    test_ratio = test_files / max(len(file_meta), 1)

    todo_res = count_todo_annotations(file_paths)
    env_res = verify_build_environment(file_paths, primary_language, root)
    ast_res = calculate_code_complexity(file_paths)

    # 중복 비율 계산
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

    # 원격 main의 score 지표 계산식 적용
    todo_ratio = todo_res["total_todos"] / max(1, len(file_meta))
    oversized_ratio = len(oversized) / max(1, len(file_meta))

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
        f"{len(file_meta):,}개 텍스트 파일과 {total_lines:,}줄이 "
        "실제 저장소 스냅샷에서 확인되었습니다.",
        f"주요 언어는 {primary_language}이며 {len(languages)}개 언어·설정 "
        "유형이 감지되었습니다.",
    ]

    stack = env_res["detected_stack"]
    if stack:
        strengths.append(
            f"{', '.join(sorted(stack))} 기반의 실행 구성이 명확하게 감지됩니다."
        )
    if duplicate_code_ratio < 0.03:
        strengths.append("중복 코드 신호가 낮아 공통 로직 재사용 상태가 양호합니다.")

    risks: list[str] = []
    if oversized:
        risks.append(
            f"700줄을 넘는 대형 파일 {len(oversized)}개가 있어 책임 분리 검토가 필요합니다."
        )
    if todo_res["total_todos"]:
        risks.append(
            f"TODO/FIXME/HACK 표식 {todo_res['total_todos']}개가 남아 있어 "
            "기술 부채 우선순위를 정해야 합니다."
        )
    if duplicate_code_ratio >= 0.08:
        risks.append(
            "여러 파일에 반복되는 코드 패턴이 감지되어 공통 모듈 추출 검토가 필요합니다."
        )

    if not risks:
        risks.append(
            "정적 구조상 즉시 드러나는 고위험 신호는 적지만 런타임·권한 "
            "경계 검증은 별도로 필요합니다."
        )

    recommendations = []
    if duplicate_code_ratio >= 0.08:
        recommendations.append({
            "title": "반복 코드 공통화",
            "detail": "여러 파일에 반복되는 구현 패턴을 공통 함수나 모듈로 추출하세요.",
            "affected_files": duplicate_files[:5], "priority": "high",
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

    # size를 완전히 소거하고 bytes로 통일하여 리스트 조립
    files = []
    for f in file_meta:
        files.append({
            "path": f["path"],
            "name": f["name"],
            "language": f["language"],
            "lines": f["lines"],
            "bytes": f["bytes"],    # 💡 size 삭제 및 bytes 통일
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
        "health_metrics": health_metrics,
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


def search_repository(
    root_path: str, query: str, limit: int = 6
) -> list[dict[str, Union[str, int]]]:
    root = Path(root_path).resolve()
    terms = {
        token.lower() for token in TOKEN_RE.findall(query) if len(token) > 2
    }
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
            (
                i
                for i, line in enumerate(lines)
                if any(term in line.lower() for term in terms)
            ),
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
