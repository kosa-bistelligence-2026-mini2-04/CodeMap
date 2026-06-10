import { useNavigate } from "react-router-dom"
import { MessageSquarePlus } from "lucide-react"
import { Button } from "./ui/button"

interface ChatNavbarProps {
  onNewChat: () => void
}

export function ChatNavbar({ onNewChat }: ChatNavbarProps) {
  const navigate = useNavigate()
  
  const handleLogoClick = (e: React.MouseEvent) => {
    e.preventDefault()
    onNewChat() // This will clear messages and close the WebSocket
    navigate('/')
  }

  return (
    <div className="w-full bg-white">
      <div className="max-w-screen-xl mx-auto px-4 sm:px-8 py-4 sm:py-6">
        <div className="flex justify-between items-center">
          {/* Logo */}
          <a 
            href="/"
            onClick={handleLogoClick}
            className="text-2xl sm:text-3xl font-bold hover:opacity-90 transition-opacity flex items-center gap-2"
          >
            <div>
              <span className="text-main">TalkTo</span>
              <span className="text-foreground">GitHub</span>
            </div>
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-main/10 text-main font-medium">BETA</span>
          </a>

          {/* New Chat Button */}
          <Button 
            variant="default"
            className="bg-main hover:bg-main/90 text-main-foreground rounded-2xl px-3 sm:px-6 py-2 font-medium flex items-center gap-2 shadow-shadow cursor-pointer text-sm sm:text-base"
            onClick={onNewChat}
          >
            <span className="hidden sm:inline">New Chat</span>
            <span className="sm:hidden">New Chat</span>
            <MessageSquarePlus className="h-4 w-4 sm:h-5 sm:w-5" />
          </Button>
        </div>
      </div>
      <div className="h-[4px] bg-black" />
    </div>
  )
}
