import { createAnalysisStream } from '@/services/http/analysis'
import type { AnalysisResult, AnalysisSectionType, SseEvent } from '@repo/shared'
import { useEffect, useRef, useState } from 'react'

interface StreamState {
  sections: Partial<AnalysisResult>
  currentSection: string | null
  isDone: boolean
  error: string | null
}

export function useAnalysisStream(analysisId: string | null) {
  const [state, setState] = useState<StreamState>({
    sections: {},
    currentSection: null,
    isDone: false,
    error: null,
  })

  const esRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!analysisId) return

    setState({ sections: {}, currentSection: null, isDone: false, error: null })

    const eventSource = createAnalysisStream(analysisId)
    esRef.current = eventSource

    eventSource.onmessage = (event: MessageEvent) => {
      try {
        const payload = JSON.parse(event.data as string) as SseEvent

        if (payload.type === 'section') {
          setState((prev) => ({
            ...prev,
            sections: { ...prev.sections, [payload.name as AnalysisSectionType]: payload.data },
            currentSection: null,
          }))
        }

        if (payload.type === 'progress') {
          setState((prev) => ({ ...prev, currentSection: payload.message }))
        }

        if (payload.type === 'done') {
          setState((prev) => ({ ...prev, isDone: true, currentSection: null }))
          eventSource.close()
        }

        if (payload.type === 'error') {
          setState((prev) => ({ ...prev, error: payload.message, currentSection: null }))
          eventSource.close()
        }
      } catch {}
    }

    eventSource.onerror = () => {
      setState((prev) => ({
        ...prev,
        error: 'Connection lost. The analysis may have failed.',
        currentSection: null,
      }))
      eventSource.close()
    }

    return () => {
      eventSource.close()
    }
  }, [analysisId])

  return state
}
