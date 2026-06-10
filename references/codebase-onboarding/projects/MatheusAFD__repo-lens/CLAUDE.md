# CLAUDE.md — RepoLens

> Reference guide for Claude Code to work in this monorepo.
> Full architecture and coding rules are in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), [`docs/CODING-STANDARDS.md`](docs/CODING-STANDARDS.md) and [`docs/TESTING.md`](docs/TESTING.md).

---

## Monorepo Structure

```
repo-ai-analyzer/
├── apps/
│   ├── portal/          # TanStack Start (port 3000) — end-user portal
│   └── api/             # NestJS + Express (port 4000) — REST API
├── packages/
│   ├── ui/              # Component library (Vite + Shadcn/UI + Radix UI)
│   ├── auth/            # Shared Better Auth configuration
│   ├── shared/          # Shared types and utilities
│   └── typescript-config/ # Reusable tsconfig bases
├── e2e/
│   └── portal/          # Portal E2E tests
├── docs/
│   ├── ARCHITECTURE.md
│   ├── CODING-STANDARDS.md
│   └── TESTING.md
├── playwright.config.ts
├── turbo.json
├── biome.json
└── pnpm-workspace.yaml
```

---

## Tech Stack

| Project | Technology | Port |
|---|---|---|
| `apps/portal` | TanStack Start v1, React 19, TanStack Query, Better Auth client | 3000 |
| `apps/api` | NestJS v11, Express, Drizzle ORM, Better Auth, PostgreSQL, Anthropic SDK | 4000 |
| `packages/ui` | Vite, React 19, Shadcn/UI (styling), Radix UI | — |
| `packages/auth` | better-auth (shared client factory) | — |
| `packages/shared` | Pure TypeScript — types and Result/ok/err utilities | — |

---

## Main Commands

```bash
# Install all dependencies
pnpm install

# Development (all projects in parallel)
pnpm dev

# Development for a specific project
pnpm --filter @repo/portal dev
pnpm --filter @repo/api dev

# Production build
pnpm build

# Typecheck all projects
pnpm typecheck

# Lint + format
pnpm lint
pnpm format

# Backend — Docker infrastructure
cd apps/api && docker-compose up -d

# Backend — Drizzle migrations
pnpm --filter @repo/api db:generate
pnpm --filter @repo/api db:migrate
pnpm --filter @repo/api db:studio

# E2E Tests (Playwright)
pnpm test:e2e                  # Run all E2E tests
pnpm test:e2e:portal           # Portal tests only
pnpm test:e2e:ui               # Interactive mode (UI Mode)
```

---

## Environment Variables

**IMPORTANT:** Each project has its own `.env.example`. Never commit `.env`.

### `apps/portal/.env`
```env
VITE_API_URL=http://localhost:4000
```

### `apps/api/.env`
```env
NODE_ENV=development
PORT=4000
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/repo_lens
BETTER_AUTH_SECRET=your-super-secret-key-change-in-production-min-32-chars
BETTER_AUTH_URL=http://localhost:4000
ALLOWED_ORIGINS=http://localhost:3000
ANTHROPIC_API_KEY=your-anthropic-api-key
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
```

---

## Recommended MCP Servers

Configure in your `~/.claude/settings.json` or `.claude/settings.local.json`:

```json
{
  "mcpServers": {
    "shadcn": {
      "command": "npx",
      "args": ["-y", "shadcn@latest", "mcp"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/matheusfernandes/www/personal/repo-ai-analyzer"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<your-token>"
      }
    }
  }
}
```

> **shadcn MCP**: allows Claude to add components directly with `npx shadcn@latest add <component>` in the `packages/ui` package.
> **filesystem MCP**: fast monorepo navigation.

---

## Key Patterns (summary — details in docs/)

### Error Handling (Go-style)

```ts
// ALWAYS use Result tuple in services
const [error, data] = await someService.doSomething()
if (error) return [error, null]
return [null, data]

// Helpers available in @repo/shared
import { ok, err, isErr } from '@repo/shared'
```

