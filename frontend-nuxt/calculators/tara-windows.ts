import type { TaraResult } from './tara'

export const TARA_GOALS = [
  { label: 'Переговоры и встречи', taras: [8, 9], reason: 'общение и сотрудничество' },
  { label: 'Договор и деловые вопросы', taras: [2, 9], reason: 'договорённости и деловые вопросы' },
  { label: 'Старт долгосрочного проекта', taras: [4, 6], reason: 'созидание, устойчивость и достижение целей' },
  { label: 'Ремонт и обустройство', taras: [4], reason: 'ремонт и обустройство дома' },
  { label: 'Учёба и сосредоточенная работа', taras: [6], reason: 'учёба, внимание и дисциплина' },
  { label: 'Завершение начатого и порядок', taras: [3, 5, 7], reason: 'ревизия, исправление ошибок и завершение дел' },
]

type Range = { start: number; end: number }
type SolarWindow = Range & { kind: 'rahu' | 'bhadra' | 'abhijit' | 'wednesday' }
type PersonalWindow = Range & { taras: TaraResult[] }

export function findTaraWindows(
  day: Range, personal: PersonalWindow[], solar: SolarWindow[],
  goal: typeof TARA_GOALS[number], durationMinutes: number,
) {
  const minimum = durationMinutes * 60000
  if (!Number.isInteger(durationMinutes) || durationMinutes < 1) return []
  return personal.flatMap(part => {
    if (!part.taras.length || !part.taras.every(tara => goal.taras.includes(tara.n))) return []
    const start = Math.max(day.start, part.start)
    const end = Math.min(day.end, part.end)
    if (end <= start) return []
    const relevant = solar.filter(window => window.start < end && start < window.end)
    const edges = [...new Set([start, end, ...relevant.flatMap(window => [
      Math.max(start, window.start), Math.min(end, window.end),
    ])])].sort((a, b) => a - b)
    const names = [...new Set(part.taras.map(tara => tara.name))]
    const schoolPositions = [...new Set(part.taras.filter(tara => tara.schoolAvoid).map(tara => tara.pos))]
    return edges.slice(0, -1).flatMap((edge, i) => {
      const last = edges[i + 1]
      const firstStart = day.start + Math.ceil((edge - day.start) / 60000) * 60000
      if (firstStart + minimum > last) return []
      const flags = [...new Set(relevant.filter(window => window.start <= edge && edge < window.end)
        .map(window => window.kind))]
      const caution = schoolPositions.length > 0 || flags.includes('rahu') || flags.includes('bhadra') || flags.includes('wednesday')
      return [{ start: firstStart, end: last, names, schoolPositions, flags, caution }]
    })
  }).sort((a, b) => Number(a.caution) - Number(b.caution)
    || Number(b.flags.includes('abhijit')) - Number(a.flags.includes('abhijit'))
    || a.start - b.start)
}
