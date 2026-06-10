# RepoInsight Deployment Guide

This guide covers two ways to bring up RepoInsight on a single host:

1. **Local dev** — PowerShell 7 scripts (recommended for development, hot reload)
2. **Docker Compose** — production-shaped single-host stack (recommended for demo / staging)

> Target ports: backend `8000`, frontend `5173` (Compose maps nginx :80 → host :5173 to keep parity with dev).

---

## 0. Prerequisites

| Tool       | Min version | Used for                       |
|------------|-------------|--------------------------------|
| PowerShell | 7.0+        | All `scripts/*.ps1`            |
| Python     | 3.12        | Backend runtime                |
| uv         | 0.5+        | Backend package management     |
| Node       | 20 LTS      | Frontend tooling               |
| pnpm       | 9+          | Frontend package management    |
| git        | any         | Required for repo cloning      |
| Docker     | 24+         | Compose path only              |

Install hints (Windows):

```powershell
winget install --id Microsoft.PowerShell
winget install --id astral-sh.uv
winget install --id OpenJS.NodeJS.LTS
winget install --id pnpm.pnpm
winget install --id Docker.DockerDesktop
```

---

## 1. Configure secrets

Copy the template and fill in your `OPENAI_API_KEY`:

```powershell
Copy-Item .env.example .env
notepad .env       # or: code .env
```

`.env` minimum required keys:

```dotenv
OPENAI_API_KEY=sk-...your-key...
LOG_LEVEL=INFO
```

> The bootstrap script refuses to proceed if `OPENAI_API_KEY` is missing or set to a placeholder.
> Never commit `.env` — it is excluded by `.gitignore` and `.dockerignore`.

---

## 2. Path A — Local dev (PowerShell 7)

### 2.1 One-time bootstrap

```powershell
pwsh ./scripts/bootstrap.ps1
```

What it does:

- Verifies `.env` and `OPENAI_API_KEY`
- Verifies `uv` and `pnpm` are on PATH
- Runs `uv sync` in `backend/`
- Runs `pnpm install` in `frontend/`
- Creates `backend/data/` for the SQLite database

Useful flags:

```powershell
pwsh ./scripts/bootstrap.ps1 -SkipFrontend     # backend only
pwsh ./scripts/bootstrap.ps1 -SkipBackend      # frontend only
```

### 2.2 Start dev servers

```powershell
pwsh ./scripts/dev.ps1
```

Two new PowerShell windows open:

- **Backend**  → `http://localhost:8000` (uvicorn `--reload`)
- **API docs** → `http://localhost:8000/docs`
- **Frontend** → `http://localhost:5173` (Vite HMR)

If you prefer single-window background jobs:

```powershell
pwsh ./scripts/dev.ps1 -NoWindow
Get-Job
Receive-Job -Name repo-insight-backend -Keep -Wait
```

### 2.3 Smoke test

```powershell
pwsh ./scripts/smoke.ps1
```

Probes `/api/health` and the frontend root. Bounded to 30s. Exits `0` on PASS, `1` on FAIL.

### 2.4 Stop

```powershell
pwsh ./scripts/stop.ps1
```

Looks up listeners on ports 8000 / 5173 via `Get-NetTCPConnection`, sends a polite stop, then force-kills any survivor after 5 s. Use `-Force` to skip the grace period.

---

## 3. Path B — Docker Compose

### 3.1 Build & start

```powershell
docker compose up -d --build
docker compose ps
docker compose logs -f
```

Endpoints (host-side):

| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:5173        |
| Backend  | http://localhost:8000        |
| API docs | http://localhost:8000/docs   |
| Health   | http://localhost:8000/api/health |

The frontend container fronts the backend with nginx and proxies:

- `/api/*` → `backend:8000`
- `/ws`    → `backend:8000` (with `Upgrade` / `Connection` headers)

### 3.2 Smoke test against the stack

