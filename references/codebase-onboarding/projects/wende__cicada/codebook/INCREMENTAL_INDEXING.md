# Incremental Indexing

Cicada's incremental indexing system dramatically speeds up reindexing by only processing files that have changed since the last run. Instead of re-parsing your entire codebase on every index operation, Cicada uses MD5 file hashing to detect which files are new, modified, or deleted, then processes only those changes.

## Overview

When you first index a repository, Cicada performs a full index and computes MD5 hashes for each processed file. On subsequent runs, it compares current file hashes against stored hashes to identify:

- **New files**: Files that didn't exist in the previous index
- **Modified files**: Files whose content hash changed
- **Deleted files**: Files that existed before but no longer exist

Only new and modified files are re-parsed; deleted files are removed from the index. This results in 10-25x faster reindexing for typical development workflows.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Incremental Indexing Flow                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Load existing index.json and hashes.json                    │
│                         │                                        │
│                         ▼                                        │
│  2. Scan current files and compute hashes                       │
│                         │                                        │
│                         ▼                                        │
│  3. detect_file_changes() → (new, modified, deleted)            │
│                         │                                        │
│                         ▼                                        │
│  4. Parse only new + modified files                             │
│                         │                                        │
│                         ▼                                        │
│  5. merge_indexes_incremental() → combined index                │
│                         │                                        │
│                         ▼                                        │
│  6. Save updated index.json and hashes.json                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Location | Description |
|-----------|----------|-------------|
| `compute_file_hash` | `cicada/utils/hash_utils.py:15` | Computes MD5 hash of a file's content |
| `detect_file_changes` | `cicada/utils/hash_utils.py:104` | Compares hashes to find new, modified, deleted files |
| `load_file_hashes` | `cicada/utils/hash_utils.py:46` | Loads stored hashes from hashes.json |
| `save_file_hashes` | `cicada/utils/hash_utils.py:73` | Saves hashes to hashes.json |
| `compute_hashes_for_files` | `cicada/utils/hash_utils.py:161` | Batch compute hashes for multiple files |
| `merge_indexes_incremental` | `cicada/utils/index_utils.py:288` | Merges old index with new changes |
| `ElixirIndexer.incremental_index_repository` | `cicada/indexer.py:958` | Main entry point for Elixir incremental indexing |
| `PythonSCIPIndexer.incremental_index_repository` | `cicada/languages/python/indexer.py:193` | Python incremental indexing |

---

## Hash Storage

File hashes are stored in `~/.cicada/projects/<repo_hash>/hashes.json`:

```json
{
  "version": "1.0",
  "hashes": {
    "lib/my_app/user.ex": "5d41402abc4b2a76b9719d911017c592",
    "lib/my_app/account.ex": "7d793037a0760186574b0282f2f435e7",
    "test/my_app/user_test.exs": "1bc29b36f623ba82aaf6724fd3b16718"
  },
  "last_updated": "2025-10-28T20:15:42Z"
}
```

### Why MD5?

MD5 is used for change detection because:
- Built into Python (no extra dependencies)
- Fast (~400 MB/s for typical files)
- Collision risk is negligible for change detection (not security)
- Shorter hashes than SHA256 (32 vs 64 chars)

---

## Change Detection Algorithm

The `detect_file_changes` function compares current files against stored hashes:

```python
def detect_file_changes(
    files: list[str],           # Current files in repo
    old_hashes: dict[str, str], # Previous file hashes
    repo_path: str | None = None
) -> tuple[list[str], list[str], list[str]]:
    """
    Returns: (new_files, modified_files, deleted_files)
    """
    # 1. Deleted = in old_hashes but not in files
    deleted_files = old_hashes.keys() - set(files)

    # 2. New = in files but not in old_hashes
    # 3. Modified = hash differs from old_hashes
    for file_path in files:
        if file_path not in old_hashes:
            new_files.append(file_path)
        else:
            current_hash = compute_file_hash(file_path)
            if current_hash != old_hashes[file_path]:
                modified_files.append(file_path)

    return new_files, modified_files, deleted_files
```

---

## Index Merging

After processing changed files, `merge_indexes_incremental` combines results:

1. **Keep unchanged modules**: Modules from old index whose files weren't deleted
2. **Add/update changed modules**: Modules from new index (overwrites old)
3. **Remove deleted modules**: Modules whose files were deleted
4. **Update metadata**: Recalculate counts and timestamp

```python
def merge_indexes_incremental(
    old_index: dict[str, Any],
    new_index: dict[str, Any],
    deleted_files: list[str],
) -> dict[str, Any]:
    merged = {"modules": {}, "metadata": {}}
    deleted_set = set(deleted_files)

    # Keep modules from old_index that aren't deleted
    for module_name, module_data in old_index["modules"].items():
        if module_data.get("file", "") not in deleted_set:
            merged["modules"][module_name] = module_data

    # Add/update modules from new_index
    merged["modules"].update(new_index["modules"])

    # Update stats
    stats = get_index_stats(merged)
    merged["metadata"]["total_modules"] = stats["total_modules"]
    merged["metadata"]["total_functions"] = stats["total_functions"]

    return merged
```

