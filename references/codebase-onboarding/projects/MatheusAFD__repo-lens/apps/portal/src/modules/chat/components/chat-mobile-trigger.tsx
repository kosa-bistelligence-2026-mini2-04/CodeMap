import type { Repository } from '@/modules/repos/domain/repo.domain'
import { Button } from '@repo/ui/components/button'
import { Sheet, SheetContent, SheetTitle, SheetTrigger } from '@repo/ui/components/sheet'
import { Menu } from 'lucide-react'
import { useState } from 'react'
import { ChatSidebar } from './chat-sidebar'

interface ChatMobileTriggerProps {
  repo: Repository
  activeChatId?: string
}

export function ChatMobileTrigger({ repo, activeChatId }: ChatMobileTriggerProps) {
  const [open, setOpen] = useState(false)

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 md:hidden"
          aria-label="Open conversations"
        >
          <Menu className="h-4 w-4" aria-hidden="true" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-80 p-0">
        <SheetTitle className="sr-only">Conversations</SheetTitle>
        <ChatSidebar repo={repo} activeChatId={activeChatId} onNavigate={() => setOpen(false)} />
      </SheetContent>
    </Sheet>
  )
}
