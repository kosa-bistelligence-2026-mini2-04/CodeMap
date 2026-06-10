import { z } from 'zod'

export const renameChatSchema = z.object({
  title: z.string().trim().min(1, 'Title is required').max(100, 'Title is too long'),
})

export type RenameChatFormValues = z.infer<typeof renameChatSchema>

export const sendMessageSchema = z.object({
  content: z.string().trim().min(1, 'Message is required').max(4000, 'Message is too long'),
})

export type SendMessageFormValues = z.infer<typeof sendMessageSchema>
