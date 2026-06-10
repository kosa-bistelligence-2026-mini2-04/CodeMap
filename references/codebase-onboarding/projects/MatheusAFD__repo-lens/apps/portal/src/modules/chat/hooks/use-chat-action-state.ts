import type { Chat } from '@repo/shared'
import { useCallback, useState } from 'react'

export function useChatActionState() {
  const [renameTarget, setRenameTarget] = useState<Chat | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Chat | null>(null)

  const openRename = useCallback((chat: Chat) => {
    setDeleteTarget(null)
    setRenameTarget(chat)
  }, [])

  const openDelete = useCallback((chat: Chat) => {
    setRenameTarget(null)
    setDeleteTarget(chat)
  }, [])

  const close = useCallback(() => {
    setRenameTarget(null)
    setDeleteTarget(null)
  }, [])

  return { renameTarget, deleteTarget, openRename, openDelete, close }
}