---

## Usage

### CLI Commands

```bash
# First run: full index with hash computation
cicada index --force

# Subsequent runs: automatic incremental indexing
cicada index                    # Only processes changed files

# Force full reindex (ignore hashes)
cicada index --full
```

### Programmatic Usage

```python
from cicada.indexer import ElixirIndexer

indexer = ElixirIndexer()

# Incremental by default
index = indexer.incremental_index_repository(
    repo_path="/path/to/repo",
    output_path="~/.cicada/projects/<hash>/index.json",
    extract_keywords=True,
    force_full=False  # Set to True for full reindex
)
```

---

## Interrupt Safety

Incremental indexing includes interrupt safety:

1. **Signal handlers** catch Ctrl-C (SIGINT) and SIGTERM
2. **Current file finishes** processing gracefully
3. **Partial progress saved** to disk
4. **Next run continues** from where you left off
5. **Double Ctrl-C** force quits (may lose current file)

---

## Performance

### Benchmark: 200-file Elixir codebase, 5 files changed

| Indexing Type | Time | Speedup |
|--------------|------|---------|
| Full index | 12.3s | - |
| Incremental | 0.8s | **15.4x** |

### With Keyword Extraction

| Indexing Type | Time | Speedup |
|--------------|------|---------|
| Full + keywords | 48.7s | - |
| Incremental + keywords | 2.1s | **23.2x** |

---

## File Reference

| File | Description |
|------|-------------|
| `cicada/utils/hash_utils.py` | MD5 hashing and change detection utilities |
| `cicada/utils/index_utils.py` | Index merging and incremental merge logic |
| `cicada/indexer.py` | ElixirIndexer with incremental support |
| `cicada/languages/python/indexer.py` | PythonSCIPIndexer with incremental support |
| `cicada/languages/erlang/indexer.py` | ErlangIndexer with incremental support |
| `cicada/parsing/base_indexer.py` | Base class defining incremental interface |
| `packages/cicada-core/src/cicada_core/utils/hash_utils.py` | Core package hash utilities |

---

## Watch Mode

Watch mode automatically triggers incremental reindexing whenever files change in your repository. It monitors the filesystem for changes and runs incremental indexing with a configurable debounce interval.

### CLI Usage

```bash
# Start watching for changes (default 2s debounce)
cicada watch

# Custom debounce interval
cicada watch --debounce 5

# Watch with specific indexing mode
cicada watch --keywords
cicada watch --embeddings

# Quiet mode (suppress progress output)
cicada watch --quiet
```

### How It Works

1. **File Monitoring**: Watches source files for changes using filesystem events
2. **Debouncing**: Waits for a configurable interval after the last change before reindexing
3. **Incremental Update**: Only reprocesses changed files using the incremental indexing system
4. **Background Process**: Can run as a linked background process with the MCP server

### MCP Server Integration

When the MCP server starts, it can automatically spawn a watch process:

```python
from cicada.watch_manager import start_watch_process, stop_watch_process

# Start watching
start_watch_process(
    repo_path="/path/to/repo",
    indexing_mode="keywords",
    debounce=2.0
)

# Stop watching
stop_watch_process()
```

### Key Components

| Component | Location | Description |
|-----------|----------|-------------|
| `WatchProcessManager` | `cicada/watch_manager.py:20` | Manages the watch subprocess lifecycle |
| `handle_watch` | `cicada/commands.py:1019` | CLI command handler for `cicada watch` |
| `start_watch_process` | `cicada/watch_manager.py:291` | Convenience function to start watching |
| `stop_watch_process` | `cicada/watch_manager.py:319` | Stops the global watch process |

---

## File Reference

| File | Description |
|------|-------------|
| `cicada/utils/hash_utils.py` | MD5 hashing and change detection utilities |
| `cicada/utils/index_utils.py` | Index merging and incremental merge logic |
| `cicada/indexer.py` | ElixirIndexer with incremental support |
| `cicada/languages/python/indexer.py` | PythonSCIPIndexer with incremental support |
| `cicada/languages/erlang/indexer.py` | ErlangIndexer with incremental support |
| `cicada/parsing/base_indexer.py` | Base class defining incremental interface |
| `cicada/watch_manager.py` | Watch process management for auto-reindexing |
| `packages/cicada-core/src/cicada_core/utils/hash_utils.py` | Core package hash utilities |

---

## Related Features

- **[AST-Level Indexing](AST_INDEXING.md)**: The parsing that incremental indexing accelerates
- **Keyword Extraction**: Benefits most from incremental indexing due to NLP overhead
