import { taraFor } from './tara'
import { evaluateEventNakshatra, evaluateEventTithi, evaluateEventWeekday, evaluateEventYoga, listEvents } from './event-picker'
import { splitTithi } from './api-adapter'
import { WEEKDAYS_RU, type ScoreLine } from './types'

export type TaraTiming = 'start' | 'whole'
export type TaraGoal = {
  id: string
  label: string
  taras: readonly number[] | null
  reason: string
  timing: TaraTiming
  minutes: number
  missing?: string
  ruleId?: string
}

const EVENT_GROUPS = [
  { label: 'Семья и дом', ids: ['wedding', 'house', 'namakarana', 'conception', 'construction', 'renovation'] },
  { label: 'Дело и деньги', ids: ['business', 'newproject', 'factory', 'contract', 'finance', 'court', 'conflict', 'sell_stuff'] },
  { label: 'Покупки', ids: ['vehicle', 'buy_electronics', 'buy_clothes'] },
  { label: 'Учёба и творчество', ids: ['education', 'creative'] },
  { label: 'Дорога и отдых', ids: ['travel', 'rest', 'sport'] },
  { label: 'Тело и здоровье', ids: ['medical', 'haircut', 'cosmetic', 'bodycare'] },
  { label: 'Духовная практика', ids: ['spiritual', 'sadhana', 'tapas'] },
  { label: 'Быт и природа', ids: ['cleaning', 'planting', 'aquarium', 'pet_care'] },
]

const timePresets: Record<string, Omit<TaraGoal, 'id' | 'ruleId' | 'label'>> = {
  contract: { taras: [2, 9], reason: 'договорённости и деловые вопросы', timing: 'start', minutes: 30 },
  newproject: { taras: [4, 6], reason: 'созидание, устойчивость и достижение целей', timing: 'start', minutes: 30 },
  renovation: { taras: [4], reason: 'ремонт и обустройство дома', timing: 'whole', minutes: 30 },
  education: { taras: [6], reason: 'учёба, внимание и дисциплина', timing: 'whole', minutes: 30 },
  travel: { taras: [2, 9], timing: 'start', minutes: 1, reason: 'начало путешествия', missing: 'Отдельные правила для разных видов транспорта и этапов поездки.' },
  haircut: { taras: null, timing: 'whole', minutes: 90, reason: 'общие факторы времени', missing: 'Отдельный ориентир по Тара-бале для стрижки.' },
  cosmetic: { taras: null, timing: 'whole', minutes: 60, reason: 'общие факторы времени', missing: 'Правила Тара-балы для выбранного вида ухода.' },
  bodycare: { taras: null, timing: 'whole', minutes: 60, reason: 'общие факторы времени', missing: 'Правила, по которым общий ориентир для массажа применять к разным спа-процедурам.' },
}

const legacyEventIds = new Map<string, string>([
  ['project', 'newproject'],
  ['study', 'education'],
  ['departure', 'travel'],
  ['hair', 'haircut'],
  ['beauty-care', 'cosmetic'],
  ['spa', 'bodycare'],
])

const eventDefs = listEvents()
const catalog: TaraGoal[] = eventDefs.map(event => {
  const preset = timePresets[event.id]
  return {
    id: event.id,
    ruleId: event.id,
    label: event.label === 'Садхана' ? event.name : event.label,
    taras: preset?.taras ?? null,
    reason: preset?.reason ?? '',
    timing: preset?.timing ?? 'start',
    minutes: preset?.minutes ?? 30,
    missing: preset?.missing,
  }
})
const assignedIds = new Set(EVENT_GROUPS.flatMap(group => group.ids))
export const EVENT_GOAL_GROUPS = [
  ...EVENT_GROUPS.map(group => ({
    label: group.label,
    goals: group.ids.flatMap(id => catalog.filter(goal => goal.id === id)),
  })),
  { label: 'Прочее', goals: catalog.filter(goal => !assignedIds.has(goal.id)) },
].filter(group => group.goals.length)

export function findEventGoal(id: unknown) {
  if (typeof id !== 'string') return
  const canonical = legacyEventIds.get(id) ?? id
  return catalog.find(goal => goal.id === canonical)
}


