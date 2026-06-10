from dataclasses import dataclass
from typing import Iterator
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript
from tree_sitter import Language, Parser, Node

PY_LANGUAGE = Language(tspython.language())
JS_LANGUAGE = Language(tsjavascript.language())

CHUNK_NODE_TYPES = {
    "python": {"function_definition", "async_function_definition", "class_definition"},
    "javascript": {
        "function_definition",
        "arrow_function",
        "class_declaration",
        "method_definition",
        "export_statement",
    },
}


@dataclass
class CodeChunk:
    content: str
    context_prefix: str
    file_path: str
    language: str
    chunk_type: str
    name: str | None
    start_line: int
    end_line: int


def get_parser(language: str) -> Parser:
    lang = PY_LANGUAGE if language == "python" else JS_LANGUAGE
    parser = Parser(lang)
    return parser


def _node_name(node: Node, source: bytes) -> str | None:
    name_node = node.child_by_field_name("name")
    return name_node.text.decode() if name_node else None


def _build_prefix(
    file_path: str, parent_name: str | Node | None, node_name: str | None
) -> str:
    parts = [file_path]
    if parent_name and isinstance(parent_name, str):
        parts.append(parent_name)
    if node_name:
        parts.append(node_name)
    return " > ".join(parts)


def _walk(
    node: Node,
    source: bytes,
    file_path: str,
    language: str,
    parent_name: str | None = None,
) -> Iterator[CodeChunk]:
    """Recursively walk the AST and yield CodeChunk for each function/class/method."""
    target_types = CHUNK_NODE_TYPES.get(language, set())

    if node.type in target_types:
        name = _node_name(node, source)
        chunk_type = "class" if "class" in node.type else "function"
        content = source[node.start_byte : node.end_byte].decode(
            "utf-8", errors="replace"
        )

        # Skip tiny stubs (<3 lines) - not worth indexing
        if node.end_point[0] - node.start_point[0] >= 2:
            yield CodeChunk(
                content=content,
                context_prefix=_build_prefix(file_path, parent_name, name),
                file_path=file_path,
                language=language,
                chunk_type=chunk_type,
                name=name,
                start_line=node.start_point[0],
                end_line=node.end_point[0],
            )

        # Recurse into class bodies - methods become their own chunks
        if chunk_type == "class":
            for child in node.children:
                yield from _walk(child, source, file_path, language, parent_name=name)

    else:
        for child in node.children:
            yield from _walk(
                child, source, file_path, language, parent_name=parent_name
            )


def chunk_file(file_path: str, source_code: str, language: str) -> list[CodeChunk]:
    parser = get_parser(language)
    source_bytes = source_code.encode("utf-8")
    tree = parser.parse(source_bytes)
    chunks = list(_walk(tree.root_node, source_bytes, file_path, language))

    ## Fallback: if AST yields nothing, treat whole file as one module
    if not chunks and len(source_code.strip()) > 0:
        chunks = [
            CodeChunk(
                content=source_code,
                context_prefix=file_path,
                file_path=file_path,
                language=language,
                chunk_type="module",
                name="module",
                start_line=0,
                end_line=source_code.count("\n"),
            )
        ]

    return chunks
