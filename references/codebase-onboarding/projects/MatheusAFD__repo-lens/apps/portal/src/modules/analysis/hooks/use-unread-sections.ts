import type { AnalysisSectionType } from '@repo/shared'
import { useEffect, useRef, useState } from 'react'

export function useUnreadSections(
  completedSections: AnalysisSectionType[],
  activeTab: AnalysisSectionType,
): Set<AnalysisSectionType> {
  const [unread, setUnread] = useState<Set<AnalysisSectionType>>(new Set())
  const prevCompleted = useRef<Set<AnalysisSectionType>>(new Set())

  useEffect(() => {
    const prev = prevCompleted.current
    const newSections = completedSections.filter((s) => !prev.has(s))

    if (newSections.length === 0) return

    setUnread((current) => {
      const next = new Set(current)
      for (const section of newSections) {
        if (section !== activeTab) {
          next.add(section)
        }
      }
      return next
    })

    prevCompleted.current = new Set(completedSections)
  }, [completedSections, activeTab])

  useEffect(() => {
    setUnread((current) => {
      if (!current.has(activeTab)) return current
      const next = new Set(current)
      next.delete(activeTab)
      return next
    })
  }, [activeTab])

  return unread
}
