# Architecture Guide

> Technical reference for SRC (Structured Repo Context) internals.

This document covers the internal architecture, project structure, and development patterns. For user documentation, see [README.md](./README.md).

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Architecture Overview](#architecture-overview)
3. [Core Components](#core-components)
4. [Feature System](#feature-system)
5. [Data Flow](#data-flow)
6. [Supported Languages](#supported-languages)
7. [Testing](#testing)
8. [Development Workflow](#development-workflow)
9. [Release Process](#release-process)
10. [Naming Conventions](#naming-conventions)

---

## Project Structure

```
src/
├── index.ts              # MCP server entry point (stdio transport)
├── bin.ts                # CLI entry point
├── server.ts             # Server configuration
│
├── features/             # Business logic (exposed as MCP tools + CLI)
│   ├── index.ts          # Feature registry
│   ├── types.ts          # Feature and FeatureResult interfaces
│   ├── utils/            # Shared feature utilities
│   │
│   ├── info/             # get_server_info
│   ├── index-codebase/   # index_codebase
│   ├── search-code/      # search_code
│   ├── update-index/     # update_index
│   ├── get-index-status/ # get_index_status
│   ├── get-call-graph/   # Call graph extraction (internal)
│   │
│   ├── analyze-file/     # File analysis (internal)
│   ├── parse-ast/        # AST parsing (internal)
│   ├── query-code/       # SCM queries (internal)
│   └── list-symbols/     # Symbol extraction (internal)
│
├── core/                 # Parsing and embedding engines
│   ├── embeddings/       # Embedding pipeline
│   │   ├── index.ts      # Public API exports
│   │   ├── ollama.ts     # Ollama client
│   │   ├── vectorstore.ts # LanceDB store
│   │   ├── chunker.ts    # Semantic chunking
│   │   ├── enricher.ts   # AST enrichment
│   │   ├── callgraph.ts  # Call graph analysis
│   │   ├── bm25.ts       # BM25 scoring
│   │   └── types.ts      # Type definitions
│   │
│   ├── parser/           # Tree-sitter WASM parser
│   ├── symbols/          # Symbol extraction
│   ├── queries/          # SCM query execution
│   ├── unified/          # Unified parser with fallback
│   ├── fallback/         # LangChain text splitter
│   ├── ast/              # AST type definitions
│   ├── utils/            # Asset loading, caching
│   └── constants.ts      # Configuration constants
│
├── tools/                # MCP tools adapter
│   ├── adapter.ts        # Feature → MCP Tool conversion
│   └── index.ts          # Tool registration
│
├── resources/            # MCP resources
├── prompts/              # MCP prompts
│
├── cli/                  # CLI adapter
│   ├── adapter.ts        # Feature → CLI command conversion
│   ├── parser.ts         # Zod → citty args conversion
│   └── index.ts          # CLI setup
│
├── config/               # Configuration
│   └── index.ts          # EMBEDDING_CONFIG, ENRICHMENT_CONFIG
│
├── types/                # Shared TypeScript types
└── utils/                # Utilities (logger, colors, spinner)

assets/                   # Runtime assets
├── wasm/                 # Tree-sitter WASM parsers (18 files)
├── queries/              # SCM query files per language
└── languages.json        # Language configuration

.src-index/               # Generated per project (gitignored)
├── lancedb/              # Vector database
├── callgraph.json        # Call graph cache
└── .src-index-hashes.json # File hash cache
```

---

## Architecture Overview

### Design Principles

1. **Feature-first** — Business logic lives in `features/`, adapters expose it
2. **Single source of truth** — Define once, use everywhere (MCP + CLI)
3. **Colocated tests** — `index.test.ts` next to `index.ts`
4. **Flat structure** — Maximum 3 levels of nesting

### High-Level Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Entry Points                              │
├─────────────────────────────────────────────────────────────────┤
│  index.ts (MCP Server)              bin.ts (CLI)                │
│       │                                  │                       │
│       ▼                                  ▼                       │
│  tools/adapter.ts                   cli/adapter.ts              │
│  (Zod → MCP Schema)                 (Zod → citty args)          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    features/index.ts                             │
│                    (Feature Registry)                            │
├─────────────────────────────────────────────────────────────────┤
│  index_codebase  │  search_code  │  update_index  │  ...        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      core/embeddings/                            │
├─────────────────────────────────────────────────────────────────┤
│  ollama.ts     │ vectorstore.ts │ chunker.ts   │ enricher.ts   │
│  (Embeddings)  │ (LanceDB)      │ (Splitting)  │ (AST metadata)│
├─────────────────────────────────────────────────────────────────┤
│  callgraph.ts  │ bm25.ts        │ crossfile.ts │               │
│  (Call graph)  │ (Keywords)     │ (Imports)    │               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                       core/parser/                               │
├─────────────────────────────────────────────────────────────────┤
│  parser/       │ symbols/       │ queries/     │ unified/      │
│  (Tree-sitter) │ (Extraction)   │ (SCM)        │ (Fallback)    │
└─────────────────────────────────────────────────────────────────┘
```

### Request Flow

```
MCP Client (Claude)          CLI (Terminal)
       │                           │
       │ stdio JSON-RPC            │ citty command
       ▼                           ▼
   server.ts                    bin.ts
       │                           │
       │ server.tool()             │ defineCommand()
       ▼                           ▼
   tools/adapter.ts            cli/adapter.ts
       │                           │
       │ registerFeatureAsTool()   │ featureToCittyCommand()
       ▼                           ▼
       └───────────┬───────────────┘
                   │
                   ▼
            feature.execute(input)
                   │
                   ▼
            FeatureResult { success, data, message, error }
                   │
       ┌───────────┴───────────┐
       ▼                       ▼
   MCP Response            CLI Output
   (JSON via stdio)        (Formatted text)
```

---

## Core Components

### Ollama Client (`core/embeddings/ollama.ts`)

Handles communication with Ollama API for embeddings.

```typescript
interface OllamaClient {
  healthCheck(): Promise<{ ok: boolean; error?: string }>;
  embedBatch(texts: string[]): Promise<number[][]>;
}
```

**Configuration:**
- `OLLAMA_BASE_URL`: API endpoint (default: `http://localhost:11434`)
- `EMBEDDING_MODEL`: Model name (default: `nomic-embed-text`)

### Vector Store (`core/embeddings/vectorstore.ts`)

LanceDB wrapper for vector and full-text search.

```typescript
interface VectorStore {
  connect(): Promise<void>;
  close(): void;
  exists(): boolean;
  clear(): Promise<void>;
  addChunks(chunks: EmbeddedChunk[]): Promise<void>;
  searchVector(vector: number[], limit: number): Promise<SearchResult[]>;
  searchFTS(query: string, limit: number): Promise<SearchResult[]>;
  searchHybrid(vector: number[], query: string, limit: number): Promise<SearchResult[]>;
}
```

**Storage:**
- Location: `.src-index/lancedb/` within each project
- Schema: `id`, `content`, `filePath`, `language`, `startLine`, `endLine`, `symbolName`, `symbolType`, `vector`

### Semantic Chunker (`core/embeddings/chunker.ts`)

Splits code into meaningful chunks preserving context.

```typescript
interface Chunk {
  id: string;           // Unique identifier
  content: string;      // Code content
  filePath: string;     // Source file path
  language: string;     // Detected language
  startLine: number;    // Start line number
  endLine: number;      // End line number
  symbolName?: string;  // Function/class name
  symbolType?: string;  // "function" | "class" | "method" | etc.
}
```

**Strategy:**
1. Parse AST to find symbol boundaries (functions, classes)
2. Split at boundaries with configurable size (default: 1000 chars)
3. Add overlap for context (default: 200 chars)
4. Fall back to LangChain splitter for unsupported languages

### AST Enricher (`core/embeddings/enricher.ts`)

Adds semantic metadata from AST analysis.

```typescript
interface EnrichedChunk extends Chunk {
  enrichedContent: string;    // Content with metadata header
  containedSymbols: string[]; // Symbols defined in chunk
  imports: ImportInfo[];      // Resolved imports
  exports: ExportInfo[];      // Exported symbols
  wasEnriched: boolean;       // Enrichment success flag
}
```

**Features:**
- Symbol extraction (functions, classes, variables, interfaces, types)
- Import resolution (relative, absolute, path aliases)
- Export detection
- Cross-file context inclusion

### Hybrid Search

Combines multiple search strategies:

```
                    ┌─────────────────┐
                    │      Query      │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              │              ▼
    ┌─────────────────┐      │    ┌─────────────────┐
    │  Embed Query    │      │    │ Tokenize Query  │
    │ (nomic-embed)   │      │    │    (BM25)       │
    └────────┬────────┘      │    └────────┬────────┘
             │               │             │
             ▼               │             ▼
    ┌─────────────────┐      │    ┌─────────────────┐
    │  Vector Search  │      │    │   BM25 Search   │
    │ (cosine sim)    │      │    │ (term freq)     │
    └────────┬────────┘      │    └────────┬────────┘
             │               │             │
             └───────────────┼─────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   RRF Fusion    │
                    │ score = Σ 1/(k+r) │
                    │    k = 60       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Add Call Graph │
                    │ (callers/callees)│
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Results      │
                    └─────────────────┘
```

### Call Graph (`core/embeddings/callgraph.ts`)

Extracts function call relationships.

```typescript
interface CallContext {
  callers: CallerInfo[];  // Who calls this function
  callees: CalleeInfo[];  // What this function calls
}

interface CallerInfo {
  name: string;
  filePath: string;
  line: number;
}
```

**Process:**
1. Parse AST for all files
2. Extract function definitions and call sites
3. Resolve cross-file references
4. Cache to `.src-index/callgraph.json`

---

## Feature System

### Feature Interface

```typescript
// src/features/types.ts

interface Feature<TInput extends z.ZodType = z.ZodType> {
  name: string;           // Tool name (snake_case)
  description: string;    // LLM-friendly description
  schema: TInput;         // Zod validation schema
  execute: (input: z.infer<TInput>) => FeatureResult | Promise<FeatureResult>;
}

interface FeatureResult {
  success: boolean;
  data?: unknown;
  message?: string;
  error?: string;
}
```

### Creating a New Feature

1. **Create folder:** `src/features/my_feature/`

2. **Create `index.ts`:**

```typescript
import { z } from "zod";
import type { Feature, FeatureResult } from "@features/types";

// 1. Define schema with descriptions for LLMs
export const myFeatureSchema = z.object({
  param: z.string().describe("Description for LLM understanding"),
  optional: z.boolean().optional().default(false).describe("Optional flag"),
});

export type MyFeatureInput = z.infer<typeof myFeatureSchema>;

// 2. Implement execute function
export async function execute(input: MyFeatureInput): Promise<FeatureResult> {
  try {
    // Business logic here
    return {
      success: true,
      message: "Operation completed",
      data: { result: "..." },
    };
  } catch (err) {
    return {
      success: false,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

// 3. Export feature definition
export const myFeature: Feature<typeof myFeatureSchema> = {
  name: "my_feature",  // snake_case
  description: "Clear description for LLMs",
  schema: myFeatureSchema,
  execute,
};
```

3. **Create `index.test.ts`:**

```typescript
import { describe, expect, test, vi } from "vitest";
import { execute, myFeatureSchema } from "@features/my_feature";

describe("myFeatureSchema", () => {
  test("validates valid input", () => {
    const result = myFeatureSchema.safeParse({ param: "test" });
    expect(result.success).toBe(true);
  });

  test("applies defaults", () => {
    const result = myFeatureSchema.safeParse({ param: "test" });
    if (result.success) {
      expect(result.data.optional).toBe(false);
    }
  });
});

describe("execute", () => {
  test("returns success for valid input", async () => {
    const result = await execute({ param: "test", optional: false });
    expect(result.success).toBe(true);
  });
});
```

4. **Register in `src/features/index.ts`:**

```typescript
export { myFeature } from "./my_feature";

export const features: Feature[] = [
  // ... existing features
  myFeature,
];
```

### Adapter System

**MCP Tools Adapter** (`src/tools/adapter.ts`):
- Converts `Feature.schema` (Zod) → MCP input schema
- Registers with `server.tool(name, schema, handler)`
- Wraps `execute()` result in MCP response format

**CLI Adapter** (`src/cli/adapter.ts`):
- Converts `Feature.schema` (Zod) → citty args via `zodToCittyArgs()`
- Creates `defineCommand()` with generated options
- Handles output formatting with colors

---

## Data Flow

### Indexing Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    index_codebase                                │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. Collect Files                                                 │
│    - Read .gitignore                                            │
│    - Apply exclusions                                           │
│    - Filter by supported extensions                             │
│    - Skip hidden files/folders                                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Parallel Processing (configurable concurrency)               │
│    For each file:                                               │
│    ├─ chunkFile() → Chunk[]                                     │
│    └─ enrichChunksFromFile() → EnrichedChunk[]                  │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Generate Embeddings                                          │
│    - Batch chunks (10 per request)                              │
│    - Call Ollama embedBatch()                                   │
│    - Create EmbeddedChunk[]                                     │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Store in LanceDB                                             │
│    - vectorStore.addChunks()                                    │
│    - Create vector index                                        │
│    - Create FTS index                                           │
└─────────────────────────────────────────────────────────────────┘
```

### Search Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                      search_code                                 │
│                   query: "authentication"                        │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. Embed Query                                                   │
│    ollamaClient.embedBatch([query]) → vector[768]               │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Parallel Search (hybrid mode)                                │
│    ├─ vectorStore.searchVector(vector, limit * 2)               │
│    └─ vectorStore.searchFTS(query, limit * 2)                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. RRF Fusion                                                    │
│    score = Σ 1/(k + rank), k = 60                               │
│    Merge and sort by combined score                             │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Add Call Context (if enabled)                                │
│    For each result:                                             │
│    ├─ Find callers (who calls this function)                    │
│    └─ Find callees (what this function calls)                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Return Results                                                │
│    SearchResult[] with content, metadata, score, callContext    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Supported Languages

### Tree-sitter WASM (18 languages)

Full AST support with symbol extraction and call graph analysis.

| Language | WASM File | Query Folder |
|----------|-----------|--------------|
| JavaScript | `tree-sitter-javascript.wasm` | `queries/javascript/` |
| TypeScript | `tree-sitter-typescript.wasm` | `queries/typescript/` |
| TSX | `tree-sitter-tsx.wasm` | `queries/tsx/` |
| Python | `tree-sitter-python.wasm` | `queries/python/` |
| Rust | `tree-sitter-rust.wasm` | `queries/rust/` |
| Go | `tree-sitter-go.wasm` | `queries/go/` |
| Java | `tree-sitter-java.wasm` | `queries/java/` |
| C | `tree-sitter-c.wasm` | `queries/c/` |
| C++ | `tree-sitter-cpp.wasm` | `queries/cpp/` |
| C# | `tree-sitter-c_sharp.wasm` | `queries/c_sharp/` |
| Ruby | `tree-sitter-ruby.wasm` | `queries/ruby/` |
| PHP | `tree-sitter-php.wasm` | `queries/php/` |
| Kotlin | `tree-sitter-kotlin.wasm` | `queries/kotlin/` |
| Scala | `tree-sitter-scala.wasm` | `queries/scala/` |
| Swift | `tree-sitter-swift.wasm` | `queries/swift/` |
| HTML | `tree-sitter-html.wasm` | `queries/html/` |
| Svelte | `tree-sitter-svelte.wasm` | `queries/svelte/` |
| OCaml | `tree-sitter-ocaml.wasm` | `queries/ocaml/` |

### LangChain Fallback (16 languages)

Intelligent text splitting without full AST:

`markdown`, `latex`, `rst`, `sol`, `proto`, `cob`, `lua`, `hs`, `ex`, `ps1`, `pl`, `vb`, `xslt`, `as`, `asm`, `f90`

### Language Configuration

Located in `assets/languages.json`:

```json
{
  "treesitter": {
    "javascript": {
      "wasm": "tree-sitter-javascript.wasm",
      "queries": "javascript",
      "extensions": [".js", ".mjs", ".cjs", ".jsx"]
    }
  },
  "langchain": {
    "supported": ["markdown", "latex", ...]
  },
  "fallbackExtensions": {
    ".dockerfile": "dockerfile"
  },
  "specialFilenames": {
    "Dockerfile": "dockerfile",
    "Makefile": "makefile"
  },
  "binaryExtensions": [".exe", ".dll", ".png", ...]
}
```

---

## Testing

### Framework

- **Runner:** Vitest
- **Command:** `npm test` (uses Vitest)
- **Location:** Colocated with source (`index.test.ts`)

### Running Tests

```bash
npm test              # Run all tests
npm test:watch        # Watch mode
npm test:coverage     # With coverage
npm test:ui           # Vitest UI
```

### Test Structure

```typescript
import { describe, expect, test, vi, beforeEach, afterEach } from "vitest";

describe("FeatureName", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("schema", () => {
    test("validates valid input", () => { ... });
    test("applies defaults", () => { ... });
    test("rejects invalid input", () => { ... });
  });

  describe("execute", () => {
    test("success case", async () => { ... });
    test("error case", async () => { ... });
  });
});
```

### Mocking

```typescript
// Mock modules
vi.mock("@core/embeddings");

// Mock implementations
vi.mocked(embeddings.createOllamaClient).mockReturnValue({
  healthCheck: vi.fn().mockResolvedValue({ ok: true }),
  embedBatch: vi.fn().mockResolvedValue([[0.1, 0.2, ...]]),
});
```

---

## Development Workflow

### Commands

```bash
# Development
npm run dev              # Watch mode with auto-reload
npm run cli help         # Test CLI

# Quality checks
npm run check            # All: typecheck + lint + format
npm run typecheck        # TypeScript only
npm run lint             # ESLint only
npm run lint:fix         # Auto-fix lint issues
npm run format           # Prettier format
npm run format:check     # Check formatting

# Build
npm run build            # Compile TypeScript
```

### Import Aliases

Always use path aliases (never relative imports):

| Alias | Path |
|-------|------|
| `@features/*` | `src/features/*` |
| `@tools/*` | `src/tools/*` |
| `@cli/*` | `src/cli/*` |
| `@config` | `src/config` |
| `@utils/*` | `src/utils/*` |
| `@core/*` | `src/core/*` |
| `@/*` | `src/*` |

```typescript
// Correct
import { logger } from "@utils";
import type { Feature } from "@features/types";

// Incorrect
import { logger } from "../utils";
```

---

## Release Process

### Automatic Release

Releases are triggered by merging to `main` with `[release]` in commit message.

```bash
# 1. Update version
npm version minor  # or patch, major

# 2. Push to dev
git push origin dev

# 3. Merge to main with [release]
git checkout main
git merge dev -m "chore(release): v1.2.0 [release]"
git push origin main
```

### What Happens

1. GitHub Actions detects `[release]` in commit
2. Generates CHANGELOG.md from conventional commits
3. Commits changelog to main
4. Creates GitHub Release with notes
5. Publishes to npm with provenance

### Conventional Commits

| Prefix | Changelog Section |
|--------|-------------------|
| `feat:` | Features |
| `fix:` | Bug Fixes |
| `perf:` | Performance |
| `revert:` | Reverts |

Other prefixes (`docs:`, `chore:`, `test:`, etc.) are not included in changelog.

---

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| **Feature names** | snake_case + verb | `get_server_info`, `search_code` |
| **File names** | kebab-case | `adapter.ts`, `vector-store.ts` |
| **Test files** | `*.test.ts` | `index.test.ts` |
| **Functions** | camelCase | `createVectorStore()` |
| **Types/Interfaces** | PascalCase | `Feature`, `SearchResult` |
| **Constants** | SCREAMING_SNAKE | `EMBEDDING_CONFIG` |

### Verb Prefixes for Features

| Prefix | Usage |
|--------|-------|
| `get_` | Retrieve single item |
| `list_` | Retrieve multiple items |
| `search_` | Query with results |
| `index_` | Create/build index |
| `update_` | Modify existing |
| `delete_` | Remove item |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Embedding model |
| `EMBEDDING_DIMENSIONS` | `768` | Vector size |
| `CHUNK_SIZE` | `1000` | Chars per chunk |
| `CHUNK_OVERLAP` | `200` | Overlap size |
| `EMBEDDING_BATCH_SIZE` | `10` | Batch size |
| `LOG_LEVEL` | `info` | Log verbosity |

### Internal Configuration

Located in `src/config/index.ts`:

```typescript
export const EMBEDDING_CONFIG: EmbeddingConfig = {
  ollamaBaseUrl: process.env.OLLAMA_BASE_URL ?? "http://localhost:11434",
  embeddingModel: process.env.EMBEDDING_MODEL ?? "nomic-embed-text",
  embeddingDimensions: Number(process.env.EMBEDDING_DIMENSIONS) || 768,
  defaultChunkSize: Number(process.env.CHUNK_SIZE) || 1000,
  defaultChunkOverlap: Number(process.env.CHUNK_OVERLAP) || 200,
  batchSize: Number(process.env.EMBEDDING_BATCH_SIZE) || 10,
};

export const ENRICHMENT_CONFIG = {
  includeCrossFileContext: true,
  maxImportsToResolve: 10,
  maxSymbolsPerImport: 5,
};
```

---

## Links

- [README](./README.md) — User documentation
- [Changelog](./CHANGELOG.md) — Version history
- [Report Issues](https://github.com/kvnpetit/structured-repo-context-mcp/issues)
- [MCP Specification](https://modelcontextprotocol.io/specification)
- [Ollama](https://ollama.com)
- [LanceDB](https://lancedb.com)
- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/)
