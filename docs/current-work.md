# Current Work

## 2026-06-18 — Notion HTML to HTTP API specification migration

- Branch: `feat/integrated-workspace`
- Goal: preserve every Notion HTML specification locally and strengthen executable `.http` API contracts.
- Status: conversion and first API-contract reinforcement complete.

### Files and areas

- `docs/http/`: 49 executable API specification files across 12 domains.
- `docs/http/_source-spec/`: comment-only conversions of all 113 source HTML files.
- `docs/http/_source-spec/manifest.json`: source path, SHA-256 and token coverage evidence.
- `scripts/convert_notion_html_to_http.py`: standard-library-only converter.
- `scripts/validate_http_specs.py`: preservation, traceability, request-block and placeholder validator.

### Validation

```bash
python3 scripts/validate_http_specs.py
python3 -m py_compile scripts/convert_notion_html_to_http.py scripts/validate_http_specs.py
git diff --check
```

Latest result: 113/113 source files, 100% source-token coverage, 49 executable specs, 107 request blocks, and zero unmapped source feature/API IDs.

### Contract decisions still required

- `PROJECT-LIST-API-005`: choose one policy for limit overflow (200 warning vs 413/422 rejection).
- `PROJECT-PIPELINE-API-004`: define allowed `target` values before implementation.
- Phase 2 stack scoring, long-term memory, PDF/share and graph contracts are design drafts, not implemented endpoints.
- Reconcile legacy flat error responses with the common nested error envelope before backend implementation.

### Preserved unrelated local work

Existing changes under `docs/03_API/` were not staged or included in this HTTP migration commit.
