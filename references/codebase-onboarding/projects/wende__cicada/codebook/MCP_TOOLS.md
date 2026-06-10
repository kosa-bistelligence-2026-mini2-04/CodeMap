# MCP Tools

Cicada exposes its code intelligence capabilities through the Model Context Protocol (MCP), providing AI assistants with powerful tools for code exploration, analysis, and discovery.

## Overview

The MCP (Model Context Protocol) is a standardized interface for AI assistants to interact with external tools. Cicada implements 7 MCP tools organized into three categories:

1. **Discovery Tools**: Find code by keywords, patterns, or semantic search
   - `query` - Primary entry point for all code exploration
   - `expand_result` - Drill down into specific results

2. **Analysis Tools**: Deep-dive into modules and functions
   - `search_module` - Complete module API with dependency analysis
   - `search_function` - Function definitions and call sites

3. **Utility Tools**: Index management and advanced queries
   - `git_history` - Git history and PR attribution (see [GIT_HISTORY.md](GIT_HISTORY.md))
   - `refresh_index` - Force index refresh
   - `query_jq` - Advanced jq queries against the index

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         MCP Client                               │
│               (Claude Code, Cursor, VS Code)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │ MCP Protocol
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       CicadaServer                               │
│                    (cicada/mcp/server.py)                        │
│  • Tool definitions                                              │
│  • Request logging                                               │
│  • Error handling                                                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       ToolRouter                                 │
│                   (cicada/mcp/router.py)                         │
│  • Argument validation                                           │
│  • Tool routing                                                  │
│  • Handler coordination                                          │
└──────┬──────────┬──────────┬──────────┬──────────┬─────────────┘
       │          │          │          │          │
       ▼          ▼          ▼          ▼          ▼
┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Module   │ │ Function │ │   Git    │ │   PR     │ │ Analysis │
│ Handler  │ │ Handler  │ │ Handler  │ │ Handler  │ │ Handler  │
└──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘
       │          │          │          │          │
       └──────────┴──────────┴──────────┴──────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                       IndexManager                               │
│                (cicada/mcp/handlers/index_manager.py)            │
│  • Index loading & caching                                       │
│  • Staleness detection                                           │
│  • Auto-refresh                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Location | Description |
|-----------|----------|-------------|
| `CicadaServer` | `cicada/mcp/server.py` | MCP server implementation |
| `ToolRouter` | `cicada/mcp/router.py` | Routes tool calls to handlers |
| `ModuleSearchHandler` | `cicada/mcp/handlers/module_handlers.py` | Module search and usage analysis |
| `FunctionSearchHandler` | `cicada/mcp/handlers/function_handlers.py` | Function search and call sites |
| `GitHistoryHandler` | `cicada/mcp/handlers/git_handlers.py` | Git history queries |
| `PRHistoryHandler` | `cicada/mcp/handlers/pr_handlers.py` | PR lookup and enrichment |
| `AnalysisHandler` | `cicada/mcp/handlers/analysis_handlers.py` | Query orchestration and jq queries |
| `IndexManager` | `cicada/mcp/handlers/index_manager.py` | Index lifecycle management |
| `get_tool_definitions` | `cicada/mcp/tools.py` | Tool schema definitions |

---

## Tool Reference

### query

**Primary entry point for all code exploration and discovery.**

The `query` tool is the "Google for code" - start here for any search task. It intelligently detects whether you're searching by keywords or patterns and combines results from multiple sources.

#### Smart Auto-Detection

| Input | Detection | Behavior |
|-------|-----------|----------|
| `['authentication', 'login']` | Keywords | Semantic search across docs and strings |
| `'MyApp.User.create*'` | Pattern | Exact pattern matching with wildcards |
| `['oauth', 'MyApp.Auth.*']` | Mixed | Combines keyword and pattern search |

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string \| string[] | Keywords, patterns, or mixed (required) |
| `scope` | `'all'` \| `'public'` \| `'private'` | Filter by visibility (default: 'all') |
| `recent` | boolean | Filter to last 14 days (default: false) |
| `result_type` | `'all'` \| `'modules'` \| `'functions'` | Filter result type (default: 'all') |
| `match_source` | `'all'` \| `'docs'` \| `'strings'` \| `'comments'` | Where to search (default: 'all') |
| `glob` | string | Glob pattern for file path filtering |
| `path` | string | Base directory (prepended to glob) |
| `type` | string | File type shorthand (e.g., 'py', 'ex', 'ts') |
| `max_results` | integer | Maximum results (default: 10) |
| `offset` | integer | Skip first N results for pagination |
| `show_snippets` | boolean | Show code context (default: false) |
| `verbose` | boolean | Full docs and confidence scores |

#### Output Features