```powershell
pwsh ./scripts/smoke.ps1 `
    -BackendUrl http://localhost:8000 `
    -FrontendUrl http://localhost:5173
```

### 3.3 Stop & clean

```powershell
docker compose down              # stop, keep volumes
docker compose down -v           # also drop SQLite + cache volumes
docker compose build --no-cache  # force rebuild
```

### 3.4 What is in each image

- `backend` — multi-stage: `python:3.12-slim` builder with `uv` → slim runtime
  with the prebuilt venv. Runs as **non-root user `app` (uid 1001)**. `HEALTHCHECK`
  hits `/api/health`. Includes `git` for repo cloning and `libgomp1` for
  `sentence-transformers`.
- `frontend` — multi-stage: `node:20-bookworm-slim` builder running `pnpm build`
  → `nginx:1.27-alpine` runtime serving `/usr/share/nginx/html`. Runs as
  non-root user `app`. `HEALTHCHECK` hits `/`.

Both images pin base versions — **never `latest`** — so builds are reproducible.

---

## 4. Troubleshooting

### `bootstrap.ps1` fails with "OPENAI_API_KEY is missing"

Open `.env` and ensure the line exists, is uncommented, and the value is not
`your-key-here` / `sk-xxx`. Quoting is optional but consistent quoting helps:

```dotenv
OPENAI_API_KEY="sk-proj-..."
```

### `bootstrap.ps1` fails with "Missing required tools: uv"

Install uv and reopen the PowerShell window so `PATH` refreshes:

```powershell
winget install astral-sh.uv
# or
pip install uv
```

### `dev.ps1` says ports are already in use

```powershell
pwsh ./scripts/stop.ps1 -Force
# or, manual:
Get-NetTCPConnection -LocalPort 8000,5173 -State Listen | Select-Object LocalPort,OwningProcess
Stop-Process -Id <PID> -Force
```

### `smoke.ps1` reports backend FAIL but frontend PASS

- Confirm the backend window is still open and uvicorn finished startup.
- `http://localhost:8000/api/health` should return JSON. 404 means the route
  is not yet implemented in `backend/app/api/`.
- Check the backend window for a stack trace; the most common cause is a
  missing env var (e.g. `OPENAI_API_KEY` not loaded into the process).

### Docker: `backend` container is `unhealthy`

```powershell
docker compose logs backend --tail 200
docker compose exec backend curl -v http://127.0.0.1:8000/api/health
```

If the route does not exist yet, the healthcheck is the canary — fix the
route, not the healthcheck.

### Docker: frontend can reach `/` but `/api` returns 502

The nginx upstream `backend:8000` is unreachable. Check that `backend` is
`healthy` (Compose only starts `frontend` after `backend` reports healthy via
`depends_on.condition: service_healthy`). If you bypass that with `--no-deps`
the 502 is expected.

### Windows: PowerShell complains about execution policy

Run scripts via `pwsh -File` or relax the policy for the current user once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

### sentence-transformers first run is slow

The MiniLM model (~22 MB) is downloaded on first use and cached under
`backend/.cache/` (host) or the `backend_cache` named volume (Docker). This is
expected — subsequent starts are instant.

---

## 5. File map

```
repo-insight/
├── docker-compose.yml          # backend + frontend stack
├── .dockerignore               # root build context exclusions
├── backend/
│   ├── Dockerfile              # uv multi-stage, non-root, HEALTHCHECK
│   └── .dockerignore
├── frontend/
│   ├── Dockerfile              # node → nginx multi-stage, non-root
│   ├── nginx.conf              # SPA + /api proxy + /ws upgrade
│   └── .dockerignore
├── scripts/
│   ├── bootstrap.ps1           # one-shot env + deps init
│   ├── dev.ps1                 # concurrent backend+frontend dev start
│   ├── stop.ps1                # graceful stop on ports 8000/5173
│   └── smoke.ps1               # /api/health + frontend / probe
└── docs/
    └── DEPLOYMENT.md           # this file
```
