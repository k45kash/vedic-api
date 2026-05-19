// Date/duration formatting used in result blocks.
export function useFormatters() {
  function fmtDate(s: string): string {
    if (!s) return ''
    const d = new Date(s)
    if (isNaN(d.getTime())) return s
    return d.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' })
  }

  function fmtYears(days: number): string {
    if (days < 365) return `${Math.round(days)} дн`
    const y = Math.floor(days / 365.25)
    const m = Math.round((days - y * 365.25) / 30.44)
    return m === 0 ? `${y} г` : `${y} г ${m} мес`
  }

  return { fmtDate, fmtYears }
}