### File Naming

- Components: `kebab-case.tsx` (e.g. `login-form.tsx`)
- Hooks: `use-kebab-case.ts` (e.g. `use-auth-actions.ts`)
- Server functions: `kebab-case.fn.ts` (e.g. `get-session.fn.ts`)
- Schemas: `kebab-case.schema.ts` (e.g. `auth.schema.ts`)
- Types/domain: `kebab-case.domain.ts` (e.g. `user.domain.ts`)

### Exports

- **Named exports** everywhere (except TanStack routes that require default)
- Props interface: `{ComponentName}Props`

### No Comments in Code

- **Never add comments to code** — no inline comments (`//`), block comments (`/* */`), JSDoc (`/** */`), or JSX comments (`{/* */}`)
- Code must be self-documenting through clear naming and structure
- The only allowed exceptions are `biome-ignore` directives when a lint rule must be suppressed and there is no alternative

### Semantic Boolean Variables

- **Always extract complex boolean conditions into a named `const`** before using them in JSX or logic
- The name must express intent, not mechanics

```tsx
// ❌ Hard to read inline
{!isLoading && repos && repos.length > 0 && <RepoList />}

// ✅ Extract to semantic const
const hasRepos = !isLoading && !!repos && repos.length > 0
{hasRepos && <RepoList />}

// More examples
const showEmpty = !isLoading && !hasData
const hasError = !!error || (!isLoading && !data)
const canSubmit = isValid && !isSubmitting
```

### Import Aliases

```ts
// ✅ Use @/ alias for imports within the same app
import { cn } from '@/common/lib/utils'

// ✅ Use the package name for cross-package imports
import { Button } from '@repo/ui'
import { ok, err } from '@repo/shared'
```

### UI Components

Components in `packages/ui` use **Radix UI** as headless primitives, styled with Tailwind CSS v4 and CVA.

To add new Shadcn components to `packages/ui`:
```bash
cd packages/ui
npx shadcn@latest add <component>
```

---

## Module Structure (Portal)

```
src/modules/{feature}/
├── components/      # Feature-specific components
├── hooks/           # Feature-specific hooks (use-{feature}-actions.ts)
├── schemas/         # Zod schemas ({feature}.schema.ts)
├── server/          # TanStack Start server functions ({action}.fn.ts)
├── providers/       # Context providers (if needed)
└── domain/          # Domain types ({feature}.domain.ts)
```

---

## Backend — NestJS Conventions

### API Modules

The API has the following modules in `apps/api/src/modules/`:

- `chat/` — Conversational AI over a repository (Anthropic streaming SSE, prompt suggestions, scope mapper)
- `analysis/` — Structured AI analysis pipeline (Anthropic SDK, SSE streaming, section parser)
- `github/` — GitHub OAuth and repository access
- `repos/` — Repository management and analysis orchestration
- `sessions/` — User session management

### Module Layout (use-case pattern)

Each module is split into thin facade services and single-responsibility use-cases:

```
modules/{module}/
├── {module}.controller.ts     # HTTP layer
├── {module}.module.ts         # NestJS module wiring
├── {module}.service.ts        # Facade — delegates to use-cases
├── use-cases/
│   ├── {verb-noun}.use-case.ts  # One per public method
│   └── ...
├── dto/                        # Request DTOs
└── (optional builders / mappers)
```

Conventions:

- Use-case file name: `{verb}-{noun}.use-case.ts` (e.g. `create-chat.use-case.ts`).
- Class name: `{Verb}{Noun}UseCase`, single public method `execute(params)` taking a plain object.
- Returns `Result<T>` (Go-tuple) where the service contract uses Result, throws `NotFoundException`/`ForbiddenException` where the controller/spec relies on try-throw.
- `@Injectable()` on every use-case, deps injected via constructor.
- Service stays as a facade so controllers and cross-module callers (e.g. `ChatService` consuming `AnalysisService.getLatestAnalysis`) keep their existing signatures.

