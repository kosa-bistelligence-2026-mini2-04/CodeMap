# AST-Level Indexing

Cicada uses Abstract Syntax Tree (AST) parsing to extract semantic information from source code. This document describes how AST indexing works for each supported language.

## Overview

AST indexing is the core mechanism that powers Cicada's code intelligence features. Rather than relying on text-based pattern matching, Cicada parses source code into structured syntax trees, enabling accurate extraction of:

- Module/class definitions and their documentation
- Function/method signatures with parameters and types
- Dependencies (imports, aliases, requires)
- Function calls and their call sites
- String literals and inline comments (for keyword search)

## Architecture

### Parsing Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                        Language Parsers                          │
├─────────────────┬─────────────────────┬────────────────────────┤
│  ElixirParser   │   PythonSCIPIndexer │     ErlangParser       │
│  (tree-sitter)  │   (SCIP/Pyright)    │     (tree-sitter)      │
└────────┬────────┴──────────┬──────────┴───────────┬────────────┘
         │                   │                      │
         ▼                   ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BaseIndexer                                 │
│  • Universal enrichment pipeline                                 │
│  • Keyword extraction & expansion                                │
│  • Timestamp computation                                         │
│  • Co-change analysis                                            │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Index Storage                              │
│                      (index.json)                                │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Location | Description |
|-----------|----------|-------------|
| `BaseParser` | `cicada/parsing/base_parser.py` | Abstract interface for language parsers |
| `BaseIndexer` | `cicada/parsing/base_indexer.py` | Universal indexer with shared enrichment pipeline |
| `ElixirParser` | `cicada/languages/elixir/parser.py` | Tree-sitter based Elixir parser |
| `ElixirIndexer` | `cicada/indexer.py` | Elixir-specific indexer with incremental support |
| `PythonSCIPIndexer` | `cicada/languages/python/indexer.py` | SCIP-based Python indexer |
| `ErlangParser` | `cicada/languages/erlang/parser.py` | Tree-sitter based Erlang parser |
| `ErlangIndexer` | `cicada/languages/erlang/indexer.py` | Erlang-specific indexer |

---

## Language-Specific Implementations

### Elixir (Tree-sitter)

Elixir uses tree-sitter for AST parsing, with specialized extractors for different code elements.

#### Parser Entry Point

**File:** `cicada/languages/elixir/parser.py`

The `ElixirParser` class initializes tree-sitter with the Elixir grammar and coordinates extraction:

```
ElixirParser.parse_file(file_path)
    │
    ├── Parse source with tree-sitter
    ├── extract_modules() → Module definitions with do_blocks
    ├── extract_functions() → def/defp/test declarations
    ├── extract_specs() → @spec type annotations
    ├── extract_docs() → @doc/@moduledoc attributes
    ├── match_specs_to_functions() → Associate specs with functions
    ├── match_docs_to_functions() → Associate docs with functions
    ├── extract_aliases() → alias declarations
    ├── extract_imports() → import declarations
    ├── extract_requires() → require declarations
    ├── extract_uses() → use declarations
    ├── extract_behaviours() → @behaviour attributes
    ├── extract_function_calls() → Function call sites
    └── extract_value_mentions() → Module value mentions
```

#### Extractors

All extractors are located in `cicada/languages/elixir/extractors/`:

| File | Functions | Description |
|------|-----------|-------------|
| `module.py` | `extract_modules`, `extract_moduledoc` | Extracts `defmodule` declarations and module docs |
| `function.py` | `extract_functions` | Extracts `def`, `defp`, and `test` declarations with args, guards, and `@impl` |
| `spec.py` | `extract_specs`, `match_specs_to_functions` | Extracts `@spec` type annotations |
| `doc.py` | `extract_docs`, `match_docs_to_functions` | Extracts `@doc` attributes and examples |
| `dependency.py` | `extract_aliases`, `extract_imports`, `extract_requires`, `extract_uses`, `extract_behaviours` | Extracts module dependencies |
| `call.py` | `extract_function_calls`, `extract_value_mentions` | Extracts call sites and module references |
| `string.py` | `StringExtractor` | Extracts string literals for keyword indexing |
| `comment.py` | `CommentExtractor` | Extracts inline comments for keyword indexing |

#### Extracted Data Structure

For each Elixir module, the parser produces:

