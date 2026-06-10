import { useState } from 'react'

export type ViewMode = 'all' | 'product' | 'technical'

const STORAGE_KEY = 'repolens:view-mode'

function readStoredMode(): ViewMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'product' || stored === 'technical' || stored === 'all') return stored
  } catch {}
  return 'all'
}

export function useViewMode() {
  const [viewMode, setViewModeState] = useState<ViewMode>(readStoredMode)

  function setViewMode(mode: ViewMode) {
    setViewModeState(mode)
    try {
      localStorage.setItem(STORAGE_KEY, mode)
    } catch {}
  }

  return { viewMode, setViewMode }
}
