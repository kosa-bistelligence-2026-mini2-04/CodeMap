import { cn } from '@repo/ui/lib/utils'
import type { ViewMode } from '../hooks/use-view-mode'

interface ViewModeToggleProps {
  value: ViewMode
  onChange: (mode: ViewMode) => void
}

const OPTIONS: { value: ViewMode; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'product', label: 'Product' },
  { value: 'technical', label: 'Technical' },
]

export function ViewModeToggle({ value, onChange }: ViewModeToggleProps) {
  return (
    <div className="flex items-center gap-0.5 rounded-lg bg-muted p-0.5">
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          data-testid={`btn-view-mode-${option.value}`}
          className={cn(
            'px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer',
            value === option.value
              ? 'bg-background text-foreground shadow-sm'
              : 'text-muted-foreground hover:text-foreground',
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
