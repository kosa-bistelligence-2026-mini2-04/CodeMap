# RepoLens - Architecture Documentation

## Architecture Overview

RepoLens is a **chat-first AI tool for any GitHub repository**, backed by a modular monolith. The default landing surface for any repo is a conversation grounded in selected source files plus the latest structured analysis. The structured analysis view (security, dependencies, architecture, etc) remains available as a secondary path.

```
repo-lens/
├── apps/
│   ├── portal/          # TanStack Start — chat-first portal (port 3000)
│   └── api/             # NestJS — REST + SSE API (port 4000)
├── packages/
│   ├── ui/              # Shared components (Shadcn + Radix + Markdown)
│   ├── auth/            # Shared Better Auth configuration
│   ├── shared/          # Types, constants and utilities (incl. chat domain)
│   └── typescript-config/
└── docs/
```

## Core Principles

1. **Feature Modules**: Each feature is self-contained in `modules/` with its own components, schemas, hooks and server functions
2. **Service Layer**: HTTP communication abstracted into service classes with dependency injection
3. **Use-cases (backend)**: Backend services are thin facades; each public method is implemented by a dedicated `*UseCase` class under `modules/{x}/use-cases/`. Cross-cutting helpers live in `apps/api/src/common/` (SSE pool, section parser, mappers, ownership guard)
4. **Go-style Error Handling**: `[Error | null, Data | null]` tuples throughout the service layer
5. **Type Safety**: Strict TypeScript with runtime validation via Zod
6. **Server Functions**: TanStack Start server functions for SSR data fetching
7. **SSE Streaming**: Chat replies and analysis sections stream via NestJS `@Sse()` Observables backed by RxJS Subjects pooled in `SseSubjectPool<TEvent>`

## Chat module (primary feature)

- **Entry point**: `/repos/$repoId/chat` (defaults to last conversation or empty state with prompt suggestions)
- **Persistence**: `chat` and `chat_message` tables (cascade-deleted with the repo). Each chat caches a `bootstrapContext` after the first message — a slice of the most relevant source files plus the latest analysis JSON — so subsequent turns avoid re-fetching the repo
- **Prompt suggestions**: Cross-product of detected **code areas** (modules) × analytical **lenses** (executive_summary, security, architecture, etc). Areas are detected by `ScopeMapperService` using a Claude Haiku call against the repo tree, cached on `repository.codeAreas` for 7 days
- **Streaming pipeline**: `SendMessageUseCase` writes user + assistant placeholder rows, builds the system prompt + history window, calls `anthropic.messages.stream`, and emits `ChatSseEvent` deltas via `SseSubjectPool`. Errors mark the assistant row `failed`

## Module Structure (Portal)

```
src/
├── common/
│   ├── constants/       # Constants (http-status-code, times, etc.)
│   └── utils/           # Pure utilities (logger, etc.)
├── lib/
│   └── auth-client.ts   # Configured Better Auth client
├── middleware/
│   └── auth.ts          # SSR auth middleware
├── modules/
│   └── {feature}/
│       ├── components/  # Feature components
│       ├── hooks/       # Feature-specific hooks
│       ├── schemas/     # Zod schemas
│       ├── domain/      # Domain types
│       └── server/      # Server functions (TanStack Start)
├── services/
│   ├── adapters/        # FetchHttpClientAdapter
│   ├── factories/       # httpClientFactory
│   ├── error.ts         # ApiError, AuthenticationError, ForbiddenError
│   └── http/
│       └── {entity}/
│           ├── {entity}-service.ts      # Service class
│           ├── use-{entity}-service.ts   # TanStack Query hooks
│           └── index.ts                  # Service instance
├── types/
│   └── http.ts          # HttpClient, RequestConfig, Response
├── env.ts               # Typed environment variables
├── routes/              # File-based routing
└── router.tsx           # TanStack Router configuration
```

## Service Layer Pattern

### HttpClient Interface

```ts
type HttpClient = {
  request<T>(config: RequestConfig): Promise<[ApiError | null, Response<T> | null]>
}

type RequestConfig = {
  url: string
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
  headers?: Record<string, string>
  params?: Record<string, string>
}
```

### Service Class

```ts
export type ISessionsService = {
  listSessions(): Promise<[Error | null, SessionItem[] | null]>
  revokeSession(token: string): Promise<[Error | null, RevokeSessionResponse | null]>
}

export class SessionsService implements ISessionsService {
  constructor(readonly httpClient: HttpClient) {}

  async listSessions(): Promise<[Error | null, SessionItem[] | null]> {
    const [error, response] = await this.httpClient.request<SessionItem[]>({
      url: '/sessions',
      method: 'GET'
    })

    if (error || !response) {
      return [error, null]
    }

    return [null, response.data]
  }
}
```

### Service Instance (index.ts)

```ts
import { env } from '@/env'
import { httpHttpClientFactory } from '@/services/factories/http-client-factory'
import { SessionsService } from './sessions-service'

const apiClient = httpHttpClientFactory(env.VITE_API_URL)

export const sessionsService = new SessionsService(apiClient)
```

### TanStack Query Hooks

```ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { sessionsService } from '.'

export const sessionsQueryKey = 'sessions' as const

export function useSessions() {
  return useQuery({
    queryKey: [sessionsQueryKey],
    queryFn: async () => {
      const [error, result] = await sessionsService.listSessions()

      if (error || !result) {
        throw error || new Error('Failed to fetch sessions')
      }

      return result
    },
  })
}

export function useRevokeSession() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (token: string) => {
      const [error, result] = await sessionsService.revokeSession(token)

      if (error || !result) {
        throw error || new Error('Failed to revoke session')
      }

      return result
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [sessionsQueryKey] })
    },
  })
}
```

