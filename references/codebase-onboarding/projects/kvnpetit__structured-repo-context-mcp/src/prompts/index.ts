import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

/**
 * Register MCP prompts
 *
 * Prompts are reusable templates that help AI assistants understand
 * how to use SRC effectively for code search and analysis.
 */
export function registerPrompts(server: McpServer): void {
  // Main overview prompt - helps AI understand when to use SRC
  server.registerPrompt(
    "src-overview",
    {
      title: "SRC Overview",
      description:
        "Learn about SRC capabilities and when to use it for code search and analysis",
    },
    () => ({
      messages: [
        {
          role: "user",
          content: {
            type: "text",
            text: `# SRC (Structured Repo Context) - Overview

## What is SRC?
SRC is a semantic code search MCP server. It indexes codebases and provides intelligent search using:
- **Vector embeddings** for semantic similarity (understands meaning, not just keywords)
- **BM25 keyword search** for exact matches
- **Hybrid search** combining both with RRF fusion
- **Call graph analysis** showing function relationships

## When to use SRC?

**USE SRC when the user wants to:**
- Find code by meaning/concept ("find authentication logic", "where is error handling")
- Understand code relationships ("what calls this function", "what does this function call")
- Search across a large codebase
- Find similar code patterns
- Explore unfamiliar code

**DON'T USE SRC for:**
- Reading a specific file (use file read tools instead)
- Simple text search in a single file (use grep/search)
- Non-code queries

## Typical Workflow

1. **Check status**: Use \`get_index_status\` to see if index exists
2. **Index if needed**: Use \`index_codebase\` (only once per project)
3. **Search**: Use \`search_code\` with natural language queries

Note: When using \`serve\` mode, the server auto-indexes on startup and watches for file changes.

## Supported Languages
- **Full AST support (18)**: JavaScript, TypeScript, Python, Rust, Go, Java, C, C++, C#, Ruby, PHP, Kotlin, Scala, Swift, HTML, Svelte, OCaml
- **Text splitting (16+)**: Markdown, LaTeX, Solidity, Haskell, Elixir, and more
- **Generic (30+)**: Config files, shell scripts, SQL, and more

## Tips
- Use natural language queries: "authentication middleware" not "auth*"
- The hybrid search mode (default) works best for most queries
- Call context is included by default - shows who calls what`,
          },
        },
      ],
    }),
  );

  // Workflow prompt - step by step guide
  server.registerPrompt(
    "code-search-workflow",
    {
      title: "Code Search Workflow",
      description: "Step-by-step guide for searching code with SRC",
    },
    () => ({
      messages: [
        {
          role: "user",
          content: {
            type: "text",
            text: `# Code Search Workflow with SRC

## Step 1: Check Index
\`\`\`
get_index_status()
\`\`\`

## Step 2: Index if Needed
If no index exists:
\`\`\`
index_codebase()
\`\`\`

## Step 3: Search
\`\`\`
search_code(query: "your search query here")
\`\`\`

## search_code Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| query | string | required | Natural language search query |
| limit | number | 10 | Max results to return |
| mode | "hybrid" / "vector" / "fts" | "hybrid" | Search mode |
| includeCallContext | boolean | true | Include caller/callee info |
| threshold | number | - | Distance threshold (vector mode only) |

## Search Modes
- **hybrid** (default): Vector + BM25 + RRF fusion - best overall
- **vector**: Semantic similarity only - good for conceptual queries
- **fts**: Keyword search only - good for exact identifiers

## Examples
\`\`\`
// Find authentication code
search_code(query: "user authentication and login")

// More results
search_code(query: "error handling", limit: 20)

// Exact identifier search
search_code(query: "UserAuthService", mode: "fts")

// Without call context (faster)
search_code(query: "database queries", includeCallContext: false)
\`\`\``,
          },
        },
      ],
    }),
  );

  // Search tips prompt
  server.registerPrompt(
    "search-tips",
    {
      title: "Search Tips",
      description: "Tips for writing effective code search queries",
    },
    () => ({
      messages: [
        {
          role: "user",
          content: {
            type: "text",
            text: `# Effective Code Search Tips

## Good Query Examples

| Goal | Good Query | Why |
|------|------------|-----|
| Find auth code | "user authentication and login validation" | Describes the concept |
| Find error handling | "error handling and exception catching" | Uses related terms |
| Find API endpoints | "REST API route handlers" | Specifies the pattern |
| Find database code | "database query and data persistence" | Covers the domain |
| Find a function | "calculateTotalPrice function" | Includes the name |

## Query Writing Tips

1. **Be descriptive, not literal**
   - Good: "user password validation and hashing"
   - Bad: "validatePassword"

2. **Include context**
   - Good: "authentication middleware for Express routes"
   - Bad: "auth middleware"

3. **Use domain language**
   - Good: "shopping cart checkout process"
   - Bad: "cart function"

4. **Combine concepts**
   - Good: "file upload with size validation and error handling"
   - Bad: "upload"

## Search Mode Selection

| Mode | Use When |
|------|----------|
| **hybrid** | Default choice, works for most queries |
| **vector** | Conceptual searches like "code that handles retries" |
| **fts** | Exact identifiers like "UserAuthService" |

## Understanding Results

Each result includes:
- **content**: The matching code chunk
- **filePath**: Source file location
- **startLine/endLine**: Line numbers
- **symbolName/Type**: Function or class name if detected
- **score**: Relevance score (higher = better match)
- **callers**: Functions that call this code
- **callees**: Functions this code calls`,
          },
        },
      ],
    }),
  );
}
