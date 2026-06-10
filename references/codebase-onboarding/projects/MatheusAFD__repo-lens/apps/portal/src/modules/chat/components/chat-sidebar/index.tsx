import type { Repository } from '@/modules/repos/domain/repo.domain'
import { Button } from '@repo/ui/components/button'
import { ScrollArea } from '@repo/ui/components/scroll-area'
import { cn } from '@repo/ui/lib/utils'
import { Link, useNavigate } from '@tanstack/react-router'
import { ArrowLeft, ListTree, MessagesSquare, Plus } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { useChatActionState } from '../../hooks/use-chat-action-state'
import { useDeleteChat, useRenameChat } from '../../hooks/use-chat-actions'
import { useChats, useCreateChat } from '../../hooks/use-chats'
import { ChatSidebarItem } from '../chat-sidebar-item'
import { DeleteChatDialog } from '../delete-chat-dialog'
import { RenameChatDialog } from '../rename-chat-dialog'
import { SidebarSkeleton } from './sidebar-skeleton'

interface ChatSidebarProps {
  repo: Repository
  activeChatId?: string
  onNavigate?: () => void
}

export function ChatSidebar({ repo, activeChatId, onNavigate }: ChatSidebarProps) {
  const navigate = useNavigate()
  const { data: chats, isLoading } = useChats(repo.id)
  const createChat = useCreateChat(repo.id)
  const renameChat = useRenameChat(repo.id)
  const deleteChat = useDeleteChat(repo.id)
  const { renameTarget, deleteTarget, openRename, openDelete, close } = useChatActionState()
  const [isCreating, setIsCreating] = useState(false)

  async function handleCreate() {
    setIsCreating(true)
    try {
      const chat = await createChat.mutateAsync({})
      onNavigate?.()
      navigate({
        to: '/repos/$repoId/chat/$chatId' as never,
        params: { repoId: repo.id, chatId: chat.id } as never,
      })
    } catch (err) {
      toast.error((err as Error).message)
    } finally {
      setIsCreating(false)
    }
  }

  async function handleRenameSubmit(values: { title: string }) {
    if (!renameTarget) return
    await renameChat
      .mutateAsync({ chatId: renameTarget.id, body: { title: values.title } })
      .catch((err) => toast.error((err as Error).message))
    close()
  }

  async function handleDeleteConfirm() {
    if (!deleteTarget) return
    try {
      await deleteChat.mutateAsync(deleteTarget.id)
      if (deleteTarget.id === activeChatId) {
        navigate({
          to: '/repos/$repoId/chat' as never,
          params: { repoId: repo.id } as never,
        })
      }
    } catch (err) {
      toast.error((err as Error).message)
    }
    close()
  }

  return (
    <aside className="flex h-full w-full flex-col border-r border-border bg-card/30">
      <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-3">
        <Link
          to="/dashboard"
          className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
          Repos
        </Link>
        <Button
          size="sm"
          onClick={handleCreate}
          disabled={isCreating}
          className="h-7 gap-1.5 text-xs"
        >
          <Plus className="h-3.5 w-3.5" aria-hidden="true" />
          New chat
        </Button>
      </div>

      <div className="flex flex-col gap-0.5 px-3 py-3">
        <span className="px-1 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
          {repo.fullName}
        </span>
      </div>

      <ScrollArea className="flex-1">
        <div className="flex flex-col gap-0.5 px-2 pb-3">
          {isLoading && <SidebarSkeleton />}
          {!isLoading && (chats?.length ?? 0) === 0 && (
            <p className="px-2 py-6 text-center text-xs text-muted-foreground">
              No conversations yet.
            </p>
          )}
          {chats?.map((chat) => (
            <ChatSidebarItem
              key={chat.id}
              chat={chat}
              repoId={repo.id}
              isActive={activeChatId === chat.id}
              onRename={() => openRename(chat)}
              onDelete={() => openDelete(chat)}
            />
          ))}
        </div>
      </ScrollArea>

      <div className="mt-auto border-t border-border p-2">
        <Link
          to={'/repos/$repoId/analyses' as never}
          params={{ repoId: repo.id } as never}
          className={cn(
            'flex items-center gap-2 rounded-md px-2 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground',
          )}
        >
          <ListTree className="h-3.5 w-3.5" aria-hidden="true" />
          View technical analyses
        </Link>
        <div className="flex items-center gap-2 px-2 py-1.5 text-[11px] text-muted-foreground">
          <MessagesSquare className="h-3 w-3" aria-hidden="true" />
          {chats?.length ?? 0} conversation{(chats?.length ?? 0) === 1 ? '' : 's'}
        </div>
      </div>

      <RenameChatDialog
        open={!!renameTarget}
        onOpenChange={(open) => !open && close()}
        initialTitle={renameTarget?.title ?? ''}
        isPending={renameChat.isPending}
        onSubmit={handleRenameSubmit}
      />

      <DeleteChatDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && close()}
        chatTitle={deleteTarget?.title ?? ''}
        isPending={deleteChat.isPending}
        onConfirm={handleDeleteConfirm}
      />
    </aside>
  )
}
