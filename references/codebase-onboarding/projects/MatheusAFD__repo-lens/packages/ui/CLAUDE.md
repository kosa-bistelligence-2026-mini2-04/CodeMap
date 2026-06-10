# CLAUDE.md — packages/ui

> Shared component library. React 19, Radix UI, Tailwind CSS v4, CVA.
> Consumed by `apps/portal` and `apps/backoffice` via `@repo/ui`.

---

## Available Components

| Component | Import path | Main exports |
|---|---|---|
| Button | `@repo/ui/components/button` | `Button`, `buttonVariants` |
| Input | `@repo/ui/components/input` | `Input` |
| Label | `@repo/ui/components/label` | `Label` |
| Card | `@repo/ui/components/card` | `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter` |
| Dialog | `@repo/ui/components/dialog` | `Dialog`, `DialogContent`, `DialogHeader`, `DialogTitle`, etc. |
| Select | `@repo/ui/components/select` | `Select`, `SelectTrigger`, `SelectContent`, `SelectItem`, etc. |
| Checkbox | `@repo/ui/components/checkbox` | `Checkbox` |
| Tooltip | `@repo/ui/components/tooltip` | `TooltipProvider`, `Tooltip`, `TooltipTrigger`, `TooltipContent` |
| Badge | `@repo/ui/components/badge` | `Badge`, `badgeVariants` |
| Separator | `@repo/ui/components/separator` | `Separator` |

Or import everything from `@repo/ui` (barrel export).

---

## Usage in Apps

```tsx
// Per-component import (optimized tree-shaking)
import { Button } from '@repo/ui/components/button'
import { Input } from '@repo/ui/components/input'
import { Label } from '@repo/ui/components/label'
import { Card, CardContent, CardHeader, CardTitle } from '@repo/ui/components/card'

// Barrel import (convenient)
import { Button, Input, Label, Card } from '@repo/ui'
```

---

## Adding New Components (Shadcn)

```bash
cd packages/ui
npx shadcn@latest add <component>
```

**Note:** This project uses **Radix UI** as headless primitives (not Base UI). Components added via the Shadcn CLI already use Radix, so **do not replace** Radix imports.

---

## Creating Custom Components

Required pattern:

```tsx
import type { ComponentProps } from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

// Use CVA for variants
const myVariants = cva('base-classes', {
  variants: {
    variant: { default: '...', primary: '...' },
    size: { sm: '...', md: '...' },
  },
  defaultVariants: { variant: 'default', size: 'md' },
})

interface MyComponentProps extends ComponentProps<'div'>, VariantProps<typeof myVariants> {}

export function MyComponent(props: MyComponentProps) {
  const { variant, size, className, children, ...rest } = props
  return (
    <div className={cn(myVariants({ variant, size }), className)} {...rest}>
      {children}
    </div>
  )
}
```

**Rules:**
- Named exports (no `export default`)
- Props interface `{ComponentName}Props`
- Always spread `...rest` to support native attributes
- Use `cn()` from `@/lib/utils` to merge classes
- Components with variants use CVA
- File in `src/components/kebab-case.tsx`
- Export in `src/index.ts` (barrel)

---

## Button — Variants

```tsx
<Button>Default</Button>
<Button variant="destructive">Delete</Button>
<Button variant="outline">Cancel</Button>
<Button variant="secondary">Secondary</Button>
<Button variant="ghost">Ghost</Button>
<Button variant="link">Link</Button>

// Sizes
<Button size="sm">Small</Button>
<Button size="lg">Large</Button>
<Button size="icon"><Icon /></Button>
```

---

## Package Structure

```
src/
├── components/     # One file per component
├── hooks/          # Reusable hooks (empty for now)
├── lib/
│   └── utils.ts    # cn() helper (clsx + tailwind-merge)
├── styles/
│   └── globals.css # Global CSS with theme variables
└── index.ts        # Barrel export of everything
```

---

## References

- [Radix UI](https://www.radix-ui.com)
- [Shadcn/UI](https://ui.shadcn.com)
- [CVA](https://cva.style)
- [Tailwind CSS v4](https://tailwindcss.com)
