import { SECTION_ICONS } from '@/common/components/section-icons'
import { SECTION_META } from '@/common/constants/analysis-sections'
import type {
  EffortLevel,
  RecommendationsSection as RecommendationsSectionData,
} from '@repo/shared'
import { Badge } from '@repo/ui/components/badge'
import { cn } from '@repo/ui/lib/utils'
import { SectionCard } from './section-card'

interface RecommendationsSectionProps {
  data: RecommendationsSectionData
  isStreaming?: boolean
}

const EFFORT_STYLES: Record<EffortLevel, string> = {
  low: 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20',
  medium: 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/20',
  high: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20',
}

const IMPACT_STYLES: Record<EffortLevel, string> = {
  low: 'text-muted-foreground',
  medium: 'text-yellow-600 dark:text-yellow-400',
  high: 'text-green-600 dark:text-green-400',
}

export function RecommendationsSection({ data, isStreaming }: RecommendationsSectionProps) {
  const meta = SECTION_META.recommendations
  return (
    <SectionCard
      icon={SECTION_ICONS.recommendations}
      title={meta.label}
      description={meta.description}
      data={data}
      isStreaming={isStreaming}
    >
      <div className="space-y-2">
        {data.items.map((item) => (
          <div
            key={item.rank}
            className="flex items-start gap-3 p-3 rounded-lg border border-border/60 hover:border-border transition-colors"
          >
            <div className="w-6 h-6 rounded-full bg-muted flex items-center justify-center shrink-0 text-xs font-bold">
              {item.rank}
            </div>
            <div className="min-w-0 flex-1 space-y-1.5">
              <p className="text-sm font-medium">{item.title}</p>
              <p className="text-xs text-muted-foreground leading-relaxed">{item.rationale}</p>
              <div className="flex items-center gap-2 flex-wrap">
                <Badge
                  variant="outline"
                  className={cn('text-[10px] h-4 px-1.5', EFFORT_STYLES[item.effort])}
                >
                  effort: {item.effort}
                </Badge>
                <span className={cn('text-[11px] font-medium', IMPACT_STYLES[item.impact])}>
                  {item.impact} impact
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </SectionCard>
  )
}