- **Match indicators**: `(d)` docs, `(s)` strings, `(d+s)` both
- **Smart suggestions**: Recommends next tools to use
- **Recency labels**: Shows how recently code was modified

#### Examples

```python
# Find authentication code
query(['authentication', 'login'])

# Find functions in auth module
query('MyApp.Auth.*')

# Find recent SQL queries in strings
query(['sql', 'select'], match_source='strings', recent=True)

# Find code in specific directory
query('create_user', path='lib/accounts', type='ex')
```

---

### search_module

**View a module's complete API and dependency relationships.**

Use after `query` discovers relevant modules. Shows all functions with signatures, docs, and analyzes what calls this module and what it depends on.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `module_name` | string | Module name or pattern (supports `*` and `\|`) |
| `file_path` | string | Alternative: path to file containing module |
| `type` | `'public'` \| `'private'` \| `'all'` | Which functions to show (default: 'public') |
| `what_calls_it` | boolean | Show where this module is used (default: false) |
| `usage_type` | `'source'` \| `'tests'` \| `'all'` | Filter usage by file type |
| `what_it_calls` | boolean | Show module dependencies (default: false) |
| `dependency_depth` | integer | Transitive dependency depth (default: 1) |
| `verbose` | boolean | Include docs, specs, moduledoc |
| `glob` | string | Filter results by file path |
| `head_limit` | integer | Max results for wildcards (default: 20) |

#### Dependency Analysis

**what_calls_it=true** - Critical for impact analysis before refactoring:
- Shows all files that alias, import, require, or use the module
- Lists all function call sites with file:line references
- Filters by source vs test files

**what_it_calls=true** - Understand module dependencies:
- Lists all modules this module depends on
- Groups by internal (same project) vs external (libraries)
- Optional: show which functions use which dependencies

#### Examples

```python
# View module API
search_module('MyApp.Accounts.User')

# Check impact before refactoring
search_module('MyApp.Auth', what_calls_it=True)

# Understand dependencies
search_module('MyApp.Auth', what_it_calls=True, dependency_depth=2)

# Wildcard search
search_module('MyApp.Accounts.*', head_limit=10)
```

---

### search_function

**Find function definitions and all call sites.**

Use after `query` finds functions you want to analyze. Shows definition location, signature, documentation, and everywhere the function is called.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `function_name` | string | Function pattern (required, supports `*`, `\|`, arity) |
| `module_path` | string | Optional module prefix |
| `what_calls_it` | boolean | Show call sites (default: true) |
| `what_it_calls` | boolean | Show function's dependencies (default: false) |
| `include_usage_examples` | boolean | Show code snippets of calls |
| `max_examples` | integer | Max code examples (default: 5) |
| `usage_type` | `'source'` \| `'tests'` \| `'all'` | Filter call sites by file type |
| `changed_since` | string | Filter by modification time |
| `verbose` | boolean | Include docs and specs |
| `glob` | string | Filter by file path |

#### Pattern Syntax

| Pattern | Matches |
|---------|---------|
| `create_user` | Any function named `create_user` |
| `MyApp.User.create_user` | Specific module.function |
| `create_user/2` | With specific arity |
| `create*` | Wildcard prefix |
| `create*\|update*` | OR patterns |
| `lib/accounts/*.ex:create*` | File-scoped search |

#### changed_since Formats

| Format | Example | Description |
|--------|---------|-------------|
| Relative days | `7d` | Last 7 days |
| Relative weeks | `2w` | Last 2 weeks |
| ISO date | `2024-12-01` | Since specific date |
| Git ref | `v1.0.0` | Since git tag/commit |

#### Examples

```python
# Find function and its call sites
search_function('create_user')

# See what a function calls
search_function('handle_request', what_it_calls=True)

# Find recently changed functions
search_function('*', changed_since='7d', glob='lib/accounts/**')

# See only test usages
search_function('create_user', usage_type='tests')
```

---

### expand_result

**Drill down into a specific query result.**

Convenience wrapper that auto-detects whether you're expanding a module or function and calls the appropriate handler. Perfect for following query suggestions.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `identifier` | string | Module or function reference (required) |
| `type` | `'auto'` \| `'module'` \| `'function'` | Force type detection (default: 'auto') |
| `include_code` | boolean | Include code snippets (default: true) |
| `what_calls_it` | boolean | Show usages/call sites (default: true) |
| `what_it_calls` | boolean | Show dependencies (default: false) |

#### Auto-Detection

| Identifier | Detected As |
|------------|-------------|
| `MyApp.Auth` | Module |
| `MyApp.Auth.verify_token/2` | Function |
| `verify_token` | Function |

#### Examples

```python
# Expand from query result
expand_result('MyApp.Auth.verify_token/2')

# Force module expansion
expand_result('MyApp.Auth', type='module')

# Include dependency analysis
expand_result('MyApp.Auth', what_it_calls=True)
```

