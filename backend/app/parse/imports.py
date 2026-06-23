"""RAG-PARSE B-208: 파일 간 import 관계 분석.

각 파일의 import/require 문을 파싱해 **저장소 내 실제 파일 경로로 정규화**하고
ParsedFile.imports에 채운다. 외부 패키지(fastapi, react 등)는 제외 — 저장소
내부 의존만 남긴다(의존성 그래프 입력용).
명세: docs/03_Specifications/02_RAG/spec/RAG_PARSE_SPEC.md (B-208)
"""

from __future__ import annotations

import ast
import asyncio
import re
from pathlib import Path

from app.parse.schemas import ParsedFile

_JS_EXTS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
# JS/TS 상대경로 해석 시 시도할 확장자/인덱스 (확장자 생략 import 대응)
_JS_RESOLVE_SUFFIXES = (
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    "/index.ts", "/index.tsx", "/index.js", "/index.jsx",
)
# from '...' / import '...' / require('...') / import('...')
_JS_IMPORT_RE = re.compile(r"""(?:from|import|require)\s*\(?\s*["']([^"']+)["']""")


async def analyze_imports(files: list[ParsedFile]) -> list[ParsedFile]:
    """파일 간 import 관계를 저장소 경로로 정규화해 imports에 채운다 (RAG-PARSE-B-208).

    - Python: 표준 ast로 import/from(절대·상대) 분석
    - JS/TS: 정규식으로 상대경로 import/require 분석
    동기 파싱은 이벤트 루프를 막지 않도록 스레드 풀로 위임한다(chunking과 정합).
    입력을 in-place로 변경하지 않고 새 객체(model_copy)를 반환한다.
    """
    return await asyncio.to_thread(_analyze_imports_sync, files)


def _analyze_imports_sync(files: list[ParsedFile]) -> list[ParsedFile]:
    repo_paths = {f.path for f in files if f.file_type == "FILE"}
    result: list[ParsedFile] = []
    for node in files:
        if node.file_type != "FILE" or not node.content:
            result.append(node)
            continue
        ext = Path(node.path).suffix.lower()
        if ext == ".py":
            imports = _python_imports(node.path, node.content, repo_paths)
        elif ext in _JS_EXTS:
            imports = _js_imports(node.path, node.content, repo_paths)
        else:
            imports = []
        result.append(node.model_copy(update={"imports": imports}) if imports else node)
    return result


def _module_to_path(dotted: str, repo_paths: set[str]) -> str | None:
    """dotted 모듈명(a.b.c)을 저장소 파일 경로(a/b/c.py 또는 a/b/c/__init__.py)로 해석."""
    base = dotted.replace(".", "/")
    for cand in (f"{base}.py", f"{base}/__init__.py"):
        if cand in repo_paths:
            return cand
    return None


def _python_imports(path: str, content: str, repo_paths: set[str]) -> list[str]:
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError):
        return []
    found: list[str] = []
    pkg_parts = path.split("/")[:-1]  # 파일이 속한 디렉토리 경로 조각
    for node in ast.walk(tree):
        dotted_names: list[str] = []
        if isinstance(node, ast.Import):
            dotted_names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            # base 모듈 경로 계산 (절대/상대 level 처리)
            if node.level == 0:
                base_parts = node.module.split(".") if node.module else []
            elif node.level - 1 <= len(pkg_parts):
                # 상대 import: level-1 만큼 디렉토리 상승 후 module 결합
                base_parts = pkg_parts[: len(pkg_parts) - (node.level - 1)]
                if node.module:
                    base_parts = base_parts + node.module.split(".")
            else:
                base_parts = []
            # `from pkg import mod` 형태도 잡도록 base + 각 import 이름(모듈일 수 있음)을 후보로.
            # 예: `from backend.app import service` → backend.app + backend.app.service 둘 다 후보
            if base_parts:
                dotted_names.append(".".join(base_parts))
            for alias in node.names:
                if alias.name == "*":
                    continue
                dotted_names.append(".".join(base_parts + alias.name.split(".")))
        for dotted in dotted_names:
            resolved = _module_to_path(dotted, repo_paths)
            if resolved and resolved != path and resolved not in found:
                found.append(resolved)
    return found


def _normalize_path(p: str) -> str:
    """./ ../ 를 정리해 저장소 상대 경로로 정규화."""
    parts: list[str] = []
    for seg in p.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
        else:
            parts.append(seg)
    return "/".join(parts)


def _js_imports(path: str, content: str, repo_paths: set[str]) -> list[str]:
    found: list[str] = []
    base_dir = path.rsplit("/", 1)[0] if "/" in path else ""
    for match in _JS_IMPORT_RE.finditer(content):
        spec = match.group(1)
        if not spec.startswith("."):
            continue  # 상대경로만 저장소 내부로 간주(외부 패키지/별칭 제외)
        target = _normalize_path(f"{base_dir}/{spec}" if base_dir else spec)
        resolved = None
        if target in repo_paths:
            resolved = target
        else:
            for suffix in _JS_RESOLVE_SUFFIXES:
                if f"{target}{suffix}" in repo_paths:
                    resolved = f"{target}{suffix}"
                    break
        if resolved and resolved != path and resolved not in found:
            found.append(resolved)
    return found
