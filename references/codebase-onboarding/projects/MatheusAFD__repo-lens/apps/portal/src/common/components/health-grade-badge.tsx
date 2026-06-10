import type { SecurityGrade } from '@repo/shared'
import { cn } from '@repo/ui/lib/utils'

interface HealthGradeBadgeProps {
  grade: SecurityGrade
  className?: string
  size?: 'sm' | 'md' | 'lg'
}

const GRADE_STYLES: Record<SecurityGrade, string> = {
  A: 'bg-green-500/15 text-green-600 dark:text-green-400 border-green-500/30',
  B: 'bg-teal-500/15 text-teal-600 dark:text-teal-400 border-teal-500/30',
  C: 'bg-yellow-500/15 text-yellow-600 dark:text-yellow-400 border-yellow-500/30',
  D: 'bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-500/30',
  F: 'bg-red-500/15 text-red-600 dark:text-red-400 border-red-500/30',
}

const SIZE_STYLES = {
  sm: 'h-5 w-5 text-xs',
  md: 'h-7 w-7 text-sm',
  lg: 'h-10 w-10 text-base',
}

export function HealthGradeBadge({ grade, className, size = 'md' }: HealthGradeBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center justify-center rounded border font-bold',
        GRADE_STYLES[grade],
        SIZE_STYLES[size],
        className,
      )}
      title={`Security grade: ${grade}`}
    >
      {grade}
    </span>
  )
}
