import { AppHeader } from '@/common/components/app-header'
import { AnalysisPage } from '@/modules/analysis/components/analysis-page'
import { useRepository } from '@/modules/repos/hooks/use-repos'
import { Skeleton } from '@repo/ui/components/skeleton'
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_authed/analyze/$repoId' as never)({
  component: AnalyzeRepoPage,
})

function AnalyzeRepoPage() {
  const params = Route.useParams() as Record<string, string>
  const repoId = params.repoId as string
  const { data: repo, isLoading, error } = useRepository(repoId)

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background">
        <AppHeader />
        <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-40 rounded-xl" />
        </main>
      </div>
    )
  }

  if (error || !repo) {
    return (
      <div className="min-h-screen bg-background">
        <AppHeader />
        <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
          <p className="text-sm text-destructive">Repository not found.</p>
        </main>
      </div>
    )
  }

  return <AnalysisPage repo={repo} />
}
