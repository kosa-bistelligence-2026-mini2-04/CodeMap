import { SECTION_ICONS } from '@/common/components/section-icons'
import { SECTION_META } from '@/common/constants/analysis-sections'
import type { DependenciesSection as DependenciesSectionData } from '@repo/shared'
import { Badge } from '@repo/ui/components/badge'
import { cn } from '@repo/ui/lib/utils'
import { SectionCard } from './section-card'

interface DependenciesSectionProps {
  data: DependenciesSectionData
  isStreaming?: boolean
}

export function DependenciesSection({ data, isStreaming }: DependenciesSectionProps) {
  const meta = SECTION_META.dependencies
  return (
    <SectionCard
      icon={SECTION_ICONS.dependencies}
      title={meta.label}
      description={meta.description}
      data={data}
      isStreaming={isStreaming}
    >
      <div className="space-y-5">
        <div className="grid grid-cols-3 gap-3">
          <div className="p-3 rounded-lg bg-muted/40 text-center">
            <p className="text-2xl font-bold">{data.total}</p>
            <p className="text-xs text-muted-foreground">Total</p>
          </div>
          <div className="p-3 rounded-lg bg-yellow-500/10 text-center">
            <p className="text-2xl font-bold text-yellow-600 dark:text-yellow-400">
              {data.ecosystems.reduce((sum, ecosystem) => sum + ecosystem.outdated, 0)}
            </p>
            <p className="text-xs text-muted-foreground">Outdated</p>
          </div>
          <div className="p-3 rounded-lg bg-red-500/10 text-center">
            <p className="text-2xl font-bold text-red-600 dark:text-red-400">
              {data.ecosystems.reduce((sum, ecosystem) => sum + ecosystem.vulnerable, 0)}
            </p>
            <p className="text-xs text-muted-foreground">Vulnerable</p>
          </div>
        </div>

        {data.highlights.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Notable packages
            </p>
            <div className="space-y-1">
              {data.highlights.map((dep) => (
                <div
                  key={dep.name}
                  className="flex items-center justify-between gap-3 py-1.5 border-b border-border/40 last:border-0"
                >
                  <span className="text-sm font-mono">{dep.name}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="text-xs text-muted-foreground font-mono">{dep.version}</span>
                    <Badge
                      variant="outline"
                      className={cn(
                        'text-[10px] h-4 px-1.5',
                        dep.status === 'ok' &&
                          'text-green-600 dark:text-green-400 border-green-500/30',
                        dep.status === 'outdated' &&
                          'text-yellow-600 dark:text-yellow-400 border-yellow-500/30',
                        dep.status === 'vulnerable' &&
                          'text-red-600 dark:text-red-400 border-red-500/30',
                      )}
                    >
                      {dep.status === 'outdated' ? `→ ${dep.latestVersion}` : dep.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </SectionCard>
  )
}
