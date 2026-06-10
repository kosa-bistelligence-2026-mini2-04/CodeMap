import { useTheme, type ThemeMode } from '@/common/hooks/use-dark-mode'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@repo/ui/components/dropdown-menu'
import { Button } from '@repo/ui/components/button'
import { cn } from '@repo/ui/lib/utils'

const THEMES: { value: ThemeMode; label: string; description: string }[] = [
  { value: 'light', label: 'Light', description: 'Clean white — high readability' },
  { value: 'dark', label: 'Dark', description: 'Charcoal dark — easy on the eyes' },
  { value: 'system', label: 'System', description: 'Follow your OS preference' },
]

export function ThemeSelector() {
  const { mode, setMode } = useTheme()
  const current = THEMES.find((t) => t.value === mode) ?? THEMES[0]

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          aria-label={`Theme: ${current.label}`}
        >
          <ThemeIcon mode={mode} />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        <div className="px-2 pt-2 pb-1">
          <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-widest">
            Theme
          </p>
        </div>
        {THEMES.map((theme) => (
          <DropdownMenuItem
            key={theme.value}
            onClick={() => setMode(theme.value)}
            className={cn(
              'cursor-pointer flex flex-col items-start gap-0 py-2',
              mode === theme.value && 'bg-muted',
            )}
          >
            <div className="flex items-center gap-2 w-full">
              <span className="text-sm font-medium flex-1">{theme.label}</span>
              {mode === theme.value && (
                <svg
                  aria-hidden="true"
                  viewBox="0 0 24 24"
                  className="w-3.5 h-3.5 shrink-0"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              )}
            </div>
            <p className="text-[11px] text-muted-foreground">{theme.description}</p>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

function ThemeIcon({ mode }: { mode: ThemeMode }) {
  if (mode === 'light') {
    return (
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        className="w-4 h-4 fill-none stroke-current"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <circle cx="12" cy="12" r="5" />
        <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
      </svg>
    )
  }
  if (mode === 'system') {
    return (
      <svg
        aria-hidden="true"
        viewBox="0 0 24 24"
        className="w-4 h-4 fill-none stroke-current"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="2" y="3" width="20" height="14" rx="2" />
        <path d="M8 21h8M12 17v4" />
      </svg>
    )
  }
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className="w-4 h-4 fill-none stroke-current"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  )
}
