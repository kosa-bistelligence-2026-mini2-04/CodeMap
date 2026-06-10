import { Button } from '@repo/ui/components/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@repo/ui/components/dialog'

interface DeleteChatDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  chatTitle: string
  isPending?: boolean
  onConfirm: () => Promise<void> | void
}

export function DeleteChatDialog({
  open,
  onOpenChange,
  chatTitle,
  isPending,
  onConfirm,
}: DeleteChatDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete conversation?</DialogTitle>
          <DialogDescription>
            "{chatTitle}" and all its messages will be permanently removed.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button variant="destructive" disabled={isPending} onClick={() => void onConfirm()}>
            {isPending ? 'Deleting…' : 'Delete'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
