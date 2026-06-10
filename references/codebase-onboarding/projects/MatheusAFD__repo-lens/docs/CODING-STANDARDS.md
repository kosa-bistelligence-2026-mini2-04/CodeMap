# Coding Standards

## File Naming

- **Components**: kebab-case (e.g., `pet-info-card.tsx`)
- **Utilities/Services**: kebab-case (e.g., `pet-service.ts`)
- **Hooks**: kebab-case with `use-` prefix (e.g., `use-auth-actions.ts`)
- **Constants**: kebab-case (e.g., `http-status-code.ts`)
- **Types/Domain**: kebab-case with `.domain` suffix (e.g., `pet.domain.ts`)

## Component Patterns

### 1. Component Structure

```tsx
import { type ComponentProps } from 'react'
import { cn } from '@/common/lib/utils'

interface MyComponentProps extends ComponentProps<'div'> {
  variant?: 'default' | 'primary'
  isActive?: boolean
}

export function MyComponent(props: MyComponentProps) {
  const { variant = 'default', isActive, className, children, ...rest } = props

  return (
    <div className={cn('base-classes', className)} {...rest}>
      {children}
    </div>
  )
}
```

**Rules:**

- Use named exports (no default exports except routes)
- Props interface named `{ComponentName}Props`
- Extend `ComponentProps<T>` when wrapping native elements
- Destructure all props in function signature
- Use `cn()` utility for conditional classes

### 2. Form Field Components

Field components include label, input, and error message:

```tsx
interface TextFieldProps extends ComponentProps<typeof Input> {
  label: string
  errorMessage?: string
}

export function TextField(props: TextFieldProps) {
  const { label, errorMessage, className, ...rest } = props
  const fieldId = useId()

  return (
    <fieldset>
      <Label htmlFor={fieldId}>{label}</Label>
      <Input id={fieldId} aria-invalid={!!errorMessage} {...rest} />
      {errorMessage && <ErrorMessage>{errorMessage}</ErrorMessage>}
    </fieldset>
  )
}
```

### 3. Server Functions

Use TanStack Start server functions for SSR data:

```tsx
import { createServerFn } from '@tanstack/react-start'

export const getPetByTrackingCodeFn = createServerFn(
  'GET',
  async (trackingCode: string) => {
    const petService = PetServiceFactory.create()
    return await petService.getPetByTrackingCode(trackingCode)
  },
)
```

## Schema Validation

Use Zod for runtime validation:

```tsx
import { z } from 'zod'

export const petFormSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  species: z.enum(['dog', 'cat']),
  breed: z.string().optional(),
})

export type PetFormInput = z.infer<typeof petFormSchema>
```

**Rules:**

- One schema file per feature in `modules/{feature}/schemas/`
- Export both schema and inferred type

## Type Naming — Request / Response

Types that represent API payloads (form submissions, mutations, queries) must use the `...Request` / `...Response` suffix. Never use `...Input`, `...Output`, `...Payload`, `...Data`, or `...Dto`.

```ts
// ✅ Correct
type SignInRequest = z.infer<typeof signInSchema>
type SignUpRequest = z.infer<typeof signUpSchema>
type CreatePetRequest = z.infer<typeof createPetSchema>
type UpdateUserRequest = z.infer<typeof updateUserSchema>
type GetPetResponse = { id: string; name: string; species: string }

// ❌ Incorrect
type LoginInput = ...
type RegisterInput = ...
type CreatePetPayload = ...
type UpdateUserDto = ...
```

**Rules:**

- Schemas: `{verb}{noun}Schema` (e.g. `signInSchema`, `createPetSchema`)
- Request types: `{VerbNoun}Request` (e.g. `SignInRequest`, `CreatePetRequest`)
- Response types: `{VerbNoun}Response` (e.g. `GetPetResponse`, `ListUsersResponse`)
- Use `.min()`, `.max()`, etc. with custom error messages
- Colocate domain types in `domain/` folder

## Styling Rules

### Tailwind Usage

```tsx
// ✅ Good - Semantic class grouping
<div className="flex items-center gap-2 p-4 rounded-lg bg-white shadow-sm">

// ❌ Bad - Random order
<div className="p-4 flex rounded-lg gap-2 shadow-sm items-center bg-white">
```

**Class Order:**

1. Layout (flex, grid, block)
2. Positioning (relative, absolute)
3. Spacing (p-, m-, gap-)
4. Sizing (w-, h-)
5. Typography (text-, font-)
6. Colors (bg-, text-, border-)
7. Effects (shadow-, rounded-)

### Using `cn()` Utility

```tsx
import { cn } from '@/common/lib/utils'

<Button
  className={cn(
    'base-classes',
    variant === 'primary' && 'variant-classes',
    isActive && 'active-classes',
    className, // Always last - allows override
  )}
/>
```

### Variants with CVA

For components with multiple variants:

```tsx
import { cva, type VariantProps } from 'class-variance-authority'

const buttonVariants = cva('base-classes', {
  variants: {
    variant: {
      default: 'default-classes',
      primary: 'primary-classes',
    },
    size: {
      sm: 'sm-classes',
      md: 'md-classes',
    },
  },
  defaultVariants: {
    variant: 'default',
    size: 'md',
  },
})

interface ButtonProps extends VariantProps<typeof buttonVariants> {}
```

## TypeScript Guidelines

### Type vs Interface

```tsx
// ✅ Use interface for objects
interface User {
  id: string
  email: string
}

// ✅ Use type for unions, primitives, utilities
type Status = 'pending' | 'active' | 'inactive'
type InputWithLabel = ComponentProps<'input'> & { label: string }
```

### Type Imports

```tsx
// ✅ Explicit type imports
import { type User, type UserInput } from '@/domain/user.domain'
import { UserService } from '@/services/http/user/user-service'

// ❌ Avoid mixing value and type imports
import { User, UserService } from '@/services/user'
```

### Generics

```tsx
// Service method with generic return type
async request<T>(config: RequestConfig): Promise<HttpResponse<T>> {
  // implementation
}

// Component with generic props
interface ListProps<T> {
  items: T[]
  renderItem: (item: T) => ReactNode
}
```

## Import Aliases

Use `@/` for absolute imports:

```tsx
// ✅ Absolute imports
import { cn } from '@/common/lib/utils'
import { useAuth } from '@/modules/auth/providers/auth-provider'

// ❌ Avoid relative imports beyond parent
import { cn } from '../../../common/lib/utils'
```

## Contributing Guidelines

1. Follow the established folder structure
2. Use Biome for code formatting (runs on commit via Husky)
3. Write tests for new features
4. Use TypeScript strictly (no `any` types)
5. Keep components small and focused (< 200 lines)
6. Prefer composition over inheritance
