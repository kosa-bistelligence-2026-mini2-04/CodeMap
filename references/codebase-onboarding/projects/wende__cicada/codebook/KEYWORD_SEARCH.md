# Keyword Search

Cicada provides keyword-based code search that finds modules and functions by matching query terms against pre-extracted keywords from documentation, function names, parameter names, and string literals.

## Overview

Keyword search is the primary search mechanism in Cicada. It works by:

1. **Indexing**: Extracting keywords from module names, function names, parameters, docstrings, string literals, and comments during indexing
2. **Scoring**: Matching query terms against pre-weighted keywords and calculating relevance scores
3. **Ranking**: Sorting results by score with support for co-change boosting

Unlike full-text search, keyword search understands code structure and prioritizes code identifiers (10x weight) over regular words.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Query Processing                            │
│  • Lowercase normalization                                       │
│  • Wildcard detection (*) and OR pattern expansion (|)          │
│  • Synonym group processing (nested lists)                       │
│  • Module pattern extraction (e.g., "MyApp.User")               │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Score Calculation                           │
│  • Match query terms against document keywords                   │
│  • Sum pre-weighted keyword scores                               │
│  • Apply module name match boost                                 │
│  • Calculate confidence (% of query terms matched)              │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Result Ranking                              │
│  • Sort by score (descending)                                    │
│  • Apply co-change boosting                                      │
│  • Filter by type (modules/functions)                            │
│  • Return top N results                                          │
└─────────────────────────────────────────────────────────────────┘
```

## How Keywords Are Extracted

During indexing, keywords are extracted from multiple sources:

| Source | Weight | Description |
|--------|--------|-------------|
| Code identifiers | 10x | camelCase, snake_case, PascalCase names |
| Split identifiers | 3x | Words split from identifiers (getUserData → get, user, data) |
| Documentation | 1x | Words from @doc, @moduledoc, docstrings |
| String literals | 1.3x | Strings in function bodies (SQL, error messages) |
| Comments | 1x | Inline comments |

Keywords are expanded using lemminflect for stemming (e.g., "running" → "run").

## Search Features

### Basic Search

Search for modules and functions by keywords:

```python
from cicada.keyword_search import KeywordSearcher

searcher = KeywordSearcher(index)
results = searcher.search(["user", "authentication"], top_n=10)
```

### Wildcard Patterns

Use `*` for wildcard matching:

```python
# Find all functions starting with "create"
results = searcher.search(["create*"], top_n=10)

# Find all "handle_" functions
results = searcher.search(["handle_*"], top_n=10)
```

### OR Patterns

Use `|` to match any of multiple terms:

```python
# Find code related to authentication or login
results = searcher.search(["auth|login|signin"], top_n=10)
```

### Synonym Groups

Use nested lists for synonym groups (all terms in a group are treated as alternatives):

```python
# ["user", ["auth", "login"]] means: "user" AND ("auth" OR "login")
results = searcher.search(["user", ["auth", "login"]], top_n=10)
```

### Module-Qualified Search

Include module names for more precise results:

```python
# Find create functions in the Users module
results = searcher.search(["MyApp.Users.create"], top_n=10)
```

### Match Source Filtering

Filter by keyword source:

```python
# Search only in documentation
searcher = KeywordSearcher(index, match_source="docs")

# Search only in string literals  
searcher = KeywordSearcher(index, match_source="strings")

# Search only in comments
searcher = KeywordSearcher(index, match_source="comments")

# Search everywhere (default)
searcher = KeywordSearcher(index, match_source="all")
```

### Type Filtering

Filter results by type:

```python
# Only modules
results = searcher.search(["user"], filter_type="modules")

# Only functions
results = searcher.search(["create"], filter_type="functions")
```

### Co-Change Boosting

Results are boosted based on co-change relationships (files/functions that frequently change together):

```python
# Enable co-change boosting (default: 0.5)
searcher = KeywordSearcher(index, cochange_boost=0.5)

# Disable co-change boosting
searcher = KeywordSearcher(index, cochange_boost=0.0)
```

## Result Structure

Each search result contains:

```python
{
    # Always present
    "type": "function",           # "module" or "function"
    "name": "MyApp.Users.create/2",  # Full name with arity
    "module": "MyApp.Users",      # Module name
    "file": "lib/myapp/users.ex", # File path
    "line": 42,                   # Line number
    "score": 15.5432,             # Relevance score (rounded to 4 decimals)
    "confidence": 75.0,           # % of query terms matched
    "matched_keywords": ["user", "create"],  # Which query terms matched

    # Function-specific (only for type="function")
    "function": "create",         # Function name
    "arity": 2,                   # Function arity
    "visibility": "public",       # "public" or "private" (if available)
    "signature": "def create(name, email)",  # Function signature (if available)

    # Optional fields (included when available)
    "module_matched": True,       # True if module name matched query pattern
    "doc": "Creates a new user",  # Documentation string
    "keyword_sources": {          # Where each matched keyword was found
        "user": "docs",
        "create": "docs+strings"
    },
    "string_sources": [...],      # String literals containing matched keywords
    "last_modified_at": "2025-01-15T10:30:00",  # ISO timestamp
    "last_modified_sha": "abc123",  # Git commit SHA
    "last_modified_pr": 42,       # PR number (if PR index available)
}
```

## Keyword Suggestions

### Related Keywords (Expand)

When search returns too few results, suggest related keywords:

```python
suggestions = searcher.suggest_related_keywords(
    ["provider"],
    top_n=5,
    min_cooccurrence=1
)
# Returns: [{"keyword": "api", "cooccurrence": 5}, ...]
```

### Narrowing Keywords (Refine)

When search returns too many results, suggest keywords to narrow:

```python
suggestions = searcher.suggest_narrowing_keywords(
    ["user"],
    search_results=results,
    top_n=5,
    min_result_count=2
)
# Returns: [{"keyword": "admin", "result_count": 3}, ...]
```

## MCP Tool Integration

The `query` tool uses KeywordSearcher internally:

```
query: ["user", "authentication"]
match_source: "all"
result_type: "functions"
```

## Scoring Algorithm

The score for each result is calculated as:

1. **Base score**: Sum of matched keyword weights
2. **Module boost**: 2x multiplier if module name matches query pattern
3. **Co-change boost**: Additional score based on co-change relationships

```
final_score = base_score × module_boost + cochange_boost × cochange_count
```

## File Reference

| File | Description |
|------|-------------|
| `cicada/keyword_search.py` | KeywordSearcher class implementation |
| `cicada/scoring.py` | Score calculation utilities |
| `cicada/cooccurrence.py` | Co-occurrence analysis for suggestions |
| `cicada/extractors/keyword.py` | RegularKeywordExtractor for keyword extraction |
| `cicada/keyword_expander.py` | Keyword expansion with lemminflect |
