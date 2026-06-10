## [1.0.3](https://github.com/kvnpetit/structured-repo-context-mcp/compare/v1.0.2...v1.0.3) (2026-01-20)

### Bug Fixes

* **watcher:** auto-indexing not triggering on first run ([734e2b4](https://github.com/kvnpetit/structured-repo-context-mcp/commit/734e2b46a747efa98472acd4c4ebd0ca3db5b246))
## [1.0.2](https://github.com/kvnpetit/structured-repo-context-mcp/compare/v1.0.1...v1.0.2) (2026-01-20)

### Bug Fixes

* use stderr for all logger output to prevent MCP protocol corruption ([439429d](https://github.com/kvnpetit/structured-repo-context-mcp/commit/439429d47723fea5cb107d0f4b13507d44dcb8b6))
## [1.0.1](https://github.com/kvnpetit/structured-repo-context-mcp/compare/v1.0.0...v1.0.1) (2026-01-20)
## 1.0.0 (2026-01-20)

### Features

* **assets:** add tree-sitter WASM parsers and SCM queries ([6bc7514](https://github.com/kvnpetit/structured-repo-context-mcp/commit/6bc7514e034fbfc54c8c5f8a4c66e58c0e7939f7))
* **callgraph:** add persistent caching with hash-based invalidation ([5a5d5a3](https://github.com/kvnpetit/structured-repo-context-mcp/commit/5a5d5a396f6cde8de6c24ddc9c88e5eca84d38b7))
* **cli:** auto-start watcher on serve command ([6b213f9](https://github.com/kvnpetit/structured-repo-context-mcp/commit/6b213f97f1f21face7506aff4c181ffffb1c3f15))
* **core:** add parsing and symbol extraction modules ([023f1ac](https://github.com/kvnpetit/structured-repo-context-mcp/commit/023f1ace80f265a32c9ef67c017e35f07050f956))
* **embeddings:** add call graph extraction and storage ([bf7ca7b](https://github.com/kvnpetit/structured-repo-context-mcp/commit/bf7ca7bd6c675c446ce14a578b47d1c3698d8824))
* **embeddings:** add core embeddings module with Ollama and LanceDB ([c40d4f7](https://github.com/kvnpetit/structured-repo-context-mcp/commit/c40d4f7efe47741c14e59a09ae7627a1e96681b5))
* **embeddings:** add cross-file context resolution for imports ([c3edf0d](https://github.com/kvnpetit/structured-repo-context-mcp/commit/c3edf0ddbffe232a48ebe879a382772be877837b))
* **embeddings:** add file watcher with hash cache and debounce ([03de1dd](https://github.com/kvnpetit/structured-repo-context-mcp/commit/03de1dd685fc13161334adf5c1c2510ce7be082c))
* **embeddings:** add semantic chunking and LLM-based enrichment ([d7d0277](https://github.com/kvnpetit/structured-repo-context-mcp/commit/d7d0277840bb3e2cbd6f6537343f33871af22a65))
* **embeddings:** implement path aliases resolution from tsconfig.json ([855caec](https://github.com/kvnpetit/structured-repo-context-mcp/commit/855caece66944da884c7777118b2a9fee9031fb2))
* **embeddings:** integrate cross-file context into enrichment pipeline ([a046438](https://github.com/kvnpetit/structured-repo-context-mcp/commit/a046438b08a6cb1658fd4371233551288b203ea7))
* **features:** add code analysis MCP tools ([c027dff](https://github.com/kvnpetit/structured-repo-context-mcp/commit/c027dff5d5d401524a87c48dc586e8a6c749b197))
* **features:** add get-call-graph feature with tests ([efc620b](https://github.com/kvnpetit/structured-repo-context-mcp/commit/efc620b5ad739a30dfc9b4bab434d2eb3d1ac055))
* **features:** add semantic search features ([b51309b](https://github.com/kvnpetit/structured-repo-context-mcp/commit/b51309b480732cea3c715d6a7c1a3eac1b536cf6))
* **features:** add shared utilities for features ([6229b10](https://github.com/kvnpetit/structured-repo-context-mcp/commit/6229b10bd0a94d895daa277eb501afdaf91e2c19))
* **features:** add update-index feature with tests ([537c6c6](https://github.com/kvnpetit/structured-repo-context-mcp/commit/537c6c6ac8eff06c10657eaa16ce9b421dcdfb29))
* improve MCP server implementation ([0954f15](https://github.com/kvnpetit/structured-repo-context-mcp/commit/0954f15a456f53c0985f300ab9b582709eca5a80))
* **indexing:** add parallel file processing with configurable concurrency ([8d2aa9b](https://github.com/kvnpetit/structured-repo-context-mcp/commit/8d2aa9b62aa40ec510384a6f28603c86e1a482b1))
* **search:** add hybrid search with BM25 and RRF fusion ([25e08e5](https://github.com/kvnpetit/structured-repo-context-mcp/commit/25e08e5589fc47224badd7404156685bed7a6e2f))
* **search:** add LLM re-ranking for improved result relevance ([388094b](https://github.com/kvnpetit/structured-repo-context-mcp/commit/388094be2e0234f35304ab94429f0c50d0d27a6f))
* **search:** enable call context by default for richer results ([f7532d8](https://github.com/kvnpetit/structured-repo-context-mcp/commit/f7532d80ef5459f244b2e78e6bead479b1b0c3cd))
* **search:** enable LLM re-ranking by default with lightweight model ([4a51c65](https://github.com/kvnpetit/structured-repo-context-mcp/commit/4a51c65270f652567eecf6e9edb613735e5419fb))

### Bug Fixes

* **callgraph:** handle unwritable cache directory gracefully ([986e9eb](https://github.com/kvnpetit/structured-repo-context-mcp/commit/986e9eb2b4cd3d0f3e2fe79b89e9ac62b73891c5))
* **ci:** add npm update for Trusted Publishing ([f9c4ce9](https://github.com/kvnpetit/structured-repo-context-mcp/commit/f9c4ce92c98693e4d092ec0416608f5cfe2d4a74))
* **cli:** handle async promise rejections properly ([1a978f8](https://github.com/kvnpetit/structured-repo-context-mcp/commit/1a978f83790cb8e4a17b9d8f468738d3b01655d4))
* normalize CRLF line endings for cross-platform compatibility ([4dc9468](https://github.com/kvnpetit/structured-repo-context-mcp/commit/4dc94683ac3309ec572067f93f6afbcf3fa32855))
* **test:** resolve lint errors and type safety issues ([276bc86](https://github.com/kvnpetit/structured-repo-context-mcp/commit/276bc86035ed541823879d21a29902d073ffba98))
* **test:** resolve lint errors in watcher.test.ts ([161c4dd](https://github.com/kvnpetit/structured-repo-context-mcp/commit/161c4ddb25409c2409cc55209c3b444420ad28a6))
