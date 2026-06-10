import { ChatPage } from '@/modules/chat/components/chat-page'
import { useRepository } from '@/modules/repos/hooks/use-repos'
import { Skeleton } from '@repo/ui/components/skeleton'
import { createFileRoute } from '@tanstack/react-router'

export const Route = createFileRoute('/_authed/repos/$repoId/chat/' as never)({
  component: ChatRouteIndex,
})

function ChatRouteIndex() {
  const params = Route.useParams() as Record<string, string>
  const repoId = params.repoId as string
  const { data: repo, isLoading, error } = useRepository(repoId)

  if (isLoading) {
    return (
      <div className="flex h-screen flex-col p-6 gap-4">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="h-40 w-2/3" />
        <Skeleton className="h-24 w-1/2" />
      </div>
    )
  }

  if (error || !repo) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm text-destructive">Repository not found.</p>
      </div>
    )
  }

  return <ChatPage repo={repo} />
}
