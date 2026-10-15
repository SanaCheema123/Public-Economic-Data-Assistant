export const yearOf = (date?: string) => date ? date.slice(0, 4) : ''

export function formatValue(value: number, unit = '') {
  const formatted = Math.abs(value) >= 1000
    ? new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(value)
    : new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(value)
  return unit.startsWith('%') ? `${formatted}%` : unit ? `${formatted} ${unit}` : formatted
}

export function relativeTime(iso: string, language: 'en' | 'ar' = 'en') {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.max(1, Math.floor(diff / 60000))
  const rtf = new Intl.RelativeTimeFormat(language, { numeric: 'auto' })
  if (minutes < 60) return rtf.format(-minutes, 'minute')
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return rtf.format(-hours, 'hour')
  return rtf.format(-Math.floor(hours / 24), 'day')
}
