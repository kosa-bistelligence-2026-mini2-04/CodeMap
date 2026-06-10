import { useMouseDragScroll } from '@/common/hooks/use-mouse-drag-scroll'
import { SECTION_ICONS } from '@/common/components/section-icons'
import {
  PRODUCT_SECTIONS,
  SECTION_META,
  SECTION_ORDER,
  TECHNICAL_SECTIONS,
} from '@/common/constants/analysis-sections'
import type { AnalysisResult, AnalysisSectionType } from '@repo/shared'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@repo/ui/components/tabs'
import { motion } from 'motion/react'
import { Check, ChevronLeft, ChevronRight, Loader2, MessageSquare } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useUnreadSections } from '../hooks/use-unread-sections'
import type { ViewMode } from '../hooks/use-view-mode'
import { AnalysisProgressSection } from './analysis-progress-section'
import { AnalysisQuestions } from './analysis-questions'
import { ArchitectureSection } from './architecture-section'
import { CodeMetricsSection } from './code-metrics-section'
import { DependenciesSection } from './dependencies-section'
import { ExecutiveSummarySectionView as ExecutiveSummarySection } from './executive-summary-section'
import { FunFactsSection } from './fun-facts-section'
import { RecommendationsSection } from './recommendations-section'
import { SecuritySection } from './security-section'
import { TabSkeletonPlaceholder } from './tab-skeleton-placeholder'
import { TechStackSection } from './tech-stack-section'
import { TokenUsageCard } from './token-usage-card'
import { UpdatePlanSection } from './update-plan-section'

function getFilteredSections(viewMode: ViewMode): AnalysisSectionType[] {
  if (viewMode === 'product') return PRODUCT_SECTIONS
  if (viewMode === 'technical') return TECHNICAL_SECTIONS
  return SECTION_ORDER
}

interface SectionTabsProps {
  sections: Partial<AnalysisResult>
  isStreaming: boolean
  currentStreamingSection: string | null
  completedSections: AnalysisSectionType[]
  isDone: boolean
  analysisId: string
  viewMode: ViewMode
  inputTokens?: number | null
  outputTokens?: number | null
}

