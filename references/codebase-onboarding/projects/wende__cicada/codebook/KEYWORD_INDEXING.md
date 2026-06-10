# Keyword-Based Indexing

Cicada extracts and indexes keywords from multiple code sources during indexing, enabling fast keyword-based search across the codebase. Keywords are extracted from module names, function names, parameter names, docstrings, string literals, and inline comments.

## Overview

Keyword-based indexing is the foundation of Cicada's search capabilities. During indexing, keywords are extracted from various sources and stored with weighted scores that reflect their importance. This enables:

1. **Fast Search**: Pre-computed keywords allow instant search without full-text scanning
2. **Relevance Ranking**: Keywords have weights based on their source (code identifiers > documentation > strings)
3. **Stemming/Inflection**: Keywords are expanded to related forms (e.g., "run" → "runs", "running", "ran")

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Source Code                                 │
│  • Module names (MyApp.Users.Admin)                             │
│  • Function names (create_user, getUserData)                    │
│  • Parameter names (user_id, email)                             │
│  • Docstrings (@doc, @moduledoc, """...""")                    │
│  • String literals ("SELECT * FROM users")                      │
│  • Inline comments (# TODO: fix this)                           │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Identifier Splitting                           │
│  • camelCase → camel, case                                      │
│  • PascalCase → pascal, case                                    │
│  • snake_case → snake, case                                     │
│  • HTTPServer → http, server                                    │
│  • MyApp.Users → my, app, users                                 │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Keyword Extraction                             │
│  • Term frequency calculation                                    │
│  • Stopword filtering                                            │
│  • Weight assignment by source                                   │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Keyword Expansion                              │
│  • lemminflect-based inflection                                 │
│  • run → runs, running, ran                                     │
│  • Penalty multiplier (0.7x) for derived forms                  │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Index Storage                               │
│  • keywords: {keyword: weight, ...}                             │
│  • string_keywords: {keyword: weight, ...}                      │
│  • keyword_sources: {keyword: "docs"|"strings"|"comments"}      │
└─────────────────────────────────────────────────────────────────┘
```

## Keyword Sources and Weights

Keywords are extracted from multiple sources with different weights to reflect their importance:

| Source | Weight | Description |
|--------|--------|-------------|
| Code identifiers | 10x | camelCase, snake_case, PascalCase names directly from code |
| Split identifiers | 3x | Words split from identifiers (getUserData → get, user, data) |
| Name keywords | 1.5x | Module/function names (boosted for discoverability) |
| Documentation | 1x | Words from @doc, @moduledoc, docstrings |
| String literals | 1.3x | Strings in function bodies (SQL queries, error messages) |
| Comments | 1x | Inline comments |

### Inflection Penalty

When keywords are expanded via lemminflect, derived forms receive a penalty:

- **Original keyword**: Full score (1.0x)
- **Inflected forms**: 0.7x penalty (e.g., "run" → "running" gets 70% of original score)

## Identifier Splitting

Cicada intelligently splits compound identifiers into component words:

```python
# camelCase
"getUserData" → ["get", "user", "data"]

# PascalCase  
"UserController" → ["user", "controller"]

# snake_case
"get_user_data" → ["get", "user", "data"]

# Acronyms
"HTTPServer" → ["http", "server"]
"PostgreSQL" → ["postgre", "sql"]

# Mixed patterns
"getHTTPResponseCode" → ["get", "http", "response", "code"]

# Module paths
"MyApp.Users.Admin" → ["my", "app", "users", "admin"]
```

## Keyword Extraction Pipeline

### RegularKeywordExtractor

The default extractor uses term frequency (TF) scoring:

```python
from cicada.extractors.keyword import RegularKeywordExtractor

extractor = RegularKeywordExtractor(verbose=True)
result = extractor.extract_keywords(text, top_n=15)

# Returns:
{
    "top_keywords": [("user", 5), ("create", 3), ...],
    "regular_words": ["user", "create", "admin", ...],
    "code_identifiers": ["getUserData", "createUser"],
    "code_split_words": ["get", "user", "data", "create"],
    "tf_scores": {"user": 0.15, "create": 0.09, ...},
    "stats": {
        "total_tokens": 150,
        "total_words": 120,
        "unique_words": 45
    }
}
```

### Stopword Filtering

Common English words are filtered out to reduce noise:

- Articles: the, a, an
- Prepositions: in, on, at, to, for, of, with, by, from
- Conjunctions: and, or, but
- Pronouns: it, they, them, this, that
- Common verbs: is, are, was, were, be, have, has, do, does

## Keyword Expansion

Keywords are expanded using lemminflect to include inflected forms:

```python
from cicada.keyword_expander import KeywordExpander

expander = KeywordExpander(expansion_type="lemmi", verbose=True)
result = expander.expand_keywords(
    ["run", "database"],
    keyword_scores={"run": 0.95, "database": 0.8}
)

# Returns:
{
    "words": [
        {"word": "run", "score": 0.95, "source": "original"},
        {"word": "running", "score": 0.665, "source": "inflection", "parent": "run"},
        {"word": "runs", "score": 0.665, "source": "inflection", "parent": "run"},
        {"word": "ran", "score": 0.665, "source": "inflection", "parent": "run"},
        {"word": "database", "score": 0.8, "source": "original"},
        {"word": "databases", "score": 0.56, "source": "inflection", "parent": "database"},
    ],
    "simple": ["database", "databases", "ran", "run", "running", "runs"]
}
```

### Code Identifiers Not Inflected

Code identifiers (camelCase, snake_case names) are NOT inflected to preserve exact matches:

```python
# "getUserData" stays as "getUserData", not expanded to "getUsersData"
# "create_user" stays as "create_user", not expanded to "creates_user"
```

## Index Structure

Keywords are stored in the index with their weights:

```json
{
  "modules": {
    "MyApp.Users": {
      "keywords": {
        "user": 15.0,
        "users": 10.5,
        "create": 8.0,
        "admin": 5.0
      },
      "string_keywords": {
        "select": 1.3,
        "from": 1.3,
        "users": 1.3
      },
      "functions": [
        {
          "name": "create_user",
          "keywords": {
            "create": 10.0,
            "user": 10.0,
            "email": 3.0,
            "password": 3.0
          }
        }
      ]
    }
  }
}
```

## Configuration

Keyword-based indexing is always enabled by default. No configuration is required.

The extraction method defaults to:
- **Extraction**: `regular` (term frequency based)
- **Expansion**: `lemmi` (lemminflect-based inflection)

## File Reference

| File | Description |
|------|-------------|
| `cicada/extractors/keyword.py` | RegularKeywordExtractor and BaseKeywordExtractor classes |
| `cicada/keyword_expander.py` | KeywordExpander class for lemminflect-based expansion |
| `cicada/utils/keyword_utils.py` | Factory functions for creating extractors |
| `cicada/utils/text_utils.py` | Identifier splitting utilities (split_identifier, extract_code_identifiers) |
| `cicada/indexer.py` | ElixirIndexer._extract_name_keywords() for name-based keyword extraction |

## Related Documentation

- [Keyword Search](KEYWORD_SEARCH.md) - How to search using extracted keywords
- [String-Based Indexing](STRING_INDEXING.md) - Extracting keywords from string literals
