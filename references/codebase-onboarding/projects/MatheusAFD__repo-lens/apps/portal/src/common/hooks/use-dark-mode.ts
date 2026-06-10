import { useEffect, useState } from 'react'

export type ThemeMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'repolens-theme'
const COOKIE_NAME = 'repolens-theme'

function resolveIsLight(mode: ThemeMode): boolean {
  if (mode === 'light') return true
  if (mode === 'dark') return false
  return !window.matchMedia('(prefers-color-scheme: dark)').matches
}

function applyTheme(mode: ThemeMode) {
  const isLight = resolveIsLight(mode)
  document.documentElement.classList.toggle('light', isLight)
}

function persistTheme(mode: ThemeMode) {
  localStorage.setItem(STORAGE_KEY, mode)
  document.cookie = `${COOKIE_NAME}=${mode};path=/;max-age=31536000;samesite=lax`
}

export function useTheme() {
  const [mode, setModeState] = useState<ThemeMode>(() => {
    if (typeof window === 'undefined') return 'dark'
    return (localStorage.getItem(STORAGE_KEY) as ThemeMode) ?? 'dark'
  })

  useEffect(() => {
    if (mode !== 'system') return
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const handler = () => applyTheme('system')
    mq.addEventListener('change', handler)
    return () => mq.removeEventListener('change', handler)
  }, [mode])

  function setMode(next: ThemeMode) {
    applyTheme(next)
    persistTheme(next)
    setModeState(next)
  }

  return { mode, setMode }
}

export function useDarkMode() {
  const { mode, setMode } = useTheme()
  const isDark = !resolveIsLight(mode)
  return {
    isDark,
    toggle: () => setMode(isDark ? 'light' : 'dark'),
  }
}
