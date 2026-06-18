# Implementation notes

## 2026-06-18 — Analysis and chat integration

- The workspace uses three coordinated regions: file explorer, report, and Copilot.
- The full-screen chat reuses `ChatInterface`; it is not a second conversation implementation.
- Analysis remains useful without an LLM through deterministic scanning. Optional LLM synthesis is grounded in selected source snippets.
- Conversation tables persist thread continuity across the inline and full-screen surfaces.
- Cache bypass was renamed to “new snapshot” and moved under advanced settings because it deletes the prior clone before analysis.

## 2026-06-18 — Landing repository discovery

- GitHub autocomplete uses a Next.js Route Handler so optional `GITHUB_TOKEN` credentials stay server-side. Invalid configured credentials fall back to public search for public repositories.
- Search waits briefly after typing, cancels stale requests, and supports arrow-key navigation, Escape, Enter, mouse selection, and full-URL submission.
- The popular repositories section is a curated static list rather than a claim of real-time GitHub trending rank.
- The local-folder control uses the operating system folder picker through `webkitdirectory`, supported by current Chromium, Edge, and Safari browsers. Browser security hides the absolute path but provides files and repository-relative paths.
- Local files are sent as multipart form data, validated again on the backend, and reconstructed under the job's isolated clone workspace. A marker lets the existing pipeline skip Git clone and continue with structural analysis.
- Client and server both enforce the upload allowlist boundaries: 900 files, 5MB per file, and 50MB total. Dependency/build folders, Git history, environment files, duplicates, and unsafe paths do not enter the workspace.
