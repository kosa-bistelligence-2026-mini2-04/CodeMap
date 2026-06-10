import type { Chat } from '@repo/shared'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@repo/ui/components/dropdown-menu'
import { cn } from '@repo/ui/lib/utils'
import { Link } from '@tanstack/react-router'
import { MoreHorizontal, Pencil, Trash2 } from 'lucide-react'
import { formatRelative } from './format-relative'

interface ChatSidebarItemProps {
  chat: Chat
  repoId: string
  isActive: boolean
  onRename: () => void
  onDelete: () => void
}

export function ChatSidebarItem({
  chat,
  repoId,
  isActive,
  onRename,
  onDelete,
}: ChatSidebarItemProps) {
  return (
    <div
      className={cn(
        'group flex items-center gap-1 rounded-md px-1 py-0.5 transition-colors',
        isActive ? 'bg-muted' : 'hover:bg-muted/60',
      )}
    >
      <Link
        to={'/repos/$repoId/chat/$chatId' as never}
        params={{ repoId, chatId: chat.id } as never}
        className="flex flex-1 flex-col gap-0.5 truncate px-2 py-1.5 text-left"
        data-active={isActive}
      >
        <span className="truncate text-sm text-foreground">{chat.title}</span>
        <span className="truncate text-[11px] text-muted-foreground">
          {formatRelative(chat.lastMessageAt)}
        </span>
      </Link>
      <DropdownMenu>
        <DropdownMenuTrigger
          aria-label="Conversation options"
          className="flex h-7 w-7 items-center justify-center rounded text-muted-foreground opacity-0 transition group-hover:opacity-100 hover:bg-accent hover:text-accent-foreground data-[state=open]:opacity-100"
        >
          <MoreHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-44">
          <DropdownMenuItem onSelect={onRename} className="cursor-pointer">
            <Pencil className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
            Rename
          </DropdownMenuItem>
          <DropdownMenuItem
            onSelect={onDelete}
            className="cursor-pointer text-destructive focus:text-destructive"
          >
            <Trash2 className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}
