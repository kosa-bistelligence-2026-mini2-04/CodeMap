# RepoLens

Conversational AI for any GitHub repository — chat-first analysis grounded in your codebase, powered by the Claude API.

Connect your GitHub account, pick a repository, and start a conversation. RepoLens streams Claude's answers in markdown, citing files from the repo, and offers prompt suggestions built from detected code areas crossed with analytical lenses (security, architecture, dependencies, etc). A structured technical analysis is still available as a secondary view for the moments you want a full report.

## Features

- **Chat with a repository** — multi-turn conversations persisted per repo, with sidebar history, rename and delete, streaming markdown replies, code blocks with copy, and abortable responses
- **Prompt suggestions** — auto-detected code areas (modules) × analytical lenses (executive summary, tech stack, architecture, security, dependencies, update plan, recommendations, code metrics, fun facts) and combined cross-products
- **Technical analysis (secondary)** — the original structured report:
  - Executive Summary, Tech Stack, Architecture
  - Security findings (OWASP Top 10) with grade A–F
  - Dependencies health by ecosystem
  - Update Plan (critical, major, minor)
  - Top recommendations ordered by impact

## Stack

| App / Package | Tech |
|---|---|
| **Portal** (`apps/portal`) | TanStack Start, React 19, TanStack Query |
| **API** (`apps/api`) | NestJS 11, Drizzle ORM, PostgreSQL, Anthropic SDK |
| **UI** (`packages/ui`) | Shadcn/UI + Radix UI, Tailwind CSS v4, react-markdown |
| **Auth** (`packages/auth`) | Better Auth (GitHub OAuth) |
| **Shared** (`packages/shared`) | TypeScript — types & utilities |

**Tooling:** Turborepo · pnpm · Biome · Husky · TypeScript 5

## Getting Started

```bash
# 1. Install dependencies
pnpm install

# 2. Start infrastructure (PostgreSQL)
cd apps/api && docker-compose up -d && cd ../..

# 3. Set up environment variables
cp apps/api/.env.example apps/api/.env
cp apps/portal/.env.example apps/portal/.env
# Fill in: ANTHROPIC_API_KEY, GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET

# 4. Run database migrations
cd apps/api && npx drizzle-kit migrate && cd ../..

# 5. Start all apps in dev mode
pnpm dev
```

| Service | URL |
|---|---|
| Portal | http://localhost:3000 |
| API | http://localhost:4000 |

## Environment Variables

### `apps/api/.env`

```env
PORT=4000
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=repo_lens
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/repo_lens
BETTER_AUTH_SECRET=your-super-secret-key-change-in-production-min-32-chars
BETTER_AUTH_URL=http://localhost:4000
ALLOWED_ORIGINS=http://localhost:3000

# AI Analysis
ANTHROPIC_API_KEY=

# Optional: skip real Anthropic calls in dev
# ANTHROPIC_MOCK=true

# GitHub OAuth (create at github.com/settings/applications/new)
# Callback URL: http://localhost:4000/api/auth/callback/github
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
```

### `apps/portal/.env`

```env
VITE_API_URL=http://localhost:4000
```

## GitHub OAuth Setup

1. Go to [github.com/settings/developers](https://github.com/settings/developers) → New OAuth App
2. Set **Homepage URL**: `http://localhost:3000`
3. Set **Authorization callback URL**: `http://localhost:4000/api/auth/callback/github`
4. Copy the Client ID and Client Secret into `apps/api/.env`

## Privacy & Security

- Your `ANTHROPIC_API_KEY` stays on the server — never exposed to the browser
- GitHub OAuth tokens are encrypted by Better Auth — never stored in plain text
- Chat conversations and bootstrap context are scoped to the repository owner and cascade-deleted with the repo
- This app is designed to run **locally only**

## Project Structure

```
├── apps/
│   ├── portal/            # Chat-first portal UI (port 3000)
│   └── api/               # REST API + auth server (port 4000)
├── packages/
│   ├── ui/                # Shared component library
│   ├── auth/              # Better Auth client config
│   ├── shared/            # Shared types & utilities
│   └── typescript-config/ # Base tsconfig presets
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CODING-STANDARDS.md
│   └── TESTING.md
├── turbo.json
├── biome.json
└── pnpm-workspace.yaml
```

## Scripts

```bash
pnpm dev                # Start all apps
pnpm build              # Production build
pnpm typecheck          # Type-check everything
pnpm lint               # Lint all packages
pnpm format             # Format with Biome
```

## Git Hooks

Managed by **Husky**:

| Hook | What it does |
|---|---|
| `pre-commit` | Auto-fixes formatting and lint issues on staged files only, then re-stages those paths |
| `commit-msg` | Enforces [Conventional Commits](https://www.conventionalcommits.org/) |
| `pre-push` | Runs full build — blocks push on failure |
