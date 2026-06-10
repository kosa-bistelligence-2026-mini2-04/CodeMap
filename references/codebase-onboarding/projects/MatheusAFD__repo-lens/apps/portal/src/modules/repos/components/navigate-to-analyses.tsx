import { Button } from '@repo/ui/components/button'
import { useNavigate } from '@tanstack/react-router'
import { ListTree, MessageSquare } from 'lucide-react'

interface NavigateToAnalysesProps {
  repoId: string
}

export function NavigateToAnalyses({ repoId }: NavigateToAnalysesProps) {
  const navigate = useNavigate()
  return (
    <div className="flex w-full gap-2">
      <Button
        size="sm"
        className="h-8 flex-1 gap-1.5 text-xs"
        onClick={() =>
          navigate({
            to: '/repos/$repoId/chat' as never,
            params: { repoId } as never,
          })
        }
      >
        <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
        Open chat
      </Button>
      <Button
        size="sm"
        variant="outline"
        className="h-8 gap-1.5 text-xs"
        onClick={() =>
          navigate({
            to: '/repos/$repoId/analyses' as never,
            params: { repoId } as never,
          })
        }
      >
        <ListTree className="h-3.5 w-3.5" aria-hidden="true" />
        Analyses
      </Button>
    </div>
  )
}
