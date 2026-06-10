import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@repo/ui/components/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@repo/ui/components/dialog'
import { Input } from '@repo/ui/components/input'
import { Label } from '@repo/ui/components/label'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { type RenameChatFormValues, renameChatSchema } from '../schemas/chat.schema'

interface RenameChatDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  initialTitle: string
  isPending?: boolean
  onSubmit: (values: RenameChatFormValues) => Promise<void> | void
}

export function RenameChatDialog({
  open,
  onOpenChange,
  initialTitle,
  isPending,
  onSubmit,
}: RenameChatDialogProps) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<RenameChatFormValues>({
    resolver: zodResolver(renameChatSchema),
    defaultValues: { title: initialTitle },
  })

  useEffect(() => {
    if (open) reset({ title: initialTitle })
  }, [open, initialTitle, reset])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form onSubmit={handleSubmit(async (values) => onSubmit(values))}>
          <DialogHeader>
            <DialogTitle>Rename conversation</DialogTitle>
            <DialogDescription>Give this conversation a clearer name.</DialogDescription>
          </DialogHeader>
          <div className="space-y-2 py-3">
            <Label htmlFor="rename-chat-title">Title</Label>
            <Input id="rename-chat-title" autoFocus {...register('title')} />
            {errors.title && <p className="text-xs text-destructive">{errors.title.message}</p>}
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending || isSubmitting}>
              {isPending || isSubmitting ? 'Saving…' : 'Save'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
