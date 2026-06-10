import type { SendMessageRequest } from '@repo/shared'

export class SendMessageDto implements SendMessageRequest {
  content!: string
}

export class CreateChatDto {
  title?: string
}
