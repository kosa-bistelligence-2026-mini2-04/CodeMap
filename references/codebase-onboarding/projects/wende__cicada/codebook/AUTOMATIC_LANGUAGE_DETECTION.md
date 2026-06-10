# Automatic Language Detection

Cicada automatically detects the programming language of your project by scanning for marker files in the repository root. This eliminates manual configuration and enables seamless indexing of multi-language codebases.

## Overview

When you run `cicada install` or `cicada index`, Cicada examines your repository for language-specific marker files like `mix.exs`, `pyproject.toml`, or `Cargo.toml`. Based on these markers, it selects the appropriate parser and indexer for your project's language.

## Supported Languages and Markers

| Language | Marker Files | Priority |
|----------|--------------|----------|
| **Python** | `pyproject.toml`, `setup.py`, `requirements.txt`, `Pipfile`, `poetry.lock` | 1 (highest) |
| **Elixir** | `mix.exs` | 2 |
| **Rust** | `Cargo.toml` | 3 |
| **Erlang** | `rebar.config`, `rebar.lock`, `erlang.mk`, or `*.erl` files in `src/` | 4 |
| **TypeScript** | `tsconfig.json` | 5 |
| **JavaScript** | `package.json` (without `tsconfig.json`) | 6 |
| **Go** | `go.mod` | 7 |
| **Scala** | `build.sbt` | 8 |
| **Java** | `build.gradle`, `build.gradle.kts`, `pom.xml` | 9 |
| **C++** | `CMakeLists.txt`, `Makefile`, `compile_commands.json` (with `*.cpp`/`*.cc` files) | 10 |
| **C** | `CMakeLists.txt`, `Makefile`, `compile_commands.json` (with `*.c` files) | 11 |
| **Ruby** | `Gemfile` | 12 |
| **C#** | `*.sln`, `*.csproj` | 13 |
| **Visual Basic** | `*.vbproj` | 14 |
| **Dart** | `pubspec.yaml` | 15 |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  Language Detection Flow                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. detect_project_language(repo_path)                          │
│                         │                                        │
│                         ▼                                        │
│  2. Check Python markers (pyproject.toml, setup.py, ...)        │
│         Found? → return "python"                                 │
│                         │                                        │
│                         ▼                                        │
│  3. Check Elixir marker (mix.exs)                               │
│         Found? → return "elixir"                                 │
│                         │                                        │
│                         ▼                                        │
│  4. Check other language markers...                             │
│                         │                                        │
│                         ▼                                        │
│  5. No markers found → raise ValueError                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LanguageRegistry                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LanguageRegistry.get_indexer(language)                         │
│         │                                                        │
│         ├─→ "elixir" → ElixirIndexer (tree-sitter)              │
│         ├─→ "python" → PythonSCIPIndexer (SCIP/Pyright)         │
│         ├─→ "rust"   → RustSCIPIndexer (rust-analyzer)          │
│         ├─→ "go"     → GoSCIPIndexer (gopls)                    │
│         └─→ ...                                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Location | Description |
|-----------|----------|-------------|
| `detect_project_language` | `cicada/setup.py:29` | Scans repo for marker files and returns language name |
| `LanguageRegistry` | `cicada/languages/__init__.py:16` | Factory for language-specific parsers and indexers |
| `LanguageRegistry.get_indexer` | `cicada/languages/__init__.py:109` | Returns appropriate indexer for detected language |
| `LanguageRegistry.register_language` | `cicada/languages/__init__.py:34` | Registers new language implementations |
| `UnsupportedProjectError` | `cicada/interactive_setup_helpers.py:12` | Exception for unrecognized project types |

---

## Detection Algorithm

The `detect_project_language` function checks markers in priority order:

