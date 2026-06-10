import type { RenameChatRequest } from '@repo/shared'

export class RenameChatDto implements RenameChatRequest {
  title!: string
}
