import { Skeleton } from '@repo/ui/components/skeleton'

interface GroupSkeletonProps {
  title: string
  description: string
  chipCount: number
  chipWidths: string[]
}

const GROUPS: GroupSkeletonProps[] = [
  {
    title: 'Code areas',
    description: 'Modules detected in this repository',
    chipCount: 6,
    chipWidths: ['w-24', 'w-32', 'w-28', 'w-36', 'w-24', 'w-28'],
  },
  {
    title: 'Lenses',
    description: 'Pick an analytical perspective',
    chipCount: 9,
    chipWidths: ['w-32', 'w-24', 'w-28', 'w-24', 'w-32', 'w-28', 'w-32', 'w-28', 'w-24'],
  },
  {
    title: 'Combined',
    description: 'A lens applied to a specific area',
    chipCount: 6,
    chipWidths: ['w-44', 'w-48', 'w-40', 'w-44', 'w-48', 'w-40'],
  },
]

export function SuggestionsSkeleton() {
  return (
    <div className="flex flex-col gap-5" aria-busy="true" aria-live="polite">
      {GROUPS.map((group) => (
        <div key={group.title} className="space-y-2">
          <div className="flex flex-col">
            <span className="text-sm font-medium text-foreground">{group.title}</span>
            <span className="text-xs text-muted-foreground">{group.description}</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {Array.from({ length: group.chipCount }).map((_, i) => (
              <Skeleton
                // biome-ignore lint/suspicious/noArrayIndexKey: static skeleton list
                key={i}
                className={`h-8 ${group.chipWidths[i] ?? 'w-28'} rounded-full`}
              />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
