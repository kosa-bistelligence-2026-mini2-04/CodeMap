import { Button } from '@repo/ui/components/button'
import { Skeleton } from '@repo/ui/components/skeleton'
import { GitFork, Plus } from 'lucide-react'
import { useState } from 'react'
import { useRepositories } from '../hooks/use-repos'
import { AddRepoDialog } from './add-repo-dialog'
import { RepoCard } from './repo-card'

export function RepoList() {
  const { data: repos, isLoading, refetch } = useRepositories()
  const [dialogOpen, setDialogOpen] = useState(false)

  const repoCountText = repos
    ? `${repos.length} repositor${repos.length === 1 ? 'y' : 'ies'}`
    : 'No repositories yet'

  const hasRepos = !isLoading && !!repos && repos.length > 0
  const showEmpty = !isLoading && repos?.length === 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Repositories</h2>
          <p className="text-sm text-muted-foreground">{repoCountText}</p>
        </div>
        <Button size="sm" onClick={() => setDialogOpen(true)} className="gap-2 h-8 text-xs">
          <Plus className="w-3.5 h-3.5" aria-hidden="true" />
          Add repository
        </Button>
      </div>

      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((skeletonKey) => (
            <Skeleton key={skeletonKey} className="h-44 rounded-xl" />
          ))}
        </div>
      )}

      {hasRepos && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {repos.map((repo) => (
            <RepoCard key={repo.id} repo={repo} />
          ))}
        </div>
      )}

      {showEmpty && (
        <div className="flex flex-col items-center justify-center py-20 text-center gap-4">
          <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center">
            <GitFork className="w-6 h-6 text-muted-foreground" aria-hidden="true" />
          </div>
          <div>
            <p className="font-medium text-sm">No repositories yet</p>
            <p className="text-sm text-muted-foreground mt-1">
              Add your first repository to get started.
            </p>
          </div>
          <Button size="sm" onClick={() => setDialogOpen(true)} className="gap-2 h-8 text-xs">
            <Plus className="w-3.5 h-3.5" aria-hidden="true" />
            Add repository
          </Button>
        </div>
      )}

      <AddRepoDialog open={dialogOpen} onOpenChange={setDialogOpen} onAdded={() => refetch()} />
    </div>
  )
}
