# SRC (Structured Repo Context)

> **Transform your codebase into AI-ready context** — MCP server + CLI for semantic code search that makes your code truly understandable for AI assistants

**SRC is both:**
- 🔌 **An MCP Server** — Integrates with Claude Desktop, Cursor, and any MCP-compatible AI assistant
- 💻 **A Standalone CLI** — Use directly from your terminal for indexing and searching

[![CI](https://github.com/kvnpetit/structured-repo-context-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/kvnpetit/structured-repo-context-mcp/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/kvnpetit/structured-repo-context-mcp/branch/main/graph/badge.svg)](https://codecov.io/gh/kvnpetit/structured-repo-context-mcp)
[![npm version](https://img.shields.io/npm/v/src-mcp.svg)](https://www.npmjs.com/package/src-mcp)
[![npm downloads](https://img.shields.io/npm/dm/src-mcp.svg)](https://www.npmjs.com/package/src-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP](https://img.shields.io/badge/MCP-Compatible-blue.svg)](https://modelcontextprotocol.io)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.9-blue.svg)](https://www.typescriptlang.org/)
[![Ollama](https://img.shields.io/badge/Ollama-Required-orange.svg)](https://ollama.com)

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Installation](#installation)
4. [MCP Tools Reference](#mcp-tools-reference)
5. [CLI Reference](#cli-reference)
6. [Configuration](#configuration)
7. [Supported Languages](#supported-languages)
8. [How It Works](#how-it-works)
9. [Comparison](#comparison)
10. [Troubleshooting](#troubleshooting)
11. [Links](#links)

---

## Overview

### The Problem

AI assistants struggle to understand your entire codebase:

- They only see small snippets of code at a time
- Manual copy-pasting of context is tedious and error-prone
- Keyword search misses semantic relationships between code
- Code changes get lost in conversation history

### The Solution

SRC indexes your codebase into semantic, searchable chunks that LLMs actually understand:

| Feature | Description |
|---------|-------------|
| **Hybrid Search** | Vector + BM25 + RRF fusion for optimal results |
| **Call Graph** | Shows who calls what and what calls who |
| **Cross-file Context** | Resolves imports and path aliases automatically |
| **Incremental Updates** | SHA-256 hash detection for fast updates |
| **50+ Languages** | 18 with full AST support via Tree-sitter |

### Use Cases

| Scenario | Example Query |
|----------|---------------|
| **Code Review** | "Show me all error handling in the payment module" |
| **Debugging** | "Find where user sessions are created" |
| **Documentation** | "Explain the authentication flow" |
| **Refactoring** | "List all deprecated API usages" |
| **Onboarding** | "How does the routing system work?" |
| **Security Audit** | "Find all database query locations" |

---

## Quick Start

### 1. Install Ollama

SRC requires [Ollama](https://ollama.com) for embeddings:

```bash
# Install from https://ollama.com, then:
ollama pull nomic-embed-text
```

### 2. Install SRC

**Global installation:**
```bash
npm install -g src-mcp
```

**Or use npx:**
```bash
npx -y src-mcp serve
```

### 3. Use as MCP Server (with AI Assistants)

Add to your MCP client configuration (e.g., Claude Desktop):

**With global installation:**
```json
{
  "mcpServers": {
    "src-mcp": {
      "command": "src-mcp",
      "args": ["serve"]
    }
  }
}
```

**With npx:**
```json
{
  "mcpServers": {
    "src-mcp": {
      "command": "npx",
      "args": ["-y", "src-mcp", "serve"]
    }
  }
}
```

The server automatically indexes the current directory if no index exists, and watches for file changes.

Then in your AI assistant:
```
"Search for authentication logic"
"Find error handling code with limit 20"
"Search for UserService in fts mode"
```

### 4. Use as CLI (Standalone)

```bash
# Start server (auto-indexes if needed)
src-mcp serve

# Search for code
src-mcp search_code --query "authentication"
src-mcp search_code --query "error handling" --limit 20
src-mcp search_code --query "UserService" --mode fts

# Check index status
src-mcp get_index_status
```

### Key Arguments

| Tool | Argument | Default | Description |
|------|----------|---------|-------------|
| `search_code` | `--limit` | 10 | Max results |
| `search_code` | `--mode` | hybrid | `hybrid` / `vector` / `fts` |
| `index_codebase` | `--concurrency` | 4 | Parallel workers |
| `index_codebase` | `--force` | false | Re-index if exists |

---

## Installation

### Global Installation

```bash
npm install -g src-mcp
```

Then use directly:

```bash
src-mcp serve
src-mcp search_code --query "authentication"
src-mcp help
```

### npx (No Installation)

```bash
npx -y src-mcp serve
npx -y src-mcp search_code --query "authentication"
```

### Local Development

```bash
git clone https://github.com/kvnpetit/structured-repo-context-mcp.git
cd structured-repo-context-mcp
npm install
npm run dev
```

---

## MCP Tools Reference

SRC exposes 5 MCP tools that AI assistants can call:

### index_codebase

Index a directory with semantic chunking, AST enrichment, and embeddings.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `directory` | string | No | `.` | Path to directory to index |
| `force` | boolean | No | `false` | Force re-indexing if index exists |
| `exclude` | string[] | No | `[]` | Additional glob patterns to exclude |
| `concurrency` | number | No | `4` | Parallel file processing workers |

**Example:**
```
"Index the project at /home/user/myapp with concurrency 8"
```

**Returns:**
```json
{
  "filesIndexed": 150,
  "chunksCreated": 892,
  "languages": { "typescript": 500, "javascript": 200, "json": 192 }
}
```

---

### search_code

Hybrid search with vector similarity, BM25 keyword matching, and RRF fusion.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | **Yes** | — | Natural language search query |
| `directory` | string | No | `.` | Path to indexed directory |
| `limit` | number | No | `10` | Maximum results to return |
| `threshold` | number | No | — | Distance threshold (0-2, vector mode only) |
| `mode` | enum | No | `hybrid` | Search mode: `hybrid`, `vector`, or `fts` |
| `includeCallContext` | boolean | No | `true` | Include caller/callee information |

**Search Modes:**

| Mode | Description | Best For |
|------|-------------|----------|
| `hybrid` | Vector + BM25 + RRF fusion | General queries (default) |
| `vector` | Semantic similarity only | Conceptual searches |
| `fts` | Full-text keyword only | Exact identifiers |

**Example:**
```
"Search for 'user authentication' with limit 20"
```

**Returns:**
```json
{
  "results": [
    {
      "content": "export async function authenticateUser(credentials)...",
      "filePath": "src/auth/login.ts",
      "startLine": 45,
      "endLine": 78,
      "symbolName": "authenticateUser",
      "symbolType": "function",
      "score": 0.92,
      "callers": [{ "name": "handleLogin", "filePath": "src/routes/auth.ts", "line": 23 }],
      "callees": [{ "name": "validatePassword", "filePath": "src/auth/crypto.ts", "line": 12 }]
    }
  ]
}
```

---

### update_index

Incrementally update the index by detecting changed files via SHA-256 hash comparison.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `directory` | string | No | `.` | Path to indexed directory |
| `dryRun` | boolean | No | `false` | Preview changes without updating |
| `force` | boolean | No | `false` | Force re-index all files |

**Example:**
```
"Update the index with dry run to see what changed"
```

**Returns:**
```json
{
  "added": ["src/new-file.ts"],
  "modified": ["src/auth/login.ts"],
  "deleted": ["src/old-file.ts"],
  "unchanged": 148
}
```

---

### get_index_status

Get status of the embedding index for a directory.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `directory` | string | No | `.` | Path to directory |

**Example:**
```
"Get the index status for current directory"
```

**Returns:**
```json
{
  "exists": true,
  "indexPath": "/home/user/myapp/.src-index",
  "totalFiles": 150,
  "totalChunks": 892,
  "languages": { "typescript": 500, "javascript": 200 }
}
```

---

### get_server_info

Get server version, capabilities, and configuration.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `format` | enum | No | `text` | Output format: `text` or `json` |

**Returns:**
```json
{
  "name": "src-mcp",
  "version": "1.0.0",
  "capabilities": ["indexing", "search", "incremental-update"]
}
```

---

## CLI Reference

**Every MCP tool is also a CLI command.** You can use SRC from your terminal without any AI assistant.

### General Usage

```bash
src-mcp <command> [options]
src-mcp help                    # Show all commands
src-mcp <command> --help        # Show command options
```

Or with npx:

```bash
npx -y src-mcp <command> [options]
```

### Commands

```bash
# Start MCP server (auto-indexes if needed, watches for changes)
src-mcp serve
src-mcp serve --no-watch        # Disable file watcher

# Index a codebase manually
src-mcp index_codebase
src-mcp index_codebase --concurrency 8
src-mcp index_codebase --force   # Re-index even if index exists

# Search indexed code
src-mcp search_code --query "authentication"
src-mcp search_code --query "error handling" --limit 20 --mode hybrid
src-mcp search_code --query "UserService" --mode fts  # Exact keyword search

# Update index incrementally
src-mcp update_index
src-mcp update_index --dryRun   # Preview changes only

# Check index status
src-mcp get_index_status

# Server information
src-mcp get_server_info --format json
```

---

## Configuration

### Environment Variables

All settings can be configured via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_BASE_URL` | Ollama API endpoint | `http://localhost:11434` |
| `EMBEDDING_MODEL` | Model for embeddings | `nomic-embed-text` |
| `EMBEDDING_DIMENSIONS` | Vector dimensions | `768` |
| `CHUNK_SIZE` | Characters per chunk | `1000` |
| `CHUNK_OVERLAP` | Overlap between chunks | `200` |
| `EMBEDDING_BATCH_SIZE` | Batch size for embedding | `10` |
| `LOG_LEVEL` | Log verbosity | `info` |

**Example:**

```bash
OLLAMA_BASE_URL=http://192.168.1.100:11434 src-mcp serve
```

### MCP Client Configuration

**Claude Desktop** (`claude_desktop_config.json`):

**With global installation:**
```json
{
  "mcpServers": {
    "src-mcp": {
      "command": "src-mcp",
      "args": ["serve"]
    }
  }
}
```

**With npx:**
```json
{
  "mcpServers": {
    "src-mcp": {
      "command": "npx",
      "args": ["-y", "src-mcp", "serve"]
    }
  }
}
```

**With environment variables:**

```json
{
  "mcpServers": {
    "src-mcp": {
      "command": "src-mcp",
      "args": ["serve"],
      "env": {
        "OLLAMA_BASE_URL": "http://192.168.1.100:11434"
      }
    }
  }
}
```

### Index Storage

Indexes are stored in `.src-index/` directory within each indexed project:

```
my-project/
├── src/
├── .src-index/              # Created by SRC
│   ├── lancedb/             # Vector database
│   ├── callgraph.json       # Call graph cache
│   └── .src-index-hashes.json  # File hash cache
└── ...
```

Add `.src-index/` to your `.gitignore`:

```gitignore
.src-index/
```

---

## Supported Languages

### Full AST Support (18 languages)

These languages have complete support: symbol extraction, semantic chunking at function/class boundaries, call graph analysis, and import resolution.

| Category | Language | Extensions |
|----------|----------|------------|
| **Web** | JavaScript | `.js` `.jsx` `.mjs` `.cjs` |
| | TypeScript | `.ts` |
| | TSX | `.tsx` |
| | HTML | `.html` `.htm` |
| | Svelte | `.svelte` |
| **Systems** | C | `.c` `.h` |
| | C++ | `.cpp` `.hpp` `.cc` `.cxx` |
| | Rust | `.rs` |
| | Go | `.go` |
| **Enterprise** | Java | `.java` |
| | C# | `.cs` |
| | Kotlin | `.kt` `.kts` |
| | Scala | `.scala` `.sc` |
| **Scripting** | Python | `.py` `.pyi` `.pyw` |
| | Ruby | `.rb` `.rake` `.gemspec` |
| | PHP | `.php` `.phtml` |
| **Functional** | OCaml | `.ml` `.mli` |
| | Swift | `.swift` |

### LangChain Fallback (16 languages)

These languages use intelligent text splitting with language-aware rules:

| Language | Extensions |
|----------|------------|
| Markdown | `.md` `.mdx` |
| LaTeX | `.tex` `.latex` |
| reStructuredText | `.rst` |
| Solidity | `.sol` |
| Protocol Buffers | `.proto` |
| Lua | `.lua` |
| Haskell | `.hs` `.lhs` |
| Elixir | `.ex` `.exs` |
| PowerShell | `.ps1` `.psm1` |
| Perl | `.pl` `.pm` |
| Cobol | `.cob` `.cbl` |
| Visual Basic | `.vb` `.vbs` |
| FORTRAN | `.f` `.f90` `.f95` |
| Assembly | `.asm` `.s` |

### Generic Support (30+ file types)

All other text files use configurable chunking:

| Category | Extensions |
|----------|------------|
| **Config** | `.json` `.yaml` `.yml` `.toml` `.ini` `.env` `.xml` |
| **Shell** | `.sh` `.bash` `.zsh` `.fish` `.bat` `.cmd` |
| **Styles** | `.css` `.scss` `.sass` `.less` |
| **Data** | `.sql` `.graphql` `.gql` |
| **DevOps** | `Dockerfile` `Makefile` `.tf` `.hcl` |
| **Other** | `.zig` `.nim` `.dart` `.vue` `.elm` `.clj` |

### Auto-excluded Files

Binary files and lock files are automatically excluded:

- **Binaries:** `.exe` `.dll` `.so` `.png` `.jpg` `.mp3` `.zip` `.wasm`
- **Lock files:** `package-lock.json` `yarn.lock` `pnpm-lock.yaml`
- **Build outputs:** `.pyc` `.class` `.o` `dist/` `node_modules/`

---

## How It Works

### Indexing Pipeline

```
Source Files → Semantic Chunking → AST Enrichment → Cross-file Context → Embeddings → LanceDB
                    ↓                    ↓                  ↓                 ↓
              Split at symbol      Extract symbols    Resolve imports    nomic-embed-text
              boundaries           and metadata       and aliases        768 dimensions
```

**Steps:**

1. **Scan** — Find all supported files (respects `.gitignore`)
2. **Chunk** — Split code at function/class boundaries (1000 chars, 200 overlap)
3. **Enrich** — Add AST metadata (symbols, imports, exports)
4. **Resolve** — Resolve cross-file imports and TypeScript path aliases
5. **Embed** — Generate vectors via Ollama (nomic-embed-text)
6. **Store** — Save to LanceDB with vector and full-text indices
7. **Cache** — Store file hashes for incremental updates

### Search Pipeline

```
Query → Embed Query → Vector Search ─┐
                                     ├→ RRF Fusion → Add Call Context → Results
Query → Tokenize ───→ BM25 Search ───┘
```

**Steps:**

1. **Embed** — Convert query to vector using same model
2. **Vector Search** — Find semantically similar chunks (cosine similarity)
3. **BM25 Search** — Find keyword matches (term frequency)
4. **RRF Fusion** — Combine rankings with Reciprocal Rank Fusion (k=60)
5. **Call Context** — Add caller/callee information from call graph
6. **Return** — Ranked results with full context

### Technical Specifications

| Component | Specification |
|-----------|---------------|
| **Embedding Model** | nomic-embed-text (137M params) |
| **Vector Dimensions** | 768 |
| **Chunk Size** | 1000 characters |
| **Chunk Overlap** | 200 characters |
| **Batch Size** | 10 embeddings per request |
| **RRF Constant** | k=60 |
| **Vector Database** | LanceDB (embedded) |

---

## Comparison

### SRC vs Basic Code Search MCPs

| Feature | SRC | Basic MCPs |
|---------|-----|------------|
| **Search Method** | Hybrid (Vector + BM25 + RRF) | Keyword only or basic embedding |
| **Call Graph** | Full caller/callee context | None |
| **Cross-file Context** | Resolves imports & path aliases | None |
| **Incremental Updates** | SHA-256 hash detection | Full re-index required |
| **AST Languages** | 18 with Tree-sitter WASM | Few or none |
| **Total Languages** | 50+ | Limited |

### Key Advantages

1. **Hybrid Search** — Combines semantic understanding with keyword precision
2. **Call Graph** — Understand code relationships, not just content
3. **Cross-file Resolution** — Follows imports to provide complete context
4. **Incremental Updates** — Only re-index what changed
5. **Semantic Chunking** — Splits at symbol boundaries, not arbitrary lines

---

## Troubleshooting

### Ollama Connection Failed

```
Error: Ollama is not available
```

**Solution:**
1. Ensure Ollama is running: `ollama serve`
2. Check the URL: `curl http://localhost:11434/api/tags`
3. If using remote Ollama: set `OLLAMA_BASE_URL`

### Model Not Found

```
Error: model 'nomic-embed-text' not found
```

**Solution:**
```bash
ollama pull nomic-embed-text
```

### Index Already Exists

```
Error: Index already exists. Use force=true to re-index.
```

**Solution:**
- Use `force: true` parameter to re-index
- Or use `update_index` for incremental updates

### No Results Found

**Possible causes:**
1. Query too specific — try broader terms
2. Wrong directory — check `directory` parameter
3. Files excluded — check `.gitignore` patterns

### Slow Indexing

**Solutions:**
1. Increase concurrency: `--concurrency 8`
2. Exclude large directories: `--exclude node_modules --exclude dist`
3. Use faster storage (SSD)

---

## Links

### Project

- [GitHub Repository](https://github.com/kvnpetit/structured-repo-context-mcp)
- [npm Package](https://www.npmjs.com/package/src-mcp)
- [Report Issues](https://github.com/kvnpetit/structured-repo-context-mcp/issues)
- [Changelog](./CHANGELOG.md)
- [Architecture Guide](./ARCHITECTURE.md)

### External

- [MCP Specification](https://modelcontextprotocol.io/specification)
- [Ollama](https://ollama.com)
- [LanceDB](https://lancedb.com)
- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/)

---

## License

[MIT](./LICENSE) © 2026 kvnpetit

---

<div align="center">

**Ready to supercharge your AI coding experience?**

```bash
npm install -g src-mcp && src-mcp serve
# or
npx -y src-mcp serve
```

[Report Bug](https://github.com/kvnpetit/structured-repo-context-mcp/issues) · [Request Feature](https://github.com/kvnpetit/structured-repo-context-mcp/issues)

</div>