```json
{
  "module": "MyApp.User",
  "line": 1,
  "moduledoc": "User management module.",
  "functions": [
    {
      "name": "create",
      "arity": 2,
      "args": ["name", "email"],
      "guards": [],
      "full_name": "create/2",
      "line": 10,
      "signature": "def create",
      "type": "def",
      "visibility": "public",
      "impl": false,
      "doc": "Creates a new user.",
      "args_with_types": [
        {"name": "name", "type": "String.t()"},
        {"name": "email", "type": "String.t()"}
      ],
      "return_type": "{:ok, User.t()} | {:error, term()}"
    }
  ],
  "aliases": {"Repo": "MyApp.Repo"},
  "imports": ["Ecto.Query"],
  "requires": ["Logger"],
  "uses": ["GenServer"],
  "behaviours": ["GenServer"],
  "calls": [
    {"module": "Repo", "function": "insert", "arity": 1, "line": 15}
  ],
  "value_mentions": ["MyApp.Config"]
}
```

---

### Python (SCIP/Pyright)

Python uses SCIP (Source Code Intelligence Protocol) for semantic indexing. SCIP provides type-aware analysis powered by Pyright.

#### Indexer Entry Point

**File:** `cicada/languages/python/indexer.py`

The `PythonSCIPIndexer` coordinates the Python indexing pipeline:

```
PythonSCIPIndexer.incremental_index_repository(repo_path)
    │
    ├── Ensure scip-python is installed
    ├── Run scip-python indexer → generates .scip file
    ├── SCIPReader.read_index() → Parse protobuf format
    ├── SCIPConverter.convert() → Transform to Cicada format
    ├── _copy_unchanged_keywords() → Reuse keywords from unchanged modules
    ├── _run_enrichment_pipeline() → Keywords, timestamps, co-change
    └── Save index.json
```

#### SCIP Protocol

SCIP provides rich semantic information:

- **Symbol resolution**: Fully qualified symbol names
- **Type information**: From Pyright's type inference
- **Cross-references**: Definitions and usages linked
- **Documentation**: Docstrings extracted

**Key files:**
- `cicada/languages/scip/reader.py` - Re-exports `SCIPReader` from `cicada_scip`
- `cicada/languages/scip/converter.py` - Re-exports `SCIPConverter` from `cicada_scip`

#### Symbol Type Detection

**File:** `cicada/languages/python/symbol_types.py`

Python SCIP symbols use descriptor patterns to identify symbol types:

| Pattern | Type | Example |
|---------|------|---------|
| `module/:` | module | `calculator/__init__:` |
| `Class#` | class | `calculator/Calculator#` |
| `Class#method().` | method | `calculator/Calculator#add().` |
| `function().` | function | `calculator/helper_function().` |
| `Class#attr.` | attribute | `calculator/Calculator#value.` |

#### String Extraction

**File:** `cicada/languages/python/string_extractor.py`

Uses Python's built-in `ast` module to extract string literals:

- Excludes docstrings (first statement in module/class/function)
- Handles f-strings (extracts static parts only)
- Tracks function context for each string

#### Alias Extraction

**File:** `cicada/languages/python/alias_extractor.py`

Extracts import aliases using Python's `ast` module:

```python
import operations as ops    # {"ops": "operations"}
from utils import avg       # {"avg": "utils"}
```

---

### Erlang (Tree-sitter)

Erlang uses tree-sitter with EDoc comment extraction for documentation.

#### Parser Entry Point

**File:** `cicada/languages/erlang/parser.py`

The `ErlangParser` extracts modules and functions from Erlang source:

```
ErlangParser.parse_file(file_path)
    │
    ├── Parse source with tree-sitter
    ├── Extract -module(name) attribute → module name
    ├── Extract -export([...]) attribute → exported functions
    ├── Extract fun_decl nodes → function definitions
    ├── extract_docs_from_comments() → EDoc comments
    └── match_docs_to_declarations() → Associate docs with functions
```

#### EDoc Extraction

**File:** `cicada/languages/erlang/extractors/doc.py`

Erlang uses EDoc format for documentation in comments:

```erlang
%% @doc Creates a new user.
%% @param Name The user's name
%% @returns {ok, User} | {error, Reason}
create(Name, Email) -> ...
```

The extractor:
1. Collects all comment nodes from the AST
2. Groups consecutive comment lines into blocks
3. Parses EDoc tags (`@doc`, `@param`, `@returns`)
4. Associates docs with following declarations by proximity

#### Exported Functions

Exports are parsed from `-export([...])` attributes:

```erlang
-export([create/2, update/3]).
```

Functions are marked as `def` (public) or `defp` (private) based on export list membership.

---

## Universal Enrichment Pipeline

After language-specific parsing, all indexers run the same enrichment pipeline defined in `BaseIndexer._run_enrichment_pipeline()`:

### Phase 1: Keyword Extraction & Expansion

Keywords are extracted from:
- Module documentation (`moduledoc`)
- Function documentation (`doc`)
- Module/function names
- String literals (`string_keywords`)
- Inline comments (`comment_keywords`)