---

### refresh_index

**Force refresh the code index.**

Use when auto-refresh hasn't caught recent edits, or when query results seem stale.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `force_full` | boolean | Full reindex vs incremental (default: false) |

#### Refresh Modes

| Mode | Speed | Use Case |
|------|-------|----------|
| Incremental | ~1-2s | Default, only changed files |
| Full | Slower | When incremental seems stale |

#### Examples

```python
# Quick incremental refresh
refresh_index()

# Full rebuild
refresh_index(force_full=True)
```

---

### query_jq

**Execute custom jq queries against the index.**

Advanced tool for custom analysis, debugging, and exploring data not covered by specialized tools.

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | jq query expression (required) |
| `format` | `'compact'` \| `'pretty'` | Output format (default: 'compact') |
| `sample` | boolean | Limit to first 5 items (default: false) |

#### Index Schema

```json
{
  "modules": {
    "<module_name>": {
      "file": "lib/my_app/user.ex",
      "line": 1,
      "moduledoc": "Module documentation...",
      "functions": [
        {
          "name": "create_user",
          "arity": 2,
          "line": 15,
          "type": "def",
          "doc": "Function documentation...",
          "signature": "create_user(attrs, opts)",
          "keywords": {...},
          "string_keywords": {...}
        }
      ],
      "keywords": {...},
      "aliases": [...],
      "imports": [...]
    }
  },
  "metadata": {
    "indexed_at": "2025-01-15T10:30:00Z",
    "total_modules": 150,
    "total_functions": 1200
  }
}
```

#### Schema Discovery

Append `| schema` to any query to see available fields:

```python
query_jq('.modules | schema')
query_jq('.modules[].functions | schema')
```

#### Common Queries

```python
# List all modules
query_jq('.modules | keys')

# Count functions per module
query_jq('.modules | to_entries | map({name: .key, count: (.value.functions | length)})')

# Find test modules
query_jq('.modules | to_entries | map(select(.value.file | test("test")))')

# Find functions by arity
query_jq('[.modules[].functions[] | select(.arity == 2)]')

# Get index metadata
query_jq('.metadata')

# Preview with sample mode
query_jq('.modules | to_entries', sample=True)
```

#### Safety Limits

- Maximum query length: 10,000 characters
- Maximum nesting depth: 50 levels
- Result truncation: 1MB
- Early size warnings for large results (>500KB)

---

### git_history

**Unified tool for all git history queries.**

See [GIT_HISTORY.md](GIT_HISTORY.md) for comprehensive documentation on git history and PR indexing features.

---

## Suggested Workflow

1. **Start with `query`** - Find relevant code by keywords or patterns
2. **Follow suggestions** - Query results include next-step recommendations
3. **Use `expand_result`** - Drill into specific results
4. **Deep-dive with specialized tools**:
   - `search_module` for module API and dependencies
   - `search_function` for call sites and usage
   - `git_history` for authorship and PR attribution
5. **Use `refresh_index`** if results seem stale

---

## Output Modes

All tools support two output modes:

| Mode | Description | Use Case |
|------|-------------|----------|
| Compact (default) | Essential info only, minimal tokens | Normal queries |
| Verbose | Full docs, specs, examples | Deep analysis |

Enable verbose mode with `verbose=true` on any tool.

---

## File Reference

### Core MCP Infrastructure

| File | Description |
|------|-------------|
| `cicada/mcp/server.py` | MCP server implementation with tool definitions |
| `cicada/mcp/router.py` | Routes tool calls to appropriate handlers |
| `cicada/mcp/tools.py` | Tool schema definitions |
| `cicada/mcp/entry.py` | CLI entry point for MCP server |

### Tool Handlers

| File | Description |
|------|-------------|
| `cicada/mcp/handlers/module_handlers.py` | Module search and usage analysis |
| `cicada/mcp/handlers/function_handlers.py` | Function search and call sites |
| `cicada/mcp/handlers/git_handlers.py` | Git history queries |
| `cicada/mcp/handlers/pr_handlers.py` | PR lookup and enrichment |
| `cicada/mcp/handlers/analysis_handlers.py` | Query orchestration and jq |
| `cicada/mcp/handlers/index_manager.py` | Index lifecycle management |

### Query Infrastructure

| File | Description |
|------|-------------|
| `cicada/query/orchestrator.py` | Query execution and result ranking |
| `cicada/query/types.py` | Query domain types and options |
| `cicada/mcp/fallbacks.py` | Zero-result recovery strategies |
| `cicada/mcp/filter_utils.py` | Result filtering utilities |
| `cicada/mcp/pattern_utils.py` | Pattern parsing and matching |
