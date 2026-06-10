import { AppHeader } from '@/common/components/app-header'
import { HealthGradeBadge } from '@/common/components/health-grade-badge'
import { SECTION_ORDER } from '@/common/constants/analysis-sections'
import type { Repository } from '@/modules/repos/domain/repo.domain'
import type { AnalysisResult, AnalysisSectionType } from '@repo/shared'
import { Button } from '@repo/ui/components/button'
import { Skeleton } from '@repo/ui/components/skeleton'
import { Link } from '@tanstack/react-router'
import { Clock } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { useAnalysis, useStartAnalysis } from '../hooks/use-analysis'
import { useAnalysisStream } from '../hooks/use-analysis-stream'
import { useViewMode } from '../hooks/use-view-mode'
import type { StartAnalysisFormRequest } from '../schemas/start-analysis.schema'
import { AnalysisProgress } from './analysis-progress'
import { CopyAgentPromptButton } from './copy-agent-prompt-button'
import { SectionTabs } from './section-tabs'
import { StartAnalysisDialog } from './start-analysis-dialog'
import { ViewModeToggle } from './view-mode-toggle'

interface AnalysisPageProps {
  repo: Repository
  initialAnalysisId?: string
}

export function AnalysisPage({ repo, initialAnalysisId }: AnalysisPageProps) {
  const [streamingId, setStreamingId] = useState<string | null>(initialAnalysisId ?? null)
  const [isStarting, setIsStarting] = useState(false)
  const [dialogOpen, setDialogOpen] = useState(false)
  const startedInSessionRef = useRef(false)
  const { mutateAsync: startAnalysis } = useStartAnalysis(repo.id)
  const {
    data: saved,
    isLoading: savedLoading,
    refetch: refetchSaved,
  } = useAnalysis(streamingId ?? initialAnalysisId ?? null)

  const { sections: streamSections, currentSection, isDone, error } = useAnalysisStream(streamingId)
  const { viewMode, setViewMode } = useViewMode()

  const completedSections = SECTION_ORDER.filter(
    (section) => section in streamSections,
  ) as AnalysisSectionType[]
  const isStreaming = !!streamingId && !isDone && !error
  const hasStarted = !!streamingId

  const streamHasData = Object.keys(streamSections).length > 0
  const displaySections: Partial<AnalysisResult> = streamHasData
    ? streamSections
    : (saved?.result ?? {})
  const securityGrade = displaySections.security?.grade

  const allSectionsComplete = isDone && Object.keys(streamSections).length > 0

  useEffect(() => {
    if (isDone) {
      refetchSaved()
    }
  }, [isDone, refetchSaved])

  useEffect(() => {
    if (allSectionsComplete && startedInSessionRef.current) {
      toast.success('Analysis complete', {
        description: 'All sections have been analyzed successfully.',
      })
    }
  }, [allSectionsComplete])

  async function handleStartAnalysis(request: StartAnalysisFormRequest) {
    setDialogOpen(false)
    setIsStarting(true)
    try {
      const { analysisId } = await startAnalysis(request)
      startedInSessionRef.current = true
      setStreamingId(analysisId)
    } catch (startError) {
      console.error(startError)
    } finally {
      setIsStarting(false)
    }
  }

  const hasSaved = !!saved?.result && Object.keys(saved.result).length > 0
  const showReanalyzeButton = (isDone || !!error || (!isStreaming && hasSaved)) && !isStarting
  const showLoading = savedLoading && !streamHasData
  const showSections = !savedLoading || streamHasData

  return (
    <div className="min-h-screen bg-background">
      <AppHeader />

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Link
              to="/dashboard"
              className="hover:text-foreground transition-colors cursor-pointer"
            >
              Repositories
            </Link>
            <span>/</span>
            <Link
              to={'/repos/$repoId/chat' as never}
              params={{ repoId: repo.id } as never}
              className="hover:text-foreground transition-colors cursor-pointer"
            >
              {repo.fullName}
            </Link>
            <span>/</span>
            <Link
              to={'/repos/$repoId/analyses' as never}
              params={{ repoId: repo.id } as never}
              className="hover:text-foreground transition-colors cursor-pointer"
            >
              Analyses
            </Link>
            <span>/</span>
            <span>Detail</span>
          </div>
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold truncate">{repo.name}</h1>
                {securityGrade && (
                  <>
                    <HealthGradeBadge grade={securityGrade} size="sm" />
                    {displaySections.security?.score != null && (
                      <span className="text-xs text-muted-foreground tabular-nums">
                        {displaySections.security.score}/100
                      </span>
                    )}
                  </>
                )}
                {isStreaming && (
                  <span className="flex items-center gap-1 shrink-0">
                    {[0, 1, 2].map((i) => (
                      <span
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce"
                        style={{ animationDelay: `${i * 150}ms` }}
                      />
                    ))}
                  </span>
                )}
              </div>
              <p className="text-sm text-muted-foreground mt-0.5">{repo.owner}</p>
            </div>
            <div className="flex items-center gap-2 shrink-0 flex-wrap justify-end">
              {(hasSaved || streamHasData) && !isStreaming && (
                <CopyAgentPromptButton repoFullName={repo.fullName} result={displaySections} />
              )}
              {showReanalyzeButton && (
                <Button
                  size="sm"
                  variant={isDone ? 'outline' : 'default'}
                  onClick={() => setDialogOpen(true)}
                  disabled={isStarting || savedLoading}
                  className="h-8 text-xs cursor-pointer"
                  data-testid="btn-reanalyze"
                >
                  {isStarting
                    ? 'Starting...'
                    : hasSaved || streamHasData
                      ? 'Re-analyze'
                      : 'Start Analysis'}
                </Button>
              )}
            </div>
          </div>
        </div>

        {hasSaved && !hasStarted && saved?.completedAt && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground px-1">
            <Clock className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
            <span>
              Analyzed{' '}
              {new Intl.DateTimeFormat('en', {
                dateStyle: 'medium',
                timeStyle: 'short',
              }).format(new Date(saved.completedAt))}
            </span>
          </div>
        )}

        {showLoading && (
          <div className="rounded-xl border border-border bg-card p-5 space-y-3">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-3 w-full" />
            <Skeleton className="h-3 w-4/5" />
          </div>
        )}

        {isStreaming && (
          <div className="rounded-xl border border-border bg-card p-4">
            <AnalysisProgress
              completedSections={completedSections}
              currentMessage={currentSection}
            />
          </div>
        )}

        {error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        {showSections && (
          <div className="space-y-3">
            {(hasSaved || streamHasData) && (
              <div className="flex justify-end">
                <ViewModeToggle value={viewMode} onChange={setViewMode} />
              </div>
            )}
            <SectionTabs
              sections={displaySections}
              isStreaming={isStreaming}
              currentStreamingSection={currentSection}
              completedSections={completedSections}
              isDone={isDone}
              analysisId={streamingId ?? initialAnalysisId ?? ''}
              viewMode={viewMode}
              inputTokens={saved?.inputTokens}
              outputTokens={saved?.outputTokens}
            />
          </div>
        )}
      </main>

      <StartAnalysisDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onConfirm={handleStartAnalysis}
        isStarting={isStarting}
      />
    </div>
  )
}
