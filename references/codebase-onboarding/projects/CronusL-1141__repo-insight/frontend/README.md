# RepoInsight Frontend

Vite + React 18 + TypeScript + TailwindCSS frontend skeleton for RepoInsight.

## Stack

- Vite 5 / React 18 / TypeScript 5 (strict)
- TailwindCSS 3 + shadcn/ui primitives
- zustand state management
- axios REST client + native WebSocket
- ECharts (dynamic import) for line-level risk heatmap
- DOMPurify + html-react-parser for safe HTML report rendering

## Layout

```
src/
  main.tsx           App entry
  App.tsx            Two-column layout (input/progress | report)
  index.css          Tailwind directives + global styles
  types/             TS contracts mirroring backend Pydantic schemas
  lib/               Framework-agnostic helpers (api, sanitize, utils)
  hooks/             useAnalysisJob, useWebSocket
  store/             zustand store
  components/        UI components
    ui/              shadcn primitives (button, input, card)
  test/              Vitest setup
```

## Scripts

```bash
pnpm install   # install deps (run by devops, not part of skeleton)
pnpm dev       # start dev server on http://127.0.0.1:5173
pnpm build     # type-check + production build
pnpm test      # run vitest
pnpm lint      # run eslint
pnpm typecheck # tsc --noEmit
```

The dev server proxies `/api` and `/ws` to `http://127.0.0.1:8000` (FastAPI backend).

## Conventions

- Field names follow backend `snake_case` (no case translation layer).
- No `any`. `@ts-ignore` requires a comment explaining why.
- All HTML report rendering MUST go through `lib/sanitize.ts`.
- `components/` never imports `lib/api.ts` directly; go through hooks/store.
- ECharts is dynamically imported inside the heatmap component to keep first-paint bundle below 250 KB gzip.
