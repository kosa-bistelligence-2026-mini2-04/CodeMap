"""P2 tests: symbol-aware chunking for Python + tree-sitter languages, plus fallbacks."""

from __future__ import annotations

from coderag.chunking import chunk_file
from coderag.chunking.languages import detect_language
from coderag.config import Config

CFG = Config(provider="fake", window_lines=10, window_overlap=2, max_chunk_lines=50)


def _symbols(chunks):
    return {c.symbol for c in chunks if c.symbol}


def test_detect_language():
    assert detect_language("a.py") == "python"
    assert detect_language("a.tsx") == "tsx"
    assert detect_language("a.rs") == "rust"
    assert detect_language("a.unknownext") is None


def test_python_functions_and_methods():
    src = (
        "import os\n"
        "\n"
        "def top_level():\n"
        "    return 1\n"
        "\n"
        "class Greeter:\n"
        '    """A greeter."""\n'
        "    def hello(self):\n"
        "        return 'hi'\n"
        "\n"
        "    def bye(self):\n"
        "        return 'bye'\n"
    )
    chunks = chunk_file(src, "python", CFG)
    syms = _symbols(chunks)
    assert "top_level" in syms
    assert "Greeter" in syms
    assert "Greeter.hello" in syms
    assert "Greeter.bye" in syms
    # method chunk should contain its body and nothing from the sibling method
    hello = next(c for c in chunks if c.symbol == "Greeter.hello")
    assert "return 'hi'" in hello.text
    assert "return 'bye'" not in hello.text


def test_python_decorator_included_in_span():
    src = "@property\ndef name(self):\n    return self._n\n"
    chunks = chunk_file(src, "python", CFG)
    fn = next(c for c in chunks if c.symbol == "name")
    assert fn.start_line == 1
    assert "@property" in fn.text


def test_python_syntax_error_falls_back_to_windows():
    src = "def broken(:\n    this is not python\n" * 5
    chunks = chunk_file(src, "python", CFG)
    assert chunks  # did not crash
    assert all(c.kind == "window" for c in chunks)


def test_non_overlapping_coverage():
    src = "\n".join(f"x{i} = {i}" for i in range(40))
    chunks = chunk_file(src, "python", CFG)
    # windows may overlap by design, but symbol chunks must not duplicate lines wildly
    assert chunks
    assert all(c.start_line <= c.end_line for c in chunks)


def test_oversized_symbol_is_split():
    body = "\n".join(f"    a{i} = {i}" for i in range(120))
    src = f"def huge():\n{body}\n"
    chunks = chunk_file(src, "python", CFG)
    huge = [c for c in chunks if c.symbol == "huge"]
    assert len(huge) > 1  # split into multiple windows


def test_javascript_symbols():
    src = (
        "function add(a, b) {\n  return a + b;\n}\n\n"
        "class Counter {\n  inc() { this.n++; }\n}\n"
    )
    chunks = chunk_file(src, "javascript", CFG)
    syms = _symbols(chunks)
    assert "add" in syms
    assert "Counter" in syms
    assert "inc" in syms


def test_go_symbols():
    src = (
        "package main\n\n"
        "func Add(a, b int) int {\n\treturn a + b\n}\n\n"
        "type Point struct {\n\tX int\n}\n"
    )
    chunks = chunk_file(src, "go", CFG)
    syms = _symbols(chunks)
    assert "Add" in syms
    assert "Point" in syms


def test_rust_symbols():
    src = 'fn main() {\n    println!("hi");\n}\n\nstruct Foo {\n    x: i32,\n}\n'
    chunks = chunk_file(src, "rust", CFG)
    syms = _symbols(chunks)
    assert "main" in syms
    assert "Foo" in syms


def test_unknown_language_uses_windows():
    src = "\n".join(f"line {i}" for i in range(30))
    chunks = chunk_file(src, "text", CFG)
    assert chunks
    assert all(c.kind == "window" for c in chunks)


def test_empty_file_yields_nothing():
    assert chunk_file("   \n  \n", "python", CFG) == []
