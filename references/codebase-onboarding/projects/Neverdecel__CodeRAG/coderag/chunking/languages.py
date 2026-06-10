"""File-extension -> language mapping and the set of languages with symbol parsers."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

# Languages for which we extract symbol-aware spans (function/class/method).
# Python uses the stdlib ``ast``; the rest use tree-sitter.
PYTHON = "python"
TREE_SITTER_LANGUAGES = {"javascript", "typescript", "tsx", "go", "rust", "java"}
SYMBOL_LANGUAGES = {PYTHON} | TREE_SITTER_LANGUAGES

# Everything indexable. Languages not in SYMBOL_LANGUAGES are still indexed via the
# line-window fallback (so docs/config/other code remain searchable).
EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    # Indexed with the fallback chunker:
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".kt": "kotlin",
    ".swift": "swift",
    ".scala": "scala",
    ".sh": "shell",
    ".bash": "shell",
    ".sql": "sql",
    ".md": "markdown",
    ".rst": "rst",
    ".txt": "text",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".cfg": "ini",
    ".ini": "ini",
}


def detect_language(path: str | Path) -> Optional[str]:
    """Return the language for ``path``, or ``None`` if it should not be indexed."""
    return EXTENSION_TO_LANGUAGE.get(Path(path).suffix.lower())