```python
def detect_project_language(repo_path: Path) -> str:
    # Python markers (checked first - highest priority)
    python_markers = ["pyproject.toml", "setup.py", "requirements.txt", 
                      "Pipfile", "poetry.lock"]
    for marker in python_markers:
        if (repo_path / marker).exists():
            return "python"

    # Elixir marker
    if (repo_path / "mix.exs").exists():
        return "elixir"

    # Rust marker
    if (repo_path / "Cargo.toml").exists():
        return "rust"

    # ... additional languages checked in order

    # No recognized language
    raise ValueError("Could not detect project language...")
```

### Priority Rules

1. **Python takes precedence**: If both `pyproject.toml` and `mix.exs` exist, Python is detected
2. **TypeScript vs JavaScript**: `tsconfig.json` presence distinguishes TypeScript from JavaScript
3. **C vs C++**: Presence of `.cpp` or `.cc` files distinguishes C++ from C
4. **Erlang fallback**: If no `rebar.config`, checks for `*.erl` files in `src/` directory

---

## Language Registry

The `LanguageRegistry` class manages language implementations:

### Registering a Language

Languages are registered at module load time in `cicada/languages/__init__.py`:

```python
LanguageRegistry.register_language(
    language="elixir",
    parser_class="cicada.languages.elixir.parser.ElixirParser",
    indexer_class="cicada.indexer.ElixirIndexer",
    config=LanguageConfig.default_elixir(),
    formatter_class="cicada.languages.elixir.formatter.ElixirFormatter",
)
```

### Getting an Indexer

```python
from cicada.languages import LanguageRegistry

# Get indexer for detected language
indexer = LanguageRegistry.get_indexer("python")
indexer.incremental_index_repository(repo_path, output_path)
```

### SCIP-Based Languages

Languages that use SCIP (Source Code Intelligence Protocol) are only registered if the `cicada_scip` package is available. This includes: Python, TypeScript, JavaScript, Rust, Go, Java, Scala, C, C++, Ruby, C#, Visual Basic, and Dart.

---

## Usage

### Automatic Detection During Setup

```bash
# Cicada automatically detects the language
cicada install

# Output:
# ✓ Detected: Python project (pyproject.toml)
# Indexing repository...
```

### Checking Supported Languages

```python
from cicada.languages import LanguageRegistry

# List all supported languages
languages = LanguageRegistry.get_supported_languages()
# ['elixir', 'erlang', 'python', 'typescript', ...]

# Check if a language is supported
is_python_supported = LanguageRegistry.is_language_supported("python")
```

### Handling Unsupported Projects

```python
from cicada.setup import detect_project_language

try:
    language = detect_project_language(repo_path)
except ValueError as e:
    print(f"Error: {e}")
    # "Could not detect project language in /path/to/repo
    #  Expected one of: Python (pyproject.toml), Elixir (mix.exs), ..."
```

---

## Error Handling

When no recognized marker file is found, Cicada raises a `ValueError` with a helpful message listing all supported project types:

```
Could not detect project language in /path/to/repo
Expected one of: Python (pyproject.toml), Elixir (mix.exs), Rust (Cargo.toml), 
Erlang (rebar.config), TypeScript/JavaScript (package.json), Go (go.mod), 
Java (build.gradle/pom.xml), Scala (build.sbt), C/C++ (CMakeLists.txt/Makefile), 
Ruby (Gemfile), C# (*.csproj), VB (*.vbproj), Dart (pubspec.yaml)
```

---

## File Reference

| File | Description |
|------|-------------|
| `cicada/setup.py` | Contains `detect_project_language` function |
| `cicada/languages/__init__.py` | LanguageRegistry class and language registration |
| `cicada/languages/base.py` | BaseParser and BaseIndexer abstract classes |
| `cicada/interactive_setup_helpers.py` | UnsupportedProjectError exception |
| `cicada/parsing/language_config.py` | LanguageConfig class for language settings |
| `tests/languages/python/test_python_support.py` | Tests for language detection |

---

## Related Features

- **[AST-Level Indexing](AST_INDEXING.md)**: Language-specific parsing after detection
- **[Incremental Indexing](INCREMENTAL_INDEXING.md)**: Fast re-indexing for detected language
- **Editor Integration**: Uses detected language for MCP server configuration
