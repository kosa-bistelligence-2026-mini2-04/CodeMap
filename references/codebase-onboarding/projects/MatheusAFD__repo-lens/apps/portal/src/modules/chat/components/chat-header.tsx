import type { Repository } from '@/modules/repos/domain/repo.domain'
import { cn } from '@repo/ui/lib/utils'
import { Link, useRouterState } from '@tanstack/react-router'
import { ListTree, MessageSquare } from 'lucide-react'
import type { ReactNode } from 'react'

interface ChatHeaderProps {
  repo: Repository
  mobileTrigger?: ReactNode
}

export function ChatHeader({ repo, mobileTrigger }: ChatHeaderProps) {
  const { location } = useRouterState()
  const onChat = location.pathname.includes('/chat')
  const onAnalyses =
    location.pathname.includes('/analyses') || location.pathname.includes('/analyze')

  return (
    <div className="border-b border-border bg-background/80 backdrop-blur-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5">
        <div className="flex items-center gap-2 min-w-0">
          {mobileTrigger}
          <Link to="/dashboard" className="text-xs text-muted-foreground hover:text-foreground">
            Repos
          </Link>
          <span className="text-xs text-muted-foreground">/</span>
          <span className="truncate text-xs font-medium">{repo.fullName}</span>
        </div>
        <div className="flex items-center gap-1">
          <Link
            to={'/repos/$repoId/chat' as never}
            params={{ repoId: repo.id } as never}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs',
              onChat
                ? 'bg-muted text-foreground'
                : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground',
            )}
          >
            <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
            Chat
          </Link>
          <Link
            to={'/repos/$repoId/analyses' as never}
            params={{ repoId: repo.id } as never}
            className={cn(
              'inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs',
              onAnalyses
                ? 'bg-muted text-foreground'
                : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground',
            )}
          >
            <ListTree className="h-3.5 w-3.5" aria-hidden="true" />
            Technical view
          </Link>
        </div>
      </div>
    </div>
  )
}
