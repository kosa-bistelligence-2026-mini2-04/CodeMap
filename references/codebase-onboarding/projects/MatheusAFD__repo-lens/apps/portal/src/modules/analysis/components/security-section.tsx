import { HealthGradeBadge } from '@/common/components/health-grade-badge'
import { SECTION_ICONS } from '@/common/components/section-icons'
import { SECTION_META } from '@/common/constants/analysis-sections'
import type {
  SecurityGrade,
  SecuritySection as SecuritySectionData,
  SeverityLevel,
} from '@repo/shared'
import { Badge } from '@repo/ui/components/badge'
import { cn } from '@repo/ui/lib/utils'
import { SectionCard } from './section-card'

interface SecuritySectionProps {
  data: SecuritySectionData
  isStreaming?: boolean
}

const SEVERITY_STYLES: Record<SeverityLevel, string> = {
  critical: 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/30',
  high: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-400 border-yellow-500/30',
  low: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/30',
}

const GRADE_THRESHOLDS: Record<SecurityGrade, number> = {
  A: 90,
  B: 75,
  C: 60,
  D: 40,
  F: 0,
}

const NEXT_GRADE: Partial<Record<SecurityGrade, SecurityGrade>> = {
  F: 'D',
  D: 'C',
  C: 'B',
  B: 'A',
}

function getPointsToNextGrade(
  score: number,
  grade: SecurityGrade,
): { points: number; next: SecurityGrade } | null {
  const next = NEXT_GRADE[grade]
  if (!next) return null
  return { points: GRADE_THRESHOLDS[next] - score, next }
}

export function SecuritySection({ data, isStreaming }: SecuritySectionProps) {
  const meta = SECTION_META.security
  const nextGradeInfo = getPointsToNextGrade(data.score, data.grade)

  return (
    <SectionCard
      icon={SECTION_ICONS.security}
      title={meta.label}
      description={meta.description}
      data={data}
      isStreaming={isStreaming}
    >
      <div className="space-y-5">
        <div className="flex items-center gap-4">
          <HealthGradeBadge grade={data.grade} size="lg" />
          <div>
            <p className="text-2xl font-bold tabular-nums">
              {data.score}
              <span className="text-sm font-normal text-muted-foreground">/100</span>
            </p>
            {nextGradeInfo && nextGradeInfo.points > 0 ? (
              <p className="text-xs text-muted-foreground">
                +{nextGradeInfo.points} pts para nota {nextGradeInfo.next}
              </p>
            ) : (
              <p className="text-xs text-muted-foreground">Security score</p>
            )}
          </div>
        </div>

        {data.findings.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Findings
            </p>
            <div className="space-y-2">
              {data.findings.map((finding) => (
                <div
                  key={finding.description.slice(0, 40)}
                  className="flex items-start gap-3 p-3 rounded-lg border border-border/60"
                >
                  <Badge
                    variant="outline"
                    className={cn('text-[10px] shrink-0 mt-0.5', SEVERITY_STYLES[finding.severity])}
                  >
                    {finding.severity}
                  </Badge>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm">{finding.description}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{finding.owasp}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.positives.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              What's good
            </p>
            <ul className="space-y-1">
              {data.positives.map((pos) => (
                <li key={pos} className="text-sm flex items-start gap-2">
                  <span className="text-green-500 mt-0.5">✓</span>
                  {pos}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </SectionCard>
  )
}
