import { LANGUAGE_COLORS } from '@/common/constants/language-colors'
import { formatDate } from '@/common/utils/format'
import { Badge } from '@repo/ui/components/badge'
import { Card, CardContent } from '@repo/ui/components/card'
import { cn } from '@repo/ui/lib/utils'
import { GitFork } from 'lucide-react'
import type { Repository } from '../domain/repo.domain'
import { NavigateToAnalyses } from './navigate-to-analyses'

interface RepoCardProps {
  repo: Repository
}

export function RepoCard({ repo }: RepoCardProps) {
  const langColor = repo.language
    ? (LANGUAGE_COLORS[repo.language] ?? 'bg-muted text-muted-foreground')
    : undefined

  return (
    <Card
      data-testid="repo-card"
      data-repo-name={repo.name}
      className="group border-border/60 hover:border-border transition-all duration-200 hover:shadow-sm bg-card"
    >
      <CardContent className="p-5 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5 mb-1">
              <GitFork className="w-3.5 h-3.5 text-muted-foreground shrink-0" aria-hidden="true" />
              <span className="text-xs text-muted-foreground truncate">{repo.owner}</span>
              {repo.isPrivate && (
                <span className="text-[10px] px-1 py-0.5 rounded border border-border/60 text-muted-foreground">
                  private
                </span>
              )}
            </div>
            <h3 className="font-semibold text-sm text-foreground truncate">{repo.name}</h3>
          </div>
        </div>

        {repo.description && (
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {repo.description}
          </p>
        )}

        <div className="flex items-center gap-2 flex-wrap">
          {repo.language && (
            <Badge
              variant="secondary"
              className={cn('text-[11px] px-2 py-0.5 border-0', langColor)}
            >
              {repo.language}
            </Badge>
          )}
          {repo.lastAnalyzedAt && (
            <span className="text-[11px] text-muted-foreground">
              Last analyzed {formatDate(repo.lastAnalyzedAt)}
            </span>
          )}
          {!repo.hasAnalysis && (
            <span className="text-[11px] text-muted-foreground">Never analyzed</span>
          )}
        </div>

        <NavigateToAnalyses repoId={repo.id} />
      </CardContent>
    </Card>
  )
}
