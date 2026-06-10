import { getQuestions } from '@/services/http/analysis'
import type { QuestionAnswer } from '@repo/shared'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useRef, useState } from 'react'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:4000'

export function useAnalysisQuestions(analysisId: string) {
  return useQuery({
    queryKey: ['analysis', analysisId, 'questions'],
    queryFn: () => getQuestions(analysisId),
    staleTime: 0,
  })
}

export function useAskQuestion(analysisId: string) {
  const [streamingAnswer, setStreamingAnswer] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const queryClient = useQueryClient()

  const ask = useCallback(
    async (question: string) => {
      if (isStreaming) return

      setIsStreaming(true)
      setStreamingAnswer('')
      setError(null)

      abortRef.current = new AbortController()

      try {
        const res = await fetch(`${API_URL}/analysis/${analysisId}/ask`, {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
          body: JSON.stringify({ question }),
          signal: abortRef.current.signal,
        })

        if (!res.ok || !res.body) {
          setError('Failed to get a response.')
          setIsStreaming(false)
          return
        }

        const reader = res.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        let fullAnswer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.startsWith('data:')) continue
            const raw = line.slice(5).trim()
            if (!raw) continue
            try {
              const event = JSON.parse(raw) as {
                type: string
                message?: string
                analysisId?: string
              }
              if (event.type === 'progress' && event.message) {
                fullAnswer += event.message
                setStreamingAnswer(fullAnswer)
              } else if (event.type === 'done') {
                setStreamingAnswer(null)
                await queryClient.invalidateQueries({
                  queryKey: ['analysis', analysisId, 'questions'],
                })
              } else if (event.type === 'error') {
                setError(event.message ?? 'An error occurred.')
              }
            } catch {}
          }
        }
      } catch (err) {
        if ((err as Error).name !== 'AbortError') {
          setError('Connection lost.')
        }
      } finally {
        setIsStreaming(false)
        setStreamingAnswer(null)
      }
    },
    [analysisId, isStreaming, queryClient],
  )

  return { ask, streamingAnswer, isStreaming, error }
}

export type { QuestionAnswer }
