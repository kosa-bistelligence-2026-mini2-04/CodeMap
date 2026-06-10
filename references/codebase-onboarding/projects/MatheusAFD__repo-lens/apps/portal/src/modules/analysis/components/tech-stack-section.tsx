import { SECTION_ICONS } from '@/common/components/section-icons'
import { SECTION_META } from '@/common/constants/analysis-sections'
import type { TechStackSection as TechStackSectionData } from '@repo/shared'
import { Badge } from '@repo/ui/components/badge'
import { SectionCard } from './section-card'

interface TechStackSectionProps {
  data: TechStackSectionData
  isStreaming?: boolean
}

const CATEGORY_COLORS: Record<string, string> = {
  frameworks: 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20',
  databases: 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20',
  cloud: 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20',
  testing: 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20',
}

export function TechStackSection({ data, isStreaming }: TechStackSectionProps) {
  const meta = SECTION_META.tech_stack
  return (
    <SectionCard
      icon={SECTION_ICONS.tech_stack}
      title={meta.label}
      description={meta.description}
      data={data}
      isStreaming={isStreaming}
    >
      <div className="space-y-4">
        {data.languages.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Languages
            </p>
            <div className="flex flex-wrap gap-2">
              {data.languages.map((lang) => (
                <div key={lang.name} className="flex items-center gap-1.5">
                  <div
                    className="h-2 bg-primary/60 rounded-full"
                    style={{ width: `${Math.max(lang.percentage * 0.8, 8)}px` }}
                  />
                  <span className="text-sm">{lang.name}</span>
                  {lang.percentage > 0 && (
                    <span className="text-xs text-muted-foreground">{lang.percentage}%</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {Object.entries({
          frameworks: data.frameworks,
          databases: data.databases,
          cloud: data.cloud,
          testing: data.testing,
        })
          .filter(([, categoryItems]) => categoryItems.length > 0)
          .map(([key, items]) => (
            <div key={key} className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                {key}
              </p>
              <div className="flex flex-wrap gap-1.5">
                {items.map((item) => (
                  <Badge key={item} variant="outline" className={CATEGORY_COLORS[key]}>
                    {item}
                  </Badge>
                ))}
              </div>
            </div>
          ))}
      </div>
    </SectionCard>
  )
}
