# Services Layer — Guide for Claude

## Structure

```
services/
├── adapters/
│   └── fetch-adapter.ts       # FetchHttpClientAdapter — implements HttpClient
├── factories/
│   └── http-client-factory.ts # httpHttpClientFactory — creates adapter instances
├── error.ts                   # ApiError, AuthenticationError, ForbiddenError
└── http/
    └── {entity}/
        ├── {entity}-service.ts      # Service class with HTTP methods
        ├── use-{entity}-service.ts   # TanStack Query hooks (useQuery/useMutation)
        └── index.ts                  # Singleton service instance
```

## How to Create a New Service

### 1. Domain types (`modules/{feature}/domain/{entity}.domain.ts`)

```ts
export interface User {
  id: string
  name: string
  email: string
}

export interface CreateUserRequest {
  name: string
  email: string
}

export interface CreateUserResponse {
  user: User
}
```

### 2. Service class (`services/http/{entity}/{entity}-service.ts`)

```ts
import type { CreateUserRequest, CreateUserResponse, User } from '@/modules/users/domain/user.domain'
import type { HttpClient } from '@/types/http'

export type IUsersService = {
  list(): Promise<[Error | null, User[] | null]>
  create(data: CreateUserRequest): Promise<[Error | null, CreateUserResponse | null]>
}

export class UsersService implements IUsersService {
  constructor(readonly httpClient: HttpClient) {}

  async list(): Promise<[Error | null, User[] | null]> {
    const [error, response] = await this.httpClient.request<User[]>({
      url: '/users',
      method: 'GET'
    })

    if (error || !response) return [error, null]
    return [null, response.data]
  }

  async create(data: CreateUserRequest): Promise<[Error | null, CreateUserResponse | null]> {
    const [error, response] = await this.httpClient.request<CreateUserResponse>({
      url: '/users',
      method: 'POST',
      body: data
    })

    if (error || !response) return [error, null]
    return [null, response.data]
  }
}
```

### 3. Index (`services/http/{entity}/index.ts`)

```ts
import { env } from '@/env'
import { httpHttpClientFactory } from '@/services/factories/http-client-factory'
import { UsersService } from './users-service'

const apiClient = httpHttpClientFactory(env.VITE_API_URL)

export const usersService = new UsersService(apiClient)
```

### 4. Query hooks (`services/http/{entity}/use-{entity}-service.ts`)

```ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { usersService } from '.'

export const usersQueryKey = 'users' as const

// GET → useQuery
export function useUsers() {
  return useQuery({
    queryKey: [usersQueryKey],
    queryFn: async () => {
      const [error, result] = await usersService.list()
      if (error || !result) throw error || new Error('Failed to fetch users')
      return result
    },
  })
}

// POST/PUT/DELETE → useMutation + invalidateQueries
export function useCreateUser() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: async (data: CreateUserRequest) => {
      const [error, result] = await usersService.create(data)
      if (error || !result) throw error || new Error('Failed to create user')
      return result
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [usersQueryKey] })
    },
  })
}
```

## Rules

- **Always** use Go-style tuple `[Error | null, Data | null]` in service methods
- **Always** use `throw` inside `queryFn`/`mutationFn` to propagate errors to TanStack Query
- **Always** `invalidateQueries` in `onSuccess` of mutations to keep data up to date
- **Never** use `try/catch` in the service layer — the adapter already returns tuples
- **Never** use names like `Input`, `Output`, `Payload`, `Dto` — use `Request` and `Response`
- The `index.ts` creates the singleton instance — hooks and components import from it
- The `FetchHttpClientAdapter` auto-detects `FormData` and removes the `Content-Type: application/json` header
