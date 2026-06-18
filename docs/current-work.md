# Current work

## 2026-06-18 — Integrated repository workspace

- Branch: `feat/integrated-workspace`
- Goal: unify repository analysis, file exploration, and grounded chat.
- Status: implementation and browser verification complete.
- Checkpoint: the prior UI is preserved on `feat/advanced-chat-ui` at `0f4876e`.
- Validation: frontend lint/build, backend compile/unit tests, desktop and mobile browser flows.
- Next: product review of `/analyze?preview=1`, then deployment environment and database migration.

## 2026-06-18 — Landing repository discovery

- Branch: `feat/integrated-workspace`
- Goal: make the landing page useful before analysis starts.
- Status: GitHub repository autocomplete, curated popular-repository cards, and cross-platform local-folder upload and analysis implemented.
- Validation: frontend lint/build, backend compile/unit tests, live GitHub Search route, desktop/mobile browser flows, Korean/English copy.
- Local-folder behavior: browsers send selected files with repository-relative paths. The server rebuilds them in the same isolated workspace used by cloned repositories, then runs the standard analysis pipeline.
- Upload guardrails: 900 files, 5MB per file, 50MB total; dependency folders, build output, Git history, environment files, duplicate paths, and path traversal are rejected or excluded.
- Next: deployment-level request body limits and temporary-workspace retention should be aligned with these application limits.
