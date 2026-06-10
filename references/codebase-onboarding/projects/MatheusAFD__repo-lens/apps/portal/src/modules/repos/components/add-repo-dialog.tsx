import { Badge } from '@repo/ui/components/badge'
import { Button } from '@repo/ui/components/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@repo/ui/components/dialog'
import { Skeleton } from '@repo/ui/components/skeleton'
import { useState } from 'react'
import type { GithubRepo } from '../domain/repo.domain'
import { useAddRepository, useGithubRepos } from '../hooks/use-repos'

interface AddRepoDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onAdded?: () => void
}

export function AddRepoDialog({ open, onOpenChange, onAdded }: AddRepoDialogProps) {
  const { data: githubRepos, isLoading } = useGithubRepos(open)
  const { mutateAsync: addRepo, isPending } = useAddRepository()
  const [adding, setAdding] = useState<number | null>(null)

  const showEmpty = open && !isLoading && !githubRepos?.length
  const showList = open && !isLoading && !!githubRepos?.length

  async function handleAdd(repo: GithubRepo) {
    setAdding(repo.id)
    try {
      await addRepo({
        githubRepoId: String(repo.id),
        owner: repo.owner.login,
        name: repo.name,
        fullName: repo.full_name,
        description: repo.description,
        language: repo.language,
        isPrivate: repo.private,
        htmlUrl: repo.html_url,
      })
      onOpenChange(false)
      onAdded?.()
    } finally {
      setAdding(null)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Add Repository</DialogTitle>
          <DialogDescription>
            Select a repository from your GitHub account to analyze.
          </DialogDescription>
        </DialogHeader>

        <div className="mt-2 max-h-80 overflow-y-auto space-y-1 pr-1">
          {isLoading && (
            <div className="space-y-2">
              {[1, 2, 3, 4].map((skeletonKey) => (
                <Skeleton key={skeletonKey} className="h-14 w-full rounded-lg" />
              ))}
            </div>
          )}

          {showList &&
            githubRepos.map((repo) => (
              <div
                key={repo.id}
                className="flex items-center justify-between gap-3 p-3 rounded-lg border border-border/60 hover:border-border hover:bg-muted/30 transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium truncate">{repo.full_name}</p>
                  {repo.language && (
                    <Badge variant="secondary" className="mt-1 text-[10px] px-1.5 h-4">
                      {repo.language}
                    </Badge>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-7 text-xs shrink-0"
                  disabled={adding === repo.id || isPending}
                  onClick={() => handleAdd(repo)}
                >
                  {adding === repo.id ? 'Adding…' : 'Add'}
                </Button>
              </div>
            ))}

          {showEmpty && (
            <p className="text-sm text-muted-foreground text-center py-6">No repositories found.</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
