---
reviewed:
- cicada/parsing/base_parser.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/parsing/base_indexer.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/elixir/parser.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/indexer.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/elixir/extractors/__init__.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/elixir/extractors/module.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/elixir/extractors/function.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/elixir/extractors/spec.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/elixir/extractors/doc.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/elixir/extractors/dependency.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/elixir/extractors/call.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/elixir/extractors/string.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/elixir/extractors/comment.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/python/indexer.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/python/symbol_types.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/python/string_extractor.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/python/alias_extractor.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/erlang/parser.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/erlang/indexer.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/erlang/extractors/doc.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/scip/reader.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
- cicada/languages/scip/converter.py:ae433ecbdaaa7b3ffc39d8ce7b5a64f9415da86b
---
This file is a diff of a feature specification. I want you to change the code to match the new spec.

# AST Indexing Review

<diff file="codebook/AST_INDEXING.md">
```diff
diff --git a/codebook/AST_INDEXING.md b/codebook/AST_INDEXING.md
new file mode 100644
index 0000000..4c14806
--- /dev/null
+++ b/codebook/AST_INDEXING.md
@@ -0,0 +1 @@
+# AST-Level Indexing
```
</diff>

---
After completing the task, please update the task file with:
- Description of the feature task that was requested
- Short description of the changes that were made and why
Include implemenentation details how the task was implemented.
Do not include code snippets. Only describe the functional changes that were made.
Do not remove diff lines from the task file.
--- FEATURE TASK ---
Document Cicada's AST-level indexing feature comprehensively. The task was to browse through the codebase and create thorough documentation explaining how AST parsing and indexing works for all supported languages (Elixir, Python, Erlang).

--- NOTES ---
The AST indexing system is the core of Cicada's code intelligence. It uses different parsing strategies per language:
- Elixir: Tree-sitter with specialized extractors for modules, functions, specs, docs, dependencies, calls, strings, and comments
- Python: SCIP protocol (via scip-python/Pyright) for type-aware semantic indexing
- Erlang: Tree-sitter with EDoc comment extraction

All languages share a universal enrichment pipeline (BaseIndexer) that adds keyword extraction, timestamp computation, co-change analysis, and co-occurrence matrices.

--- SOLUTION ---
Created comprehensive documentation in `codebook/AST_INDEXING.md` covering:

1. **Architecture Overview**: Diagram showing the parsing layer, BaseIndexer enrichment pipeline, and index storage flow.

2. **Elixir Implementation**: Documented the ElixirParser entry point and all extractors in `cicada/languages/elixir/extractors/`:
   - module.py: defmodule and moduledoc extraction
   - function.py: def/defp/test extraction with args, guards, @impl
   - spec.py: @spec type annotations
   - doc.py: @doc attributes with examples
   - dependency.py: alias/import/require/use/behaviour
   - call.py: Function call sites and module value mentions
   - string.py: String literal extraction for keyword search
   - comment.py: Inline comment extraction

3. **Python Implementation**: Documented the SCIP-based approach:
   - PythonSCIPIndexer workflow (scip-python -> SCIPReader -> SCIPConverter)
   - Symbol type detection patterns from SCIP descriptors
   - Python-native string and alias extraction using ast module

4. **Erlang Implementation**: Documented tree-sitter parsing with EDoc:
   - ErlangParser for module/export/function extraction
   - EDoc comment extraction and proximity-based doc matching

5. **Universal Enrichment Pipeline**: Four phases shared across all languages:
   - Keyword extraction & expansion (streaming parallel)
   - Timestamp computation (git history)
   - Co-change analysis
   - Co-occurrence matrix

6. **Incremental Indexing**: File hashing, change detection, selective processing, keyword/timestamp reuse.

7. **Index Output Format**: JSON structure with modules, functions, keywords, and metadata.

8. **File Reference Table**: Complete listing of all files in the AST indexing system organized by language.
