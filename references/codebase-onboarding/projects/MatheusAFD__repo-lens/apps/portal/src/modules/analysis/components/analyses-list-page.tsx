import { AppHeader } from '@/common/components/app-header'
import { HealthGradeBadge } from '@/common/components/health-grade-badge'
import { useStartAnalysis } from '@/modules/analysis/hooks/use-analysis'
import type { Repository } from '@/modules/repos/domain/repo.domain'
import { useRepoAnalyses } from '@/modules/repos/hooks/use-repos'
import type { SecurityGrade } from '@repo/shared'
import { Button } from '@repo/ui/components/button'
import { Skeleton } from '@repo/ui/components/skeleton'
import { Link, useNavigate } from '@tanstack/react-router'
import { formatDate } from '@/common/utils/format'
import { ChevronRight, Search } from 'lucide-react'
import { useState } from 'react'

interface AnalysesListPageProps {
  repo: Repository
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    completed: 'bg-green-500/15 text-green-600 dark:text-green-400',
    running: 'bg-blue-500/15 text-blue-600 dark:text-blue-400',
    failed: 'bg-red-500/15 text-red-600 dark:text-red-400',
  }
  const style = styles[status] ?? 'bg-muted text-muted-foreground'
  return (
    <span className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${style}`}>{status}</span>
  )
}

export function AnalysesListPage({ repo }: AnalysesListPageProps) {
  const navigate = useNavigate()
  const { data: analyses, isLoading } = useRepoAnalyses(repo.id)
  const { mutateAsync: startAnalysis } = useStartAnalysis(repo.id)
  const [isStarting, setIsStarting] = useState(false)
  const [startError, setStartError] = useState<string | null>(null)

  async function handleNewAnalysis() {
    setIsStarting(true)
    setStartError(null)
    try {
      const { analysisId } = await startAnalysis(undefined)
      navigate({
        to: '/repos/$repoId/analyses/$analysisId' as never,
        params: { repoId: repo.id, analysisId } as never,
      })
    } catch (err) {
      setStartError(err instanceof Error ? err.message : 'Failed to start analysis')
    } finally {
      setIsStarting(false)
    }
  }

  const hasAnalyses = analyses && analyses.length > 0
  const showEmpty = !isLoading && !hasAnalyses

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
            <span>{repo.fullName}</span>
          </div>
          <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
              <h1 className="text-xl font-bold truncate">{repo.name}</h1>
              <p className="text-sm text-muted-foreground mt-0.5">{repo.owner}</p>
            </div>
            <Button
              size="sm"
              onClick={handleNewAnalysis}
              disabled={isStarting}
              className="h-8 text-xs shrink-0 cursor-pointer"
            >
              {isStarting ? 'Starting...' : 'New Analysis'}
            </Button>
          </div>
        </div>

        {isLoading && (
          <div className="space-y-3">
            {[1, 2, 3].map((k) => (
              <Skeleton key={k} className="h-16 rounded-xl" />
            ))}
          </div>
        )}

        {startError && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-600 dark:text-red-400">
            {startError}
          </div>
        )}

        {showEmpty && (
          <div className="rounded-xl border border-dashed border-border p-16 text-center space-y-3">
            <div className="flex justify-center">
              <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center">
                <Search className="w-5 h-5 text-muted-foreground" aria-hidden="true" />
              </div>
            </div>
            <p className="text-sm font-medium">No analyses yet</p>
            <p className="text-xs text-muted-foreground max-w-sm mx-auto">
              Click &ldquo;New Analysis&rdquo; to analyze this repository with Claude.
            </p>
          </div>
        )}

        {hasAnalyses && (
          <div className="space-y-2">
            {analyses.map((analysis) => {
              const { securityGrade } = analysis
              return (
                <Link
                  key={analysis.id}
                  to={'/repos/$repoId/analyses/$analysisId' as never}
                  params={{ repoId: repo.id, analysisId: analysis.id } as never}
                  className="flex items-center justify-between gap-4 p-4 rounded-xl border border-border/60 bg-card hover:border-border hover:shadow-sm transition-all duration-200 cursor-pointer"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {securityGrade ? (
                      <HealthGradeBadge grade={securityGrade as SecurityGrade} size="sm" />
                    ) : (
                      <div className="h-5 w-5 rounded border border-border/60 bg-muted shrink-0" />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground">
                        {analysis.completedAt
                          ? formatDate(analysis.completedAt)
                          : formatDate(analysis.createdAt)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {analysis.inputTokens && analysis.outputTokens
                          ? `${(analysis.inputTokens + analysis.outputTokens).toLocaleString()} tokens`
                          : 'In progress'}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <StatusBadge status={analysis.status} />
                    <ChevronRight className="w-4 h-4 text-muted-foreground" aria-hidden="true" />
                  </div>
                </Link>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}