### Common helpers — `apps/api/src/common/`

Shared utilities reused across modules:

- `streaming/sse-subject-pool.ts` — generic `Map<string, Subject<MessageEvent>>` with `create/emit/complete/get`. Used by chat and analysis streaming pipelines.
- `streaming/sse-emitter.ts` — `toMessageEvent(event)` helper.
- `parsing/section-parser.ts` — pure `parseSections(buffer)` for `##BEGIN/END_SECTION##` markers used by structured analysis.
- `mappers/chat.mapper.ts` and `mappers/analysis.mapper.ts` — row-to-DTO functions.
- `guards/ownership.ts` — `assertOwner({ row, userId, ... })` guard, throws on missing/foreign rows.

### Create a new module
```bash
nest g module modules/{name}
nest g controller modules/{name}
nest g service modules/{name}
```

### Protected vs public routes
```ts
// All routes are protected by default (global AuthGuard)
// To make a route public:
import { AllowAnonymous } from '@thallesp/nestjs-better-auth'

@AllowAnonymous()
@Get('health')
healthCheck() { ... }
```

### Get user session
```ts
import { Session, type UserSession } from '@thallesp/nestjs-better-auth'

@Get('me')
getMe(@Session() session: UserSession) { return session.user }
```

### Better Auth on the Backend

Better Auth exposes all authentication routes at `/api/auth/*`. The `AuthModule` from `@thallesp/nestjs-better-auth` bridges Express and the Better Auth handler. **Do not** create authentication routes manually.

---

## Infrastructure (Docker)

```bash
# Start PostgreSQL locally
cd apps/api
docker-compose up -d

# Check services
docker-compose ps

# Stop
docker-compose down

# Stop and remove volumes (CAUTION: deletes data)
docker-compose down -v
```

Available services after `docker-compose up`:
- PostgreSQL: `localhost:5432` (user: `postgres`, pass: `postgres`, db: `repo_lens`)

---

## Git Hooks (Husky)

Git hooks are managed by [Husky](https://typicode.github.io/husky/) and enforce quality checks automatically.

| Hook | Trigger | Action |
|---|---|---|
| `pre-commit` | `git commit` | Runs `pnpm format:check && pnpm lint` |
| `commit-msg` | `git commit` | Validates [Conventional Commits](https://www.conventionalcommits.org/) via commitlint |
| `pre-push` | `git push` | Runs `pnpm build` — push is blocked if build fails |

### Conventional Commit Format

```
type(scope): description

# Examples:
feat(portal): add repository analysis page
fix(api): handle null session in auth middleware
chore: update dependencies
docs: update ARCHITECTURE.md
refactor(ui): extract card variants
```

Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`.

---

## Development Workflow

1. `docker-compose up -d` in the backend to start the database
2. Copy `.env.example` to `.env` in each app and fill in values
3. `pnpm install` at the root
4. `pnpm --filter @repo/api db:migrate` to run migrations
5. `pnpm dev` to start all services

---

## References

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Architecture and service patterns
- [docs/CODING-STANDARDS.md](docs/CODING-STANDARDS.md) — Detailed coding standards
- [docs/TESTING.md](docs/TESTING.md) — E2E testing guide
- [TanStack Start](https://tanstack.com/start/latest)
- [TanStack Router](https://tanstack.com/router/latest)
- [Better Auth](https://www.better-auth.com)
- [Radix UI](https://www.radix-ui.com)
- [Shadcn/UI](https://ui.shadcn.com)
- [NestJS](https://nestjs.com)
- [Drizzle ORM](https://orm.drizzle.team)
- [Playwright](https://playwright.dev)
- [Turborepo](https://turbo.build)
- [Anthropic SDK](https://github.com/anthropics/anthropic-sdk-typescript)
