import { SECTION_ICONS } from '@/common/components/section-icons'
import { SECTION_META } from '@/common/constants/analysis-sections'
import type { CodeMetricsSection as CodeMetricsSectionData } from '@repo/shared'
import { SectionCard } from './section-card'

interface CodeMetricsSectionProps {
  data: CodeMetricsSectionData
  isStreaming?: boolean
}

export function CodeMetricsSection({ data, isStreaming }: CodeMetricsSectionProps) {
  const meta = SECTION_META.code_metrics

  return (
    <SectionCard
      icon={SECTION_ICONS.code_metrics}
      title={meta.label}
      description={meta.description}
      data={data}
      isStreaming={isStreaming}
    >
      <div className="space-y-5">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          <StatBox label="Total Files" value={data.totalFiles.toLocaleString()} />
          <StatBox label="Est. Lines" value={data.estimatedLines.toLocaleString()} />
        </div>

        {data.byLanguage.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              By Language
            </p>
            <div className="space-y-2">
              {data.byLanguage.map((lang) => (
                <div key={lang.name} className="space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-foreground">{lang.name}</span>
                    <span className="text-muted-foreground">
                      {lang.lines.toLocaleString()} lines ({lang.percentage}%)
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-muted overflow-hidden">
                    <div
                      className="h-full rounded-full bg-primary/70"
                      style={{ width: `${lang.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {data.largestFiles.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Largest Files
            </p>
            <div className="space-y-1">
              {data.largestFiles.map((file) => (
                <div
                  key={file.path}
                  className="flex items-center justify-between text-xs py-1 border-b border-border/30 last:border-0"
                >
                  <span className="text-foreground font-mono truncate max-w-[70%]">
                    {file.path}
                  </span>
                  <span className="text-muted-foreground shrink-0 ml-2">
                    {file.lines.toLocaleString()} lines
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </SectionCard>
  )
}

function StatBox({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-border/50 bg-muted/30 px-3 py-2.5 text-center">
      <p className="text-lg font-bold text-foreground">{value}</p>
      <p className="text-xs text-muted-foreground mt-0.5">{label}</p>
    </div>
  )
}