export function SectionTabs({
  sections,
  isStreaming,
  currentStreamingSection,
  completedSections,
  isDone,
  analysisId,
  viewMode,
  inputTokens,
  outputTokens,
}: SectionTabsProps) {
  const filteredOrder = getFilteredSections(viewMode)
  const availableTabs = filteredOrder.filter((s) => s in sections)
  const showQuestionsTab = isDone

  const [activeTab, setActiveTab] = useState<AnalysisSectionType | 'questions'>('executive_summary')

  const currentActiveTab = (() => {
    if (activeTab === 'questions') return 'questions'
    if (availableTabs.includes(activeTab as AnalysisSectionType))
      return activeTab as AnalysisSectionType
    return availableTabs[0] ?? 'executive_summary'
  })()

  const tabsListRef = useMouseDragScroll<HTMLDivElement>()
  const triggerRefs = useRef<Record<string, HTMLButtonElement | null>>({})
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)

  const unread = useUnreadSections(completedSections, currentActiveTab as AnalysisSectionType)

  const updateScrollState = useCallback(() => {
    const el = tabsListRef.current
    if (!el) return
    setCanScrollLeft(el.scrollLeft > 4)
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 4)
  }, [tabsListRef])

  const scrollBy = useCallback(
    (direction: 'left' | 'right') => {
      const el = tabsListRef.current
      if (!el) return
      el.scrollBy({ left: direction === 'left' ? -160 : 160, behavior: 'smooth' })
    },
    [tabsListRef],
  )

  const scrollTabIntoView = useCallback(
    (section: string) => {
      const container = tabsListRef.current
      const el = triggerRefs.current[section]
      if (!container || !el) return
      const containerRect = container.getBoundingClientRect()
      const elRect = el.getBoundingClientRect()
      const elCenter = elRect.left + elRect.width / 2 - containerRect.left
      const targetScroll = container.scrollLeft + elCenter - containerRect.width / 2
      container.scrollTo({ left: targetScroll, behavior: 'smooth' })
    },
    [tabsListRef],
  )

  useEffect(() => {
    const el = tabsListRef.current
    if (!el) return
    el.addEventListener('scroll', updateScrollState, { passive: true })
    const observer = new ResizeObserver(updateScrollState)
    observer.observe(el)
    updateScrollState()
    return () => {
      el.removeEventListener('scroll', updateScrollState)
      observer.disconnect()
    }
  }, [updateScrollState, tabsListRef])

  useEffect(() => {
    scrollTabIntoView(currentActiveTab)
  }, [currentActiveTab, scrollTabIntoView])

  if (availableTabs.length === 0 && !showQuestionsTab) return null

  const isFirstTabActive = currentActiveTab === 'executive_summary'
  const showTokenUsage = isDone && inputTokens != null && outputTokens != null

  return (
    <Tabs
      value={currentActiveTab}
      onValueChange={(v) => {
        setActiveTab(v as AnalysisSectionType | 'questions')
        scrollTabIntoView(v)
      }}
    >
      <div className="relative flex items-center">
        {canScrollLeft && (
          <button
            type="button"
            onClick={() => scrollBy('left')}
            className="absolute -left-4 z-10 flex items-center justify-center w-10 h-full bg-linear-to-r from-background via-background/80 to-transparent text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            <ChevronLeft className="size-5 shrink-0" />
          </button>
        )}
        {canScrollRight && (
          <button
            type="button"
            onClick={() => scrollBy('right')}
            className="absolute -right-4 z-10 flex items-center justify-center w-10 h-full bg-linear-to-l from-background via-background/80 to-transparent text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
          >
            <ChevronRight className="size-5 shrink-0" />
          </button>
        )}
        <div
          ref={tabsListRef}
          className="overflow-x-auto overflow-y-hidden mask-[linear-gradient(to_right,transparent,black_24px,black_calc(100%-24px),transparent)] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          <TabsList className="inline-flex! h-auto p-1 gap-0.5 rounded-xl bg-muted w-max">
            {SECTION_ORDER.map((section) => {
              const available = availableTabs.includes(section)
              const meta = SECTION_META[section]
              const isActiveStreaming = isStreaming && currentStreamingSection === section
              const isUnread = unread.has(section)
              const isHiddenByFilter = !filteredOrder.includes(section)

              if (isHiddenByFilter) return null

              return (
                <TabsTrigger
                  key={section}
                  value={section}
                  disabled={!available}
                  ref={(el) => {
                    triggerRefs.current[section] = el
                  }}
                  className="relative flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg h-auto disabled:opacity-30 cursor-pointer data-[state=active]:cursor-default whitespace-nowrap"
                >
                  <span className="[&_svg]:w-3.5 [&_svg]:h-3.5 shrink-0">
                    {SECTION_ICONS[section]}
                  </span>
                  <span>{meta.label}</span>
                  {available && !isActiveStreaming && !isUnread && (
                    <span className="flex items-center justify-center w-3.5 h-3.5 rounded-full bg-primary/15 shrink-0">
                      <Check className="size-3.5 text-primary" strokeWidth={2} />
                    </span>
                  )}
                  {isUnread && (
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0" />
                  )}
                  {isActiveStreaming && (
                    <Loader2 className="w-3 h-3 animate-spin text-primary shrink-0" />
                  )}
                </TabsTrigger>
              )
            })}

            {showQuestionsTab && (
              <TabsTrigger
                value="questions"
                ref={(el) => {
                  triggerRefs.current.questions = el
                }}
                className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg h-auto cursor-pointer data-[state=active]:cursor-default whitespace-nowrap"
              >
                <MessageSquare className="w-3.5 h-3.5" aria-hidden="true" />
                <span>Ask</span>
              </TabsTrigger>
            )}
          </TabsList>
        </div>
      </div>

      <div className="mt-4 space-y-4">
        {showTokenUsage && inputTokens != null && outputTokens != null && (
          <TokenUsageCard inputTokens={inputTokens} outputTokens={outputTokens} />
        )}

        <TabsContent value="analysis_progress">
          <motion.div
            key="analysis_progress"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
          >
            {sections.analysis_progress && (
              <AnalysisProgressSection
                data={sections.analysis_progress}
                isStreaming={isStreaming && !sections.executive_summary}
              />
            )}
          </motion.div>
        </TabsContent>
        <TabsContent value="executive_summary">
          <motion.div
            key="executive_summary"
            initial={{ opacity: 0, y: 8 }}
            animate={currentActiveTab === 'executive_summary' ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.18 }}
          >
            {sections.executive_summary ? (
              <ExecutiveSummarySection
                data={sections.executive_summary}
                isStreaming={isStreaming && !sections.tech_stack}
              />
            ) : (
              isFirstTabActive && isStreaming && <TabSkeletonPlaceholder />
            )}
          </motion.div>
        </TabsContent>
        <TabsContent value="tech_stack">
          <motion.div
            key="tech_stack"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
          >
            {sections.tech_stack && (
              <TechStackSection
                data={sections.tech_stack}
                isStreaming={isStreaming && !sections.architecture}
              />
            )}
          </motion.div>
        </TabsContent>
        <TabsContent value="architecture">
          <motion.div
            key="architecture"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
          >
            {sections.architecture && (
              <ArchitectureSection
                data={sections.architecture}
                isStreaming={isStreaming && !sections.security}
              />
            )}
          </motion.div>
        </TabsContent>
        <TabsContent value="security">
          <motion.div
            key="security"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
          >
            {sections.security && (
              <SecuritySection
                data={sections.security}
                isStreaming={isStreaming && !sections.dependencies}
              />
            )}
          </motion.div>
        </TabsContent>
        <TabsContent value="dependencies">
          <motion.div
            key="dependencies"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
          >
            {sections.dependencies && (
              <DependenciesSection
                data={sections.dependencies}
                isStreaming={isStreaming && !sections.update_plan}
              />
            )}
          </motion.div>
        </TabsContent>
        <TabsContent value="update_plan">
          <motion.div
            key="update_plan"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
          >
            {sections.update_plan && (
              <UpdatePlanSection
                data={sections.update_plan}
                isStreaming={isStreaming && !sections.recommendations}
              />
            )}
          </motion.div>
        </TabsContent>
        <TabsContent value="recommendations">
          <motion.div
            key="recommendations"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
          >
            {sections.recommendations && <RecommendationsSection data={sections.recommendations} />}
          </motion.div>
        </TabsContent>
        <TabsContent value="code_metrics">
          <motion.div
            key="code_metrics"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
          >
            {sections.code_metrics && (
              <CodeMetricsSection
                data={sections.code_metrics}
                isStreaming={isStreaming && !sections.fun_facts}
              />
            )}
          </motion.div>
        </TabsContent>
        <TabsContent value="fun_facts">
          <motion.div
            key="fun_facts"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.18 }}
          >
            {sections.fun_facts && <FunFactsSection data={sections.fun_facts} />}
          </motion.div>
        </TabsContent>
        <TabsContent value="questions">
          <AnalysisQuestions analysisId={analysisId} />
        </TabsContent>
      </div>
    </Tabs>
  )
}