The pipeline uses streaming parallel expansion:

```
Sequential Extraction → Parallel Expansion (ThreadPoolExecutor)
     │                          │
     ├── Extract keywords       ├── Expand each keyword set
     ├── Submit to pipeline     ├── Add synonyms/related terms
     └── Continue to next       └── Update target dict
```

### Phase 2: Timestamp Computation

Git history is analyzed to compute:
- `created_at`: When the function was first introduced
- `last_modified_at`: Most recent modification date
- `last_modified_sha`: Commit hash of last modification
- `modification_count`: Total number of modifications
- `modification_frequency`: How often the function changes

### Phase 3: Co-change Analysis

Identifies files and functions that frequently change together:
- `cochange_files`: Files that change with this module
- `cochange_functions`: Functions that change with this function

### Phase 4: Co-occurrence Matrix

Builds a matrix of keyword relationships based on which keywords appear together in the same modules/functions.

---

## Incremental Indexing

Cicada supports incremental indexing for efficient updates:

1. **File Hashing**: SHA-256 hashes are computed for all source files
2. **Change Detection**: Compares current hashes with stored hashes
3. **Selective Processing**: Only new/modified files are parsed
4. **Keyword Reuse**: Unchanged modules retain their keywords
5. **Timestamp Reuse**: Unchanged functions retain their timestamps
6. **Index Merging**: New data is merged with existing index

**Hash Storage:** `~/.cicada/projects/<repo_hash>/hashes.json`

---

## Index Output Format

The final index is stored as JSON with this structure:

```json
{
  "modules": {
    "ModuleName": {
      "file": "lib/module.ex",
      "line": 1,
      "moduledoc": "Module documentation",
      "functions": [...],
      "keywords": {"user": 1.5, "auth": 1.2},
      "string_keywords": {"error": 1.3},
      "cochange_files": [{"file": "lib/related.ex", "count": 5}],
      "aliases": {},
      "imports": [],
      "requires": [],
      "uses": [],
      "calls": []
    }
  },
  "metadata": {
    "indexed_at": "2025-01-15T10:30:00",
    "total_modules": 100,
    "total_functions": 500,
    "repo_path": "/path/to/repo",
    "cicada_version": "0.6.0"
  },
  "cochange_metadata": {...},
  "cooccurrences": {...}
}
```

---

## File Reference

### Core Parsing Infrastructure

| File | Description |
|------|-------------|
| `cicada/parsing/base_parser.py` | Abstract base class for language parsers |
| `cicada/parsing/base_indexer.py` | Universal indexer with enrichment pipeline |

### Elixir

| File | Description |
|------|-------------|
| `cicada/languages/elixir/parser.py` | Main Elixir parser using tree-sitter |
| `cicada/languages/elixir/extractors/__init__.py` | Exports all extractors |
| `cicada/languages/elixir/extractors/module.py` | Module extraction |
| `cicada/languages/elixir/extractors/function.py` | Function extraction |
| `cicada/languages/elixir/extractors/spec.py` | Type spec extraction |
| `cicada/languages/elixir/extractors/doc.py` | Documentation extraction |
| `cicada/languages/elixir/extractors/dependency.py` | Dependency extraction |
| `cicada/languages/elixir/extractors/call.py` | Call site extraction |
| `cicada/languages/elixir/extractors/string.py` | String literal extraction |
| `cicada/languages/elixir/extractors/comment.py` | Comment extraction |
| `cicada/languages/elixir/extractors/base.py` | Shared utilities |
| `cicada/languages/elixir/extractors/common.py` | Common traversal helpers |
| `cicada/indexer.py` | ElixirIndexer with incremental support |

### Python

| File | Description |
|------|-------------|
| `cicada/languages/python/indexer.py` | SCIP-based Python indexer |
| `cicada/languages/python/symbol_types.py` | Symbol type detection |
| `cicada/languages/python/string_extractor.py` | String literal extraction |
| `cicada/languages/python/alias_extractor.py` | Import alias extraction |
| `cicada/languages/python/scip_installer.py` | SCIP-python installation |

### Erlang

| File | Description |
|------|-------------|
| `cicada/languages/erlang/parser.py` | Tree-sitter based Erlang parser |
| `cicada/languages/erlang/indexer.py` | Erlang indexer |
| `cicada/languages/erlang/extractors/doc.py` | EDoc extraction |

### SCIP Infrastructure

| File | Description |
|------|-------------|
| `cicada/languages/scip/reader.py` | SCIP file reader |
| `cicada/languages/scip/converter.py` | SCIP to Cicada format converter |
