import type {
  Chat,
  ChatMessage,
  CreateChatRequest,
  PromptSuggestionsResponse,
  RenameChatRequest,
} from '@repo/shared'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:4000'

const opts = { credentials: 'include' as const }
const jsonHeaders = { 'Content-Type': 'application/json' }

export async function listChats(repoId: string): Promise<Chat[]> {
  const res = await fetch(`${API_URL}/chat/repos/${repoId}`, { ...opts })
  if (!res.ok) throw new Error('Failed to load chats')
  return res.json()
}

export async function createChat(repoId: string, body: CreateChatRequest = {}): Promise<Chat> {
  const res = await fetch(`${API_URL}/chat/repos/${repoId}`, {
    method: 'POST',
    headers: jsonHeaders,
    ...opts,
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error('Failed to create chat')
  return res.json()
}

export async function getChat(chatId: string): Promise<Chat> {
  const res = await fetch(`${API_URL}/chat/${chatId}`, { ...opts })
  if (!res.ok) throw new Error('Failed to load chat')
  return res.json()
}

export async function getChatMessages(chatId: string): Promise<ChatMessage[]> {
  const res = await fetch(`${API_URL}/chat/${chatId}/messages`, { ...opts })
  if (!res.ok) throw new Error('Failed to load messages')
  return res.json()
}

export async function renameChat(chatId: string, body: RenameChatRequest): Promise<Chat> {
  const res = await fetch(`${API_URL}/chat/${chatId}`, {
    method: 'PATCH',
    headers: jsonHeaders,
    ...opts,
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error('Failed to rename chat')
  return res.json()
}

export async function deleteChat(chatId: string): Promise<{ success: true }> {
  const res = await fetch(`${API_URL}/chat/${chatId}`, {
    method: 'DELETE',
    ...opts,
  })
  if (!res.ok) throw new Error('Failed to delete chat')
  return res.json()
}

export async function getPromptSuggestions(repoId: string): Promise<PromptSuggestionsResponse> {
  const res = await fetch(`${API_URL}/chat/repos/${repoId}/suggestions`, { ...opts })
  if (!res.ok) throw new Error('Failed to load suggestions')
  return res.json()
}

interface SendMessageInit {
  chatId: string
  content: string
  signal?: AbortSignal
}

export async function startMessageStream({ chatId, content, signal }: SendMessageInit) {
  const res = await fetch(`${API_URL}/chat/${chatId}/messages`, {
    method: 'POST',
    headers: { ...jsonHeaders, Accept: 'text/event-stream' },
    ...opts,
    body: JSON.stringify({ content }),
    signal,
  })
  if (!res.ok || !res.body) throw new Error('Failed to start chat stream')
  return res.body
}
