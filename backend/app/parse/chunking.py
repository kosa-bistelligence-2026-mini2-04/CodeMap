"""RAG-PARSE B-207: AST 기반 코드 청킹.

파이썬은 표준 `ast` 모듈로 함수/클래스 단위 청크를 만들고,
그 외 코드 파일은 모듈 단위 청크 하나로 처리한다.
(AST 청킹은 RAG_PARSE_SPEC B-207에서 명시한 요구사항이다.)
"""

from __future__ import annotations

import ast
import asyncio
from pathlib import Path

from app.parse.schemas import CodeChunk, ParsedFile

# 청킹 대상 코드 확장자 (AST 미지원 언어도 모듈 청크로는 처리)
_CODE_EXTS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".java", ".go", ".rb", ".rs", ".kt", ".c", ".cc", ".cpp", ".cs",
    ".vue", ".svelte", ".php", ".swift", ".scala", ".dart",
}


def _chunk_python(content: str) -> list[CodeChunk]:
    """파이썬 소스를 top-level 함수/클래스 단위로 청킹한다."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []
    lines = content.splitlines()
    chunks: list[CodeChunk] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chunk_type = "function"
        elif isinstance(node, ast.ClassDef):
            chunk_type = "class"
        else:
            continue
        start = node.lineno
        end = getattr(node, "end_lineno", None) or start
        body = "\n".join(lines[start - 1:end])
        chunks.append(
            CodeChunk(
                chunk_index=len(chunks),
                content=body,
                start_line=start,
                end_line=end,
                chunk_type=chunk_type,
            )
        )
    return chunks


def _module_chunk(content: str) -> list[CodeChunk]:
    """파일 전체를 모듈 단위 청크 하나로 만든다 (파서 미지원 언어 / 함수·클래스 없음 폴백)."""
    # splitlines()는 trailing newline을 한 줄로 세지 않으므로 실제 줄 수와 일치한다.
    line_count = max(len(content.splitlines()), 1)
    return [
        CodeChunk(chunk_index=0, content=content, start_line=1, end_line=line_count, chunk_type="module")
    ]


def _chunks_for(node: ParsedFile) -> list[CodeChunk]:
    """단일 파일 노드에 대한 청크 목록을 만든다(비코드/디렉토리/빈 파일은 빈 목록)."""
    if node.file_type != "FILE" or not node.content:
        return []
    ext = Path(node.path).suffix.lower()
    if ext not in _CODE_EXTS:
        return []
    if ext == ".py":
        return _chunk_python(node.content) or _module_chunk(node.content)
    return _module_chunk(node.content)


async def chunk_by_ast(files: list[ParsedFile]) -> list[ParsedFile]:
    """코드 파일을 AST 기반으로 청킹해 chunks가 채워진 ParsedFile 목록을 반환한다 (RAG-PARSE-B-207).

    - `.py`: 표준 ast로 함수/클래스 단위 청크 (없으면 모듈 청크로 폴백)
    - 그 외 코드 파일: 모듈 단위 청크 하나 / 비코드·디렉토리·빈 파일: 청크 없음
    동기 ast.parse는 이벤트 루프를 막지 않도록 스레드 풀로 위임한다(analyze_directory와 정합).
    입력을 in-place로 변경하지 않고 새 객체(model_copy)를 반환한다.
    """
    return await asyncio.to_thread(_chunk_by_ast_sync, files)


def _chunk_by_ast_sync(files: list[ParsedFile]) -> list[ParsedFile]:
    result: list[ParsedFile] = []
    for node in files:
        chunks = _chunks_for(node)
        result.append(node.model_copy(update={"chunks": chunks}) if chunks else node)
    return result
