const RELATIVE = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })

export function formatRelative(dateIso: string): string {
  const diffMs = new Date(dateIso).getTime() - Date.now()
  const diffMin = Math.round(diffMs / (1000 * 60))
  if (Math.abs(diffMin) < 60) return RELATIVE.format(diffMin, 'minute')
  const diffHour = Math.round(diffMin / 60)
  if (Math.abs(diffHour) < 24) return RELATIVE.format(diffHour, 'hour')
  const diffDay = Math.round(diffHour / 24)
  if (Math.abs(diffDay) < 30) return RELATIVE.format(diffDay, 'day')
  const diffMonth = Math.round(diffDay / 30)
  return RELATIVE.format(diffMonth, 'month')
}
