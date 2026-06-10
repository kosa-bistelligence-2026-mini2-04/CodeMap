import { SECTION_ICONS } from '@/common/components/section-icons'
import { SECTION_META } from '@/common/constants/analysis-sections'
import type { AnalysisProgressSection as AnalysisProgressSectionData } from '@repo/shared'
import { cn } from '@repo/ui/lib/utils'
import { SectionCard } from './section-card'

interface AnalysisProgressSectionProps {
  data: AnalysisProgressSectionData
  isStreaming?: boolean
}

export function AnalysisProgressSection({ data, isStreaming }: AnalysisProgressSectionProps) {
  const meta = SECTION_META.analysis_progress
  const scoreImproved = data.scoreChange > 0
  const scoreRegressed = data.scoreChange < 0
  const scoreUnchanged = data.scoreChange === 0

  const scoreDeltaLabel = scoreImproved
    ? `+${data.scoreChange}`
    : scoreRegressed
      ? `${data.scoreChange}`
      : '±0'

  const scoreDeltaClass = scoreImproved
    ? 'text-emerald-500'
    : scoreRegressed
      ? 'text-red-500'
      : 'text-muted-foreground'

  return (
    <SectionCard
      icon={SECTION_ICONS.analysis_progress}
      title={meta.label}
      description={meta.description}
      data={data}
      isStreaming={isStreaming}
    >
      <div className="space-y-5">
        <div className="flex items-center gap-6">
          <div className="flex flex-col items-center justify-center w-16 h-16 rounded-xl border border-border bg-muted/40">
            <span className={cn('text-xl font-bold tabular-nums', scoreDeltaClass)}>
              {scoreDeltaLabel}
            </span>
            <span className="text-[10px] text-muted-foreground mt-0.5">score</span>
          </div>
          <div className="flex-1 min-w-0">
            {data.gradeChange && (
              <p className="text-sm font-semibold mb-0.5">
                Grade:{' '}
                <span
                  className={cn(
                    scoreImproved && 'text-emerald-500',
                    scoreRegressed && 'text-red-500',
                  )}
                >
                  {data.gradeChange}
                </span>
              </p>
            )}
            {scoreUnchanged && !data.gradeChange && (
              <p className="text-sm font-semibold text-muted-foreground mb-0.5">No grade change</p>
            )}
            <p className="text-sm text-muted-foreground leading-snug">{data.summary}</p>
          </div>
        </div>

        {data.fixedIssues.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Fixed & improved
            </p>
            <div className="space-y-1.5">
              {data.fixedIssues.map((item) => (
                <div
                  key={item.title}
                  className="flex items-start gap-3 p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5"
                >
                  <span className="text-emerald-500 mt-0.5 shrink-0 text-base leading-none">✓</span>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-emerald-600 dark:text-emerald-400">
                      {item.title}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.newIssues.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              New issues found
            </p>
            <div className="space-y-1.5">
              {data.newIssues.map((item) => (
                <div
                  key={item.title}
                  className="flex items-start gap-3 p-3 rounded-lg border border-orange-500/20 bg-orange-500/5"
                >
                  <span className="text-orange-500 mt-0.5 shrink-0 text-base leading-none">!</span>
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-orange-600 dark:text-orange-400">
                      {item.title}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">{item.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.fixedIssues.length === 0 && data.newIssues.length === 0 && (
          <p className="text-sm text-muted-foreground">
            No significant changes detected between analyses.
          </p>
        )}
      </div>
    </SectionCard>
  )
}