type Range = { start: number; end: number }
type Factor = 'rahu' | 'bhadra' | 'abhijit' | 'wednesday'
type DateInterval = { dt_start: string; dt_end: string }
export type TaraTimeline = {
  nakshatra: (DateInterval & { num?: number })[]
  karana: (DateInterval & { is_bhadra?: boolean })[]
  rahu: DateInterval[]
  abhijit: DateInterval[]
  vara: (DateInterval & { num?: number })[]
  tithi?: (DateInterval & { num?: number; name?: string })[]
  yoga?: (DateInterval & { name?: string })[]
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

export function eventRuleForGoal(goal: TaraGoal) {
  return eventDefs.find(event => event.id === goal.ruleId)
}

type PanchangaFactor = Range & { label: string; line?: ScoreLine }

function startFactor(rows: PanchangaFactor[], start: number) {
  return rows.find(row => contains(row, start))
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
  fits: boolean | null
  tithi?: string
  yoga?: string
  nakshatraRule?: ScoreLine
  weekdayRule?: ScoreLine
  tithiRule?: ScoreLine
  yogaRule?: ScoreLine
  veto: boolean
  eventRank: number
  tithiRank: number
  yogaBonus: boolean
  changes: { at: number; label: string }[]
}

export function findTaraWindows(
  day: Range, rows: TaraTimeline, candidates: number[], goal: TaraGoal,
  durationMinutes: number, timing: TaraTiming, selectedStart?: number,
) {
  const duration = durationMinutes * MINUTE
  if (!Number.isInteger(durationMinutes) || durationMinutes < 1 || (goal.taras && !candidates.length)
    || duration > day.end - day.start || !rows.vara.some(row => overlaps(bounds(row), day))) return []

  const taras = goal.taras
  const first = selectedStart ?? day.start
  const last = selectedStart ?? day.end - duration
  if (first < day.start || last + duration > day.end || !Number.isFinite(first)) return []
  const rule = eventRuleForGoal(goal)
  const personal = rows.nakshatra.filter(row => row.num && overlaps(bounds(row), day)).map(row => {
    const variants = candidates.map(janma => taraFor(janma, row.num!))
    return { ...bounds(row), fits: !taras || variants.every(tara => taras.includes(tara.n)),
      names: [...new Set(variants.map(tara => tara.name))],
      school: variants.filter(tara => tara.schoolAvoid).map(tara => tara.pos),
      line: rule ? evaluateEventNakshatra(rule, row.num!) : undefined }
  })
  const factors = [
    ...rows.rahu.map(row => ({ ...bounds(row), kind: 'rahu' as const })),
    ...rows.karana.filter(row => row.is_bhadra).map(row => ({ ...bounds(row), kind: 'bhadra' as const })),
    ...rows.abhijit.map(row => ({ ...bounds(row), kind: isWednesdayAbhijit(row, rows.vara) ? 'wednesday' as const : 'abhijit' as const })),
  ].filter(row => overlaps(row, day))
  const weekdays = rows.vara.filter(row => row.num && row.num >= 1 && row.num <= 7 && overlaps(bounds(row), day)).map(row => ({
    ...bounds(row), line: rule ? evaluateEventWeekday(rule, WEEKDAYS_RU[row.num! % 7]) : undefined,
  }))
  const tithis = (rows.tithi ?? []).filter(row => row.name && overlaps(bounds(row), day)).map(row => {
    const split = row.num && row.num >= 1 && row.num <= 30 ? splitTithi(row.num) : undefined
    const label = 'Титхи · ' + row.name + (split ? (split.paksha === 'krishna' ? ' (Кришна)' : ' (Шукла)') : '')
    const line = rule && split ? evaluateEventTithi(rule, split.tithi, split.paksha).line : undefined
    return { ...bounds(row), label, line }
  })
  const yogas = (rows.yoga ?? []).filter(row => row.name && overlaps(bounds(row), day)).map(row => {
    return { ...bounds(row), label: 'Йога · ' + row.name,
      line: rule ? evaluateEventYoga(rule, row.name!) : undefined }
  })
  const suitability = personal.filter(part => part.fits).sort((a, b) => a.start - b.start)
    .reduce<Range[]>((ranges, part) => {
      const previous = ranges.at(-1)
      if (previous && part.start <= previous.end) previous.end = Math.max(previous.end, part.end)
      else ranges.push({ start: part.start, end: part.end })
      return ranges
    }, [])

  const windows: Window[] = []
  let previousSignature = ''
  for (let start = first; start <= last; start += MINUTE) {
    const event = { start, end: start + duration }
    const matches = (range: Range) => timing === 'start' ? contains(range, start) : overlaps(range, event)
    const fits = suitability.some(part => contains(part, start) && (timing === 'start' || event.end <= part.end))
    if (!fits && selectedStart === undefined) {
      previousSignature = ''
      continue
    }

    const activeTithis = tithis.filter(matches)
    const activeYogas = yogas.filter(matches)
    const vetoTithi = activeTithis.find(row => row.line?.sign === '⛔')
    const activeNakshatras = personal.filter(matches)
    const activeWeekdays = weekdays.filter(matches)
    const vetoNakshatra = activeNakshatras.find(row => row.line?.sign === '⛔')
    if ((vetoTithi || vetoNakshatra) && selectedStart === undefined) {
      previousSignature = ''
      continue
    }
    const avoidTithi = activeTithis.find(row => row.line?.sign === '−')
    const tithiGood = activeTithis.length > 0 && activeTithis.every(row => row.line?.sign === '+')
    const yogaBonus = activeYogas.length > 0 && activeYogas.every(row => row.line?.sign === '+')
    const tithiRank = avoidTithi ? -1 : Number(tithiGood)

    const avoidWeekday = activeWeekdays.find(row => row.line?.sign === '−')
    const nakshatraGood = activeNakshatras.length > 0 && activeNakshatras.every(row => row.line?.sign === '+')
    const weekdayGood = activeWeekdays.length > 0 && activeWeekdays.every(row => row.line?.sign === '+')
    const eventRank = Number(nakshatraGood) + (avoidWeekday ? -1 : Number(weekdayGood))
    const schoolPositions = [...new Set(activeNakshatras.flatMap(part => part.school))].sort()
    const warnings = [...new Set(factors.filter(row => row.kind !== 'abhijit' && matches(row)).map(row => row.kind))]
    const currentNakshatra = personal.find(part => contains(part, start))
    if (!currentNakshatra) { previousSignature = ''; continue }
    const currentWeekday = weekdays.find(part => contains(part, start))
    const currentTithi = startFactor(tithis, start)
    const currentYoga = startFactor(yogas, start)
    const signature = JSON.stringify([warnings, schoolPositions, eventRank, tithiRank, yogaBonus,
      currentNakshatra.names, currentNakshatra.line, currentWeekday?.line, avoidWeekday?.line, currentTithi?.label, currentYoga?.label])
    const previous = windows.at(-1)
    if (previous && signature === previousSignature) {
      previous.lastStart = start
      continue
    }
    previousSignature = signature

    const changes = [
      ...personal.flatMap(part => [
        ...(part.names.length ? [{ at: part.start, label: 'Тара · ' + part.names.join(' / ') }] : []),
        ...(part.line ? [{ at: part.start, label: part.line.text }] : []),
      ]),
      ...weekdays.flatMap(part => part.line ? [{ at: part.start, label: part.line.text }] : []),
      ...[...tithis, ...yogas].map(row => ({ at: row.start, label: row.line?.text ?? row.label })),
      ...factors.flatMap(({ start, end, kind }) => [
        { at: start, label: 'Начинается ' + TARA_FACTOR_LABELS[kind] },
        { at: end, label: 'Заканчивается ' + TARA_FACTOR_LABELS[kind] },
      ]),
    ].filter(change => start < change.at && change.at < event.end)
      .sort((a, b) => a.at - b.at)
    windows.push({
      firstStart: start, lastStart: start, names: currentNakshatra.names, schoolPositions, warnings, fits: taras ? fits : null,
      nakshatraRule: (vetoNakshatra ?? currentNakshatra).line,
      weekdayRule: (avoidWeekday ?? currentWeekday)?.line,
      tithi: currentTithi?.label, yoga: currentYoga?.label,
      tithiRule: (vetoTithi ?? avoidTithi ?? currentTithi)?.line, yogaRule: currentYoga?.line,
      veto: Boolean(vetoTithi || vetoNakshatra), eventRank, tithiRank, yogaBonus,
      caution: Boolean(warnings.length || schoolPositions.length || vetoTithi || vetoNakshatra || avoidTithi || avoidWeekday),
      beginsInAbhijit: factors.some(row => row.kind === 'abhijit' && contains(row, start)),
      changes,
    })
  }
  return windows.sort((a, b) => Number(a.caution) - Number(b.caution) || b.eventRank - a.eventRank || b.tithiRank - a.tithiRank
    || Number(b.yogaBonus) - Number(a.yogaBonus) || a.firstStart - b.firstStart)
}

export type TaraWindow = ReturnType<typeof findTaraWindows>[number]


export function explainMissingTaraWindow(
  day: Range, rows: TaraTimeline, candidates: number[], goal: TaraGoal,
  durationMinutes: number, timing: TaraTiming,
) {
  if (!rows.vara.some(row => overlaps(bounds(row), day))) return 'Подбор времени недоступен без цикла восхода и заката.'
  if (!rows.nakshatra.some(row => row.num && overlaps(bounds(row), day))) return 'Расчёт не вернул накшатры Луны для этой даты.'
  const baseGoal = { ...goal, ruleId: undefined }
  if (goal.taras && !findTaraWindows(day, rows, candidates, baseGoal, 1, 'start').length) {
    return 'Нет минут начала, в которые Тара-бала подходит для этой цели.'
  }
  if (eventRuleForGoal(goal) && findTaraWindows(day, rows, candidates, baseGoal, durationMinutes, timing).length) {
    return 'Стоп-факторы события по титхи или накшатре исключили все окна нужной длительности.'
  }
  return 'Подходящие минуты начала есть, но событие указанной длительности не помещается в пределах выбранных условий.'
}
