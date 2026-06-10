import { SECTION_ICONS } from '@/common/components/section-icons'
import { SECTION_META } from '@/common/constants/analysis-sections'
import type { ExecutiveSummarySection } from '@repo/shared'
import { SectionCard } from './section-card'

interface ExecutiveSummaryProps {
  data: ExecutiveSummarySection
  isStreaming?: boolean
}

export function ExecutiveSummarySectionView({ data, isStreaming }: ExecutiveSummaryProps) {
  const meta = SECTION_META.executive_summary
  return (
    <SectionCard
      icon={SECTION_ICONS.executive_summary}
      title={meta.label}
      description={meta.description}
      data={data}
      isStreaming={isStreaming}
    >
      <div className="space-y-4">
        <p className="text-sm leading-relaxed text-foreground">{data.summary}</p>
        <div className="grid sm:grid-cols-2 gap-3">
          <div className="p-3 rounded-lg bg-muted/40 space-y-1">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Target Audience
            </p>
            <p className="text-sm">{data.targetAudience}</p>
          </div>
          <div className="p-3 rounded-lg bg-muted/40 space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Key Capabilities
            </p>
            <ul className="space-y-1">
              {data.keyCapabilities.map((cap) => (
                <li key={cap} className="text-sm flex items-start gap-1.5">
                  <span className="text-primary mt-0.5">·</span>
                  {cap}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </SectionCard>
  )
}