### HTTP Request Examples

#### GET — List resources

```ts
async listSessions(): Promise<[Error | null, SessionItem[] | null]> {
  const [error, response] = await this.httpClient.request<SessionItem[]>({
    url: '/sessions',
    method: 'GET'
  })

  if (error || !response) return [error, null]
  return [null, response.data]
}
```

#### GET — Fetch by ID

```ts
async getById(id: string): Promise<[Error | null, User | null]> {
  const [error, response] = await this.httpClient.request<User>({
    url: `/users/${id}`,
    method: 'GET'
  })

  if (error || !response) return [error, null]
  return [null, response.data]
}
```

#### POST — Create resource

```ts
async create(data: CreateUserRequest): Promise<[Error | null, User | null]> {
  const [error, response] = await this.httpClient.request<User>({
    url: '/users',
    method: 'POST',
    body: data
  })

  if (error || !response) return [error, null]
  return [null, response.data]
}
```

#### PUT/PATCH — Update resource

```ts
async update(
  id: string,
  data: UpdateUserRequest
): Promise<[Error | null, User | null]> {
  const [error, response] = await this.httpClient.request<User>({
    url: `/users/${id}`,
    method: 'PATCH',
    body: data
  })

  if (error || !response) return [error, null]
  return [null, response.data]
}
```

#### DELETE — Remove resource

```ts
async delete(id: string): Promise<[Error | null, { success: boolean } | null]> {
  const [error, response] = await this.httpClient.request<{ success: boolean }>({
    url: `/users/${id}`,
    method: 'DELETE'
  })

  if (error || !response) return [error, null]
  return [null, response.data]
}
```

#### GET with Query Params

```ts
async search(
  query: string,
  page: number
): Promise<[Error | null, PaginatedResponse<User> | null]> {
  const [error, response] = await this.httpClient.request<PaginatedResponse<User>>({
    url: '/users',
    method: 'GET',
    params: {
      q: query,
      page: String(page),
      limit: '20'
    }
  })

  if (error || !response) return [error, null]
  return [null, response.data]
}
```

#### POST with FormData (Upload)

```ts
async uploadAvatar(
  userId: string,
  file: File
): Promise<[Error | null, { url: string } | null]> {
  const formData = new FormData()
  formData.append('avatar', file)

  const [error, response] = await this.httpClient.request<{ url: string }>({
    url: `/users/${userId}/avatar`,
    method: 'POST',
    body: formData
  })

  if (error || !response) return [error, null]
  return [null, response.data]
}
```

## State Management

### TanStack Query (Server State)

```ts
const { data, isLoading } = useQuery({
  queryKey: ['sessions'],
  queryFn: async () => {
    const [error, result] = await sessionsService.listSessions()
    if (error || !result) throw error || new Error('Failed')
    return result
  },
})
```

**Rules:**

- Use TanStack Query for all server-fetched data
- Use `useState` for simple component-local state
- Use Context + hooks for feature-scoped state

## Protected Routes

### TanStack Start Middleware

```ts
import { redirect } from '@tanstack/react-router'
import { createMiddleware } from '@tanstack/react-start'
import { getRequestHeaders } from '@tanstack/react-start/server'
import { authClient } from '@/lib/auth-client'

export const authMiddleware = createMiddleware().server(async ({ next }) => {
  const { data: session } = await authClient.getSession({
    fetchOptions: { headers: getRequestHeaders() },
  })

  if (!session) throw redirect({ to: '/auth/sign-in' })

  return next({ context: { session } })
})
```

### Protected Route Layout

```ts
export const Route = createFileRoute('/_authed')({
  component: AuthedLayout,
  server: {
    middleware: [authMiddleware],
  },
})
```

## Error Handling

### Custom Error Classes

```ts
export class ApiError extends Error {
  status: number
  statusText?: string
  url?: string
  method?: string
  code?: number

  constructor(data: ApiErrorData) { ... }
  toJSON() { ... }
  toString() { ... }
}

export class AuthenticationError extends ApiError {
  constructor() {
    super({ status: 401, code: 401, message: 'Unauthorized', error: true })
  }
}

export class ForbiddenError extends ApiError {
  constructor() {
    super({ status: 403, code: 403, message: 'Forbidden', error: true })
  }
}
```

### HTTP Status Codes

```ts
import { HttpStatusCodes } from '@/common/constants/http-status-code'

if (error.status === HttpStatusCodes.UNAUTHORIZED) {
  // Handle 401
}
```

## E2E Testing (Playwright)

End-to-end tests live in the `e2e/` directory at the monorepo root, organized by app (only `portal/`). The central configuration is in `playwright.config.ts`.

For full details on writing tests, best practices, and advanced patterns, see [`docs/TESTING.md`](TESTING.md).

## Backend (NestJS) — Conventions

### Module with RBAC

```ts
@Controller('sessions')
@Roles(['admin'])
export class SessionsController {
  constructor(private readonly sessionsService: SessionsService) {}

  @Get()
  async listSessions(@Session() session: UserSession) {
    return this.sessionsService.listSessions(session)
  }
}
```

### Available decorators (@thallesp/nestjs-better-auth)

- `@AllowAnonymous()` — Public route
- `@Roles(['admin'])` — Requires specific role
- `@Session()` — Inject user session
- `@OptionalAuth()` — Optional authentication

### Public vs protected routes

All routes are protected by default (global AuthGuard). To make a route public:

```ts
@AllowAnonymous()
@Get('health')
healthCheck() { return { status: 'ok' } }
```
