import { SECTION_ICONS } from '@/common/components/section-icons'
import { SECTION_META } from '@/common/constants/analysis-sections'
import type { UpdateItem, UpdatePlanSection as UpdatePlanSectionData } from '@repo/shared'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@repo/ui/components/accordion'
import { Badge } from '@repo/ui/components/badge'
import { SectionCard } from './section-card'

interface UpdatePlanSectionProps {
  data: UpdatePlanSectionData
  isStreaming?: boolean
}

function CriticalDotIcon() {
  return (
    <span className="inline-block w-2 h-2 rounded-full bg-red-500 shrink-0" aria-hidden="true" />
  )
}

function MajorDotIcon() {
  return (
    <span className="inline-block w-2 h-2 rounded-full bg-yellow-500 shrink-0" aria-hidden="true" />
  )
}

function MinorDotIcon() {
  return (
    <span className="inline-block w-2 h-2 rounded-full bg-green-500 shrink-0" aria-hidden="true" />
  )
}

function UpdateList({ items }: { items: UpdateItem[] }) {
  if (!items.length)
    return <p className="text-sm text-muted-foreground py-2">No updates in this category.</p>
  return (
    <div className="space-y-2">
      {items.map((item) => (
        <div key={item.name} className="p-3 rounded-lg border border-border/60 space-y-2">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-mono font-medium">{item.name}</span>
            <span className="text-xs text-muted-foreground">
              {item.current} → {item.target}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">{item.reason}</p>
          <div className="flex items-start gap-1.5">
            <span className="text-xs text-green-600 dark:text-green-400 font-medium shrink-0">
              Gain:
            </span>
            <span className="text-xs">{item.gain}</span>
          </div>
        </div>
      ))}
    </div>
  )
}

export function UpdatePlanSection({ data, isStreaming }: UpdatePlanSectionProps) {
  const meta = SECTION_META.update_plan
  const totalCritical = data.critical.length
  const totalMajor = data.major.length
  const totalMinor = data.minor.length

  return (
    <SectionCard
      icon={SECTION_ICONS.update_plan}
      title={meta.label}
      description={meta.description}
      data={data}
      isStreaming={isStreaming}
    >
      <Accordion
        type="multiple"
        defaultValue={totalCritical > 0 ? ['critical'] : ['major']}
        className="space-y-2"
      >
        <AccordionItem value="critical" className="border border-border/60 rounded-lg px-3">
          <AccordionTrigger className="py-3 text-sm hover:no-underline cursor-pointer">
            <div className="flex items-center gap-2">
              <CriticalDotIcon />
              <span>Critical</span>
              {totalCritical > 0 && (
                <Badge variant="destructive" className="h-4 text-[10px] px-1.5">
                  {totalCritical}
                </Badge>
              )}
            </div>
          </AccordionTrigger>
          <AccordionContent className="pb-3">
            <UpdateList items={data.critical} />
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="major" className="border border-border/60 rounded-lg px-3">
          <AccordionTrigger className="py-3 text-sm hover:no-underline cursor-pointer">
            <div className="flex items-center gap-2">
              <MajorDotIcon />
              <span>Major</span>
              {totalMajor > 0 && (
                <Badge variant="secondary" className="h-4 text-[10px] px-1.5">
                  {totalMajor}
                </Badge>
              )}
            </div>
          </AccordionTrigger>
          <AccordionContent className="pb-3">
            <UpdateList items={data.major} />
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="minor" className="border border-border/60 rounded-lg px-3">
          <AccordionTrigger className="py-3 text-sm hover:no-underline cursor-pointer">
            <div className="flex items-center gap-2">
              <MinorDotIcon />
              <span>Minor</span>
              {totalMinor > 0 && (
                <Badge variant="secondary" className="h-4 text-[10px] px-1.5">
                  {totalMinor}
                </Badge>
              )}
            </div>
          </AccordionTrigger>
          <AccordionContent className="pb-3">
            <UpdateList items={data.minor} />
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </SectionCard>
  )
}
