"""RAG-PARSE B-202/B-203: 디렉토리 구조 분석 + 진입점 탐색.

저장소를 재귀 탐색하여 파일/디렉토리 노드(ParsedFile) 목록을 만들고,
진입점 파일을 우선순위대로 정렬한다.
명세: docs/03_Specifications/02_RAG/spec/RAG_PARSE_SPEC.md (B-202, B-203)
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.parse.schemas import ParsedFile

# 탐색 제외 디렉토리 — repo/analyzer.IGNORED_DIRS와 동일 값으로 정합(노이즈/대용량 제외).
# 도메인 결합을 피하려 import 대신 parse 자체 상수로 둔다(추후 공통 상수화 가능).
_EXCLUDED_DIRS = {
    ".git", ".next", ".turbo", ".venv", "venv", "node_modules",
    "dist", "build", "coverage", "__pycache__", ".idea", ".vscode",
}
# 텍스트로 읽지 않을 확장자 (바이너리) → content=None
_BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".pdf", ".zip", ".gz", ".tar", ".jar", ".class",
    ".woff", ".woff2", ".ttf", ".eot", ".mp4", ".mp3", ".wav",
    ".pyc", ".so", ".dll", ".exe", ".bin",
}
# 민감 파일 — content를 읽지 않는다(EMBED/LLM 입력으로 비밀이 유출되는 것을 방지).
# repo/service.py의 EXCLUDED_FILE_NAMES/EXCLUDED_FILE_EXTENSIONS와 동일 정책.
_SENSITIVE_FILE_NAMES = {
    ".env", ".env.local", ".env.development", ".env.production", ".env.staging",
    "id_rsa", "id_dsa", "id_ecdsa", "id_ed25519",
    "id_rsa.pub", "id_dsa.pub", "id_ecdsa.pub", "id_ed25519.pub",
}
_SENSITIVE_FILE_EXTS = {".pem", ".key", ".p12", ".pfx", ".keystore", ".jks"}
# content를 읽을 최대 크기 (초과 시 생략)
_MAX_CONTENT_BYTES = 1_000_000

# 진입점 파일 우선순위 (앞일수록 우선; RAG-PARSE-B-203). page=Next.js App Router 진입점.
_ENTRY_STEMS = ["main", "__main__", "app", "server", "index", "page", "manage", "cli", "wsgi", "asgi"]
# 진입점으로 인정할 코드 확장자 (index.html/main.css 같은 비코드 파일 오탐 방지)
_ENTRY_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rb", ".java", ".rs", ".kt"}


def _read_text(path: Path) -> str | None:
    """텍스트 파일 내용을 반환. 바이너리/민감파일/대용량/빈파일/오류면 None."""
    # 민감 파일(.env, 키류)은 content를 읽지 않는다 — EMBED/LLM 유출 방지.
    if path.name in _SENSITIVE_FILE_NAMES or path.suffix.lower() in _SENSITIVE_FILE_EXTS:
        return None
    if path.suffix.lower() in _BINARY_EXTS:
        return None
    try:
        if path.stat().st_size > _MAX_CONTENT_BYTES:
            return None
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # 디코딩 불가(바이너리)면 content를 생략한다. errors="replace"로 오염된
        # 텍스트가 청킹·임베딩으로 유입되는 것을 방지.
        return None
    return content or None  # 빈 파일은 ""가 아니라 None으로 통일


async def analyze_directory(clone_path: str) -> list[ParsedFile]:
    """저장소를 재귀 탐색해 파일/디렉토리 노드 목록을 만든다 (RAG-PARSE-B-202).

    동기 파일 I/O(rglob/read_text)는 이벤트 루프를 막지 않도록 스레드 풀로 위임한다.
    (code_map_node가 scan_repository를 asyncio.to_thread로 호출하는 패턴과 동일.)
    """
    return await asyncio.to_thread(_analyze_directory_sync, clone_path)


def _analyze_directory_sync(clone_path: str) -> list[ParsedFile]:
    """analyze_directory의 동기 본체. analyzer._iter_files와 동일하게 rglob + parts 제외 사용.

    depth는 슬래시 개수(루트 파일=0, src/main.py=1) — GETTING_STARTED의 CodeNode 예시 기준.
    """
    root = Path(clone_path).resolve()
    nodes: list[ParsedFile] = []
    if not root.exists():
        return nodes

    for path in root.rglob("*"):
        # symlink는 건너뛴다 — clone 디렉토리 밖(host 파일/비밀)을 가리킬 수 있어
        # content가 EMBED/LLM로 유출되는 root-escape를 차단한다.
        if path.is_symlink():
            continue
        rel_parts = path.relative_to(root).parts
        if any(part in _EXCLUDED_DIRS for part in rel_parts):
            continue
        rel = path.relative_to(root).as_posix()
        if path.is_dir():
            nodes.append(
                ParsedFile(path=rel, file_type="DIRECTORY", depth=rel.count("/"), content=None)
            )
        else:
            nodes.append(
                ParsedFile(path=rel, file_type="FILE", depth=rel.count("/"), content=_read_text(path))
            )

    # 얕은 경로 → 알파벳 순으로 안정 정렬
    nodes.sort(key=lambda n: (n.path.count("/"), n.path))
    return nodes


async def find_entry_points(files: list[ParsedFile]) -> list[str]:
    """진입점 파일을 우선순위대로 반환 (RAG-PARSE-B-203).

    순수 정렬 로직이라 I/O는 없지만, PARSE 파이프라인 단계 일관성과 테스트 계약
    (await find_entry_points(...))을 위해 async로 유지한다.
    main → __main__ → app → server → index ... 순. 같은 순위면 얕은 경로 우선.
    """
    candidates: list[tuple[int, int, str]] = []
    for node in files:
        if node.file_type != "FILE":
            continue
        name = Path(node.path)
        if name.suffix.lower() not in _ENTRY_EXTS:
            continue
        stem = name.stem.lower()
        if stem in _ENTRY_STEMS:
            candidates.append((_ENTRY_STEMS.index(stem), node.path.count("/"), node.path))
    candidates.sort()
    return [path for _, _, path in candidates]
