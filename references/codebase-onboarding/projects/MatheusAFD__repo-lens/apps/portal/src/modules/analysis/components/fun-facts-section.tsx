import { SECTION_ICONS } from '@/common/components/section-icons'
import { SECTION_META } from '@/common/constants/analysis-sections'
import type { FunFactsSection as FunFactsSectionData } from '@repo/shared'
import { Badge } from '@repo/ui/components/badge'
import { SectionCard } from './section-card'

interface FunFactsSectionProps {
  data: FunFactsSectionData
  isStreaming?: boolean
}

export function FunFactsSection({ data, isStreaming }: FunFactsSectionProps) {
  const meta = SECTION_META.fun_facts

  return (
    <SectionCard
      icon={SECTION_ICONS.fun_facts}
      title={meta.label}
      description={meta.description}
      data={data}
      isStreaming={isStreaming}
    >
      <div className="space-y-4">
        {data.codeAge && (
          <div className="flex items-center gap-2">
            <Badge variant="secondary" className="text-xs">
              {data.codeAge}
            </Badge>
          </div>
        )}

        <ul className="space-y-3">
          {data.facts.map((fact, index) => (
            <li
              key={`fact-${
                // biome-ignore lint/suspicious/noArrayIndexKey: <explanation>
                index
              }`}
              className="flex items-start gap-3 text-sm text-foreground/90"
            >
              <span className="shrink-0 mt-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-semibold">
                {index + 1}
              </span>
              <span>{fact}</span>
            </li>
          ))}
        </ul>
      </div>
    </SectionCard>
  )
}
