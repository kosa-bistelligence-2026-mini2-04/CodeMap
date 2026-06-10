import { useMouseDragScroll } from '@/common/hooks/use-mouse-drag-scroll'
import { SECTION_ICONS } from '@/common/components/section-icons'
import { SECTION_META, SECTION_ORDER } from '@/common/constants/analysis-sections'
import type { AnalysisSectionType } from '@repo/shared'
import { cn } from '@repo/ui/lib/utils'

interface AnalysisProgressProps {
  completedSections: AnalysisSectionType[]
  currentMessage: string | null
}

export function AnalysisProgress({ completedSections, currentMessage }: AnalysisProgressProps) {
  const completedSet = new Set(completedSections)
  const containerRef = useMouseDragScroll<HTMLDivElement>()

  const scrollActiveIntoView = (el: HTMLDivElement | null) => {
    const container = containerRef.current
    if (!container || !el) return
    const containerRect = container.getBoundingClientRect()
    const elRect = el.getBoundingClientRect()
    const elCenter = elRect.left + elRect.width / 2 - containerRect.left
    container.scrollTo({
      left: container.scrollLeft + elCenter - containerRect.width / 2,
      behavior: 'smooth',
    })
  }

  return (
    <div className="space-y-3">
      <div
        ref={containerRef}
        className="flex items-center gap-1 overflow-x-auto overflow-y-hidden mask-[linear-gradient(to_right,transparent,black_24px,black_calc(100%-24px),transparent)] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {SECTION_ORDER.map((section, sectionIndex) => {
          const done = completedSet.has(section)
          const active = !done && completedSections.length === sectionIndex

          return (
            <div key={section} className="flex items-center gap-1 shrink-0">
              <div
                ref={active ? scrollActiveIntoView : undefined}
                className={cn(
                  'flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-[10px] font-medium transition-all duration-300',
                  done && 'bg-primary/10 text-primary',
                  active && 'bg-muted text-foreground animate-pulse',
                  !done && !active && 'bg-muted/40 text-muted-foreground',
                )}
              >
                <span
                  className={cn(
                    '[&_svg]:w-3 [&_svg]:h-3',
                    done && '[&_svg]:stroke-primary',
                    active && '[&_svg]:stroke-foreground',
                    !done && !active && '[&_svg]:stroke-muted-foreground',
                  )}
                >
                  {SECTION_ICONS[section]}
                </span>
                <span className="hidden sm:inline">{SECTION_META[section].label}</span>
              </div>
              {sectionIndex < SECTION_ORDER.length - 1 && (
                <div className={cn('w-3 h-px shrink-0', done ? 'bg-primary/40' : 'bg-border')} />
              )}
            </div>
          )
        })}
      </div>

      {currentMessage && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <div className="flex gap-1">
            {[0, 1, 2].map((dotIndex) => (
              <span
                key={dotIndex}
                className="w-1 h-1 rounded-full bg-muted-foreground animate-bounce"
                style={{ animationDelay: `${dotIndex * 150}ms` }}
              />
            ))}
          </div>
          {currentMessage}
        </div>
      )}
    </div>
  )
}
