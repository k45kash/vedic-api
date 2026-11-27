import { taraFor } from './tara'

export const TARA_GOALS = [
  { id: 'meetings', label: 'Переговоры и встречи', taras: [8, 9], reason: 'общение и сотрудничество', timing: 'whole' },
  { id: 'contract', label: 'Договор и деловые вопросы', taras: [2, 9], reason: 'договорённости и деловые вопросы', timing: 'start' },
  { id: 'project', label: 'Старт долгосрочного проекта', taras: [4, 6], reason: 'созидание, устойчивость и достижение целей', timing: 'start' },
  { id: 'renovation', label: 'Ремонт и обустройство', taras: [4], reason: 'ремонт и обустройство дома', timing: 'whole' },
  { id: 'study', label: 'Учёба и сосредоточенная работа', taras: [6], reason: 'учёба, внимание и дисциплина', timing: 'whole' },
  { id: 'completion', label: 'Завершение начатого и порядок', taras: [3, 5, 7], reason: 'ревизия, исправление ошибок и завершение дел', timing: 'whole' },
] as const

export type TaraTiming = 'start' | 'whole'
export type TaraGoal = typeof TARA_GOALS[number]
type Range = { start: number; end: number }
type Factor = 'rahu' | 'bhadra' | 'abhijit' | 'wednesday'
type DateInterval = { dt_start: string; dt_end: string }
export type TaraTimeline = {
  nakshatra: (DateInterval & { num?: number })[]
  karana: (DateInterval & { is_bhadra?: boolean })[]
  rahu: DateInterval[]
  abhijit: DateInterval[]
  vara: (DateInterval & { num?: number })[]
}

export const TARA_FACTOR_LABELS: Record<Factor, string> = {
  rahu: 'Раху-кала',
  bhadra: 'Бхадра',
  abhijit: 'Абхиджит',
  wednesday: 'Абхиджит в среду',
}

export const TARA_TIMING_LABELS = {
  start: 'В момент начала',
  whole: 'На всю длительность',
} as const

export function parseTaraDate(stamp: string) {
  return Date.parse(/[+-]\d{2}:\d{2}$|Z$/.test(stamp) ? stamp : stamp + 'Z')
}

function bounds(interval: DateInterval): Range {
  return { start: parseTaraDate(interval.dt_start), end: parseTaraDate(interval.dt_end) }
}

function contains(range: Range, at: number) {
  return range.start <= at && at < range.end
}

function overlaps(a: Range, b: Range) {
  return a.start < b.end && b.start < a.end
}

export function isWednesdayAbhijit(interval: DateInterval, vara: TaraTimeline['vara']) {
  const start = parseTaraDate(interval.dt_start)
  return vara.some(day => day.num === 3 && contains(bounds(day), start))
}

const MINUTE = 60000
type Window = {
  firstStart: number
  lastStart: number
  names: string[]
  schoolPositions: number[]
  warnings: Factor[]
  caution: boolean
  beginsInAbhijit: boolean
  changes: { at: number; label: string }[]
}

export function findTaraWindows(
  day: Range, rows: TaraTimeline, candidates: number[], goal: TaraGoal,
  durationMinutes: number, timing: TaraTiming,
) {
  const duration = durationMinutes * MINUTE
  if (!Number.isInteger(durationMinutes) || durationMinutes < 1 || !candidates.length
    || duration > day.end - day.start || !rows.vara.some(row => overlaps(bounds(row), day))) return []

  const taras: readonly number[] = goal.taras
  const personal = rows.nakshatra.filter(row => row.num && overlaps(bounds(row), day)).map(row => {
    const variants = candidates.map(janma => taraFor(janma, row.num!))
    return { ...bounds(row), fits: variants.every(tara => taras.includes(tara.n)),
      names: [...new Set(variants.map(tara => tara.name))],
      school: variants.filter(tara => tara.schoolAvoid).map(tara => tara.pos) }
  })
  const factors = [
    ...rows.rahu.map(row => ({ ...bounds(row), kind: 'rahu' as const })),
    ...rows.karana.filter(row => row.is_bhadra).map(row => ({ ...bounds(row), kind: 'bhadra' as const })),
    ...rows.abhijit.map(row => ({ ...bounds(row), kind: isWednesdayAbhijit(row, rows.vara) ? 'wednesday' as const : 'abhijit' as const })),
  ].filter(row => overlaps(row, day))
  const suitability = personal.filter(part => part.fits).sort((a, b) => a.start - b.start)
    .reduce<Range[]>((ranges, part) => {
      const previous = ranges.at(-1)
      if (previous && part.start <= previous.end) previous.end = Math.max(previous.end, part.end)
      else ranges.push({ start: part.start, end: part.end })
      return ranges
    }, [])

  const windows: Window[] = []
  let previousSignature = ''
  for (let start = day.start; start + duration <= day.end; start += MINUTE) {
    const event = { start, end: start + duration }
    const matches = (range: Range) => timing === 'start' ? contains(range, start) : overlaps(range, event)
    if (!suitability.some(part => contains(part, start) && (timing === 'start' || event.end <= part.end))) {
      previousSignature = ''
      continue
    }

    const schoolPositions = [...new Set(personal.filter(matches).flatMap(part => part.school))].sort()
    const warnings = [...new Set(factors.filter(row => row.kind !== 'abhijit' && matches(row)).map(row => row.kind))]
    const signature = JSON.stringify([warnings, schoolPositions])
    const previous = windows.at(-1)
    if (previous && signature === previousSignature) {
      previous.lastStart = start
      continue
    }
    previousSignature = signature

    const names = personal.find(part => contains(part, start))?.names ?? []
    const changes = [
      ...personal.map(part => ({ at: part.start, label: 'Тара · ' + part.names.join(' / ') })),
      ...factors.flatMap(({ start, end, kind }) => [
        { at: start, label: 'Начинается ' + TARA_FACTOR_LABELS[kind] },
        { at: end, label: 'Заканчивается ' + TARA_FACTOR_LABELS[kind] },
      ]),
    ].filter(change => start < change.at && change.at < event.end)
      .sort((a, b) => a.at - b.at)
    windows.push({
      firstStart: start, lastStart: start, names, schoolPositions, warnings,
      caution: Boolean(warnings.length || schoolPositions.length),
      beginsInAbhijit: factors.some(row => row.kind === 'abhijit' && contains(row, start)),
      changes,
    })
  }
  return windows.sort((a, b) => Number(a.caution) - Number(b.caution) || a.firstStart - b.firstStart)
}

export type TaraWindow = ReturnType<typeof findTaraWindows>[number]


export function explainMissingTaraWindow(day: Range, rows: TaraTimeline, candidates: number[], goal: TaraGoal) {
  if (!rows.vara.some(row => overlaps(bounds(row), day))) return 'Подбор времени недоступен без цикла восхода и заката.'
  if (!rows.nakshatra.some(row => row.num && overlaps(bounds(row), day))) return 'Расчёт не вернул накшатры Луны для этой даты.'
  if (!findTaraWindows(day, rows, candidates, goal, 1, 'start').length) {
    return 'Нет минут начала, в которые Тара-бала подходит для этой цели.'
  }
  return 'Подходящие минуты начала есть, но событие указанной длительности не помещается в пределах выбранных условий.'
}
