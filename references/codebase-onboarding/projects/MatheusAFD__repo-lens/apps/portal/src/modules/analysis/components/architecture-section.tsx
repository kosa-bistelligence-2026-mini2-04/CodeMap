import { SECTION_ICONS } from '@/common/components/section-icons'
import { SECTION_META } from '@/common/constants/analysis-sections'
import type { ArchitectureSection as ArchitectureSectionData } from '@repo/shared'
import { Badge } from '@repo/ui/components/badge'
import { SectionCard } from './section-card'

interface ArchitectureSectionProps {
  data: ArchitectureSectionData
  isStreaming?: boolean
}

export function ArchitectureSection({ data, isStreaming }: ArchitectureSectionProps) {
  const meta = SECTION_META.architecture
  return (
    <SectionCard
      icon={SECTION_ICONS.architecture}
      title={meta.label}
      description={meta.description}
      data={data}
      isStreaming={isStreaming}
    >
      <div className="space-y-4">
        <div className="flex items-start gap-3">
          <Badge variant="secondary" className="shrink-0">
            {data.pattern}
          </Badge>
          <p className="text-sm text-muted-foreground leading-relaxed">{data.description}</p>
        </div>
        {data.keyPatterns.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Key Patterns
            </p>
            <div className="flex flex-wrap gap-1.5">
              {data.keyPatterns.map((pattern) => (
                <Badge key={pattern} variant="outline" className="text-xs">
                  {pattern}
                </Badge>
              ))}
            </div>
          </div>
        )}
        {data.observations.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Observations
            </p>
            <ul className="space-y-1.5">
              {data.observations.map((obs) => (
                <li key={obs} className="text-sm text-foreground flex items-start gap-2">
                  <span className="text-muted-foreground mt-0.5 text-xs">→</span>
                  {obs}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </SectionCard>
  )
}
