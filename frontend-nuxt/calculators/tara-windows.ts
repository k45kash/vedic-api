import { taraFor } from './tara'
import { evaluateEventTithi, evaluateEventYoga, listEvents } from './event-picker'
import { splitTithi } from './api-adapter'
import type { ScoreLine } from './types'

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

export const TARA_GOAL_GROUPS: { label: string; goals: TaraGoal[] }[] = [
  { label: 'Основные цели', goals: [
      { id: 'meetings', label: 'Переговоры и встречи', taras: [8, 9], reason: 'общение и сотрудничество', timing: 'whole', minutes: 30 },
      { id: 'contract', ruleId: 'contract', label: 'Договор и деловые вопросы', taras: [2, 9], reason: 'договорённости и деловые вопросы', timing: 'start', minutes: 30 },
      { id: 'project', ruleId: 'newproject', label: 'Старт долгосрочного проекта', taras: [4, 6], reason: 'созидание, устойчивость и достижение целей', timing: 'start', minutes: 30 },
      { id: 'renovation', ruleId: 'renovation', label: 'Ремонт и обустройство', taras: [4], reason: 'ремонт и обустройство дома', timing: 'whole', minutes: 30 },
      { id: 'study', ruleId: 'education', label: 'Учёба и сосредоточенная работа', taras: [6], reason: 'учёба, внимание и дисциплина', timing: 'whole', minutes: 30 },
      { id: 'completion', label: 'Завершение начатого и порядок', taras: [3, 5, 7], reason: 'ревизия, исправление ошибок и завершение дел', timing: 'whole', minutes: 30 },
  ] },
  { label: 'Работа и проекты', goals: [
      { id: 'interview', label: 'Собеседование или презентация', taras: [8, 9], timing: 'whole', minutes: 45, reason: 'встречи и публичность', missing: 'Отдельные правила для собеседований и выступлений.' },
      { id: 'first-workday', label: 'Первый день на новой работе', taras: [6, 9], timing: 'start', minutes: 1, reason: 'карьера и важные дела', missing: 'Отдельные правила для начала работы.' },
      { id: 'publication', label: 'Запуск сайта, рекламы или публикации', taras: [9], timing: 'start', minutes: 1, reason: 'публичность и продвижение проектов', missing: 'Отдельные правила для запуска сайта, рекламы и публикаций.' },
      { id: 'acceptance', label: 'Приёмка работ или осмотр объекта', taras: null, timing: 'whole', minutes: 60, reason: 'общие факторы времени', missing: 'Правила Тара-балы для приёмки и осмотра.' },
      { id: 'acceptance-act', label: 'Подписание акта приёмки', taras: [2, 9], timing: 'start', minutes: 1, reason: 'договоры и документы', missing: 'Отдельные правила для подписания акта.' },
  ] },
  { label: 'Путешествия', goals: [
      { id: 'departure', ruleId: 'travel', label: 'Выезд в поездку', taras: [2, 9], timing: 'start', minutes: 1, reason: 'начало путешествия', missing: 'Отдельные правила для разных видов транспорта и этапов поездки.' },
      { id: 'road-trip', ruleId: 'travel', label: 'Старт автопутешествия', taras: [2, 9], timing: 'start', minutes: 1, reason: 'начало путешествия', missing: 'Отдельные правила для выезда на автомобиле.' },
      { id: 'move-in', label: 'Заселение при переезде', taras: null, timing: 'start', minutes: 1, reason: 'общие факторы времени', missing: 'Правила Тара-балы для момента заселения.' },
  ] },
  { label: 'Красота и уход', goals: [
      { id: 'hair', ruleId: 'haircut', label: 'Стрижка', taras: null, timing: 'whole', minutes: 90, reason: 'общие факторы времени', missing: 'Отдельный ориентир по Тара-бале для стрижки.' },
      { id: 'hair-color', label: 'Окрашивание волос', taras: null, timing: 'whole', minutes: 90, reason: 'общие факторы времени', missing: 'Отдельные правила Тара-балы, титхи и йоги для окрашивания.' },
      { id: 'nails', label: 'Маникюр или педикюр', taras: null, timing: 'whole', minutes: 90, reason: 'общие факторы времени', missing: 'Отдельное правило Тара-балы для маникюра и педикюра.' },
      { id: 'beauty-care', ruleId: 'cosmetic', label: 'Уходовая процедура', taras: null, timing: 'whole', minutes: 60, reason: 'общие факторы времени', missing: 'Правила Тара-балы для выбранного вида ухода.' },
      { id: 'spa', ruleId: 'bodycare', label: 'Массаж или спа', taras: null, timing: 'whole', minutes: 60, reason: 'общие факторы времени', missing: 'Правила, по которым общий ориентир для массажа применять к разным спа-процедурам.' },
  ] },
  { label: 'Отношения', goals: [
      { id: 'first-date', label: 'Первое свидание', taras: [2, 9], timing: 'whole', minutes: 90, reason: 'свидания и отношения', missing: 'Отдельные правила для первого свидания. Подбор для двоих требует второго профиля и правила сравнения.' },
      { id: 'date-night', label: 'Свидание вдвоём', taras: [2, 9], timing: 'whole', minutes: 120, reason: 'свидания и отношения', missing: 'Подбор для двоих требует второго профиля и правила сравнения.' },
      { id: 'proposal', label: 'Предложение руки и сердца', taras: null, timing: 'start', minutes: 1, reason: 'общие факторы времени', missing: 'Отдельные правила для момента предложения. Для подбора на двоих — второй профиль и правило сравнения.' },
      { id: 'reconciliation', label: 'Разговор для примирения', taras: [8], timing: 'whole', minutes: 45, reason: 'улучшение отношений', missing: 'Отдельные критерии примирения. Для подбора на двоих — второй профиль и правило сравнения.' },
      { id: 'personal-talk', label: 'Важный личный разговор', taras: [8], timing: 'whole', minutes: 45, reason: 'разговоры и отношения', missing: 'Отдельные критерии для темы разговора. Для подбора на двоих — второй профиль и правило сравнения.' },
      { id: 'closure-talk', label: 'Разговор о завершении общения', taras: null, timing: 'whole', minutes: 45, reason: 'общие факторы времени', missing: 'Правила Тара-балы для разговора о завершении отношений.' },
  ] },
]

export const TARA_GOALS = TARA_GOAL_GROUPS.flatMap(group => group.goals)

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
  return listEvents().find(event => event.id === goal.ruleId)
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
  tithiRule?: ScoreLine
  yogaRule?: ScoreLine
  veto: boolean
  tithiRank: number
  yogaBonus: boolean
  changes: { at: number; label: string }[]
}

export function findTaraWindows(
  day: Range, rows: TaraTimeline, candidates: number[], goal: TaraGoal,
  durationMinutes: number, timing: TaraTiming, selectedStart?: number,
) {
  const duration = durationMinutes * MINUTE
  if (!Number.isInteger(durationMinutes) || durationMinutes < 1 || !candidates.length
    || duration > day.end - day.start || !rows.vara.some(row => overlaps(bounds(row), day))) return []

  const taras = goal.taras
  const first = selectedStart ?? day.start
  const last = selectedStart ?? day.end - duration
  if (first < day.start || last + duration > day.end || !Number.isFinite(first)) return []
  const personal = rows.nakshatra.filter(row => row.num && overlaps(bounds(row), day)).map(row => {
    const variants = candidates.map(janma => taraFor(janma, row.num!))
    return { ...bounds(row), fits: !taras || variants.every(tara => taras.includes(tara.n)),
      names: [...new Set(variants.map(tara => tara.name))],
      school: variants.filter(tara => tara.schoolAvoid).map(tara => tara.pos) }
  })
  const factors = [
    ...rows.rahu.map(row => ({ ...bounds(row), kind: 'rahu' as const })),
    ...rows.karana.filter(row => row.is_bhadra).map(row => ({ ...bounds(row), kind: 'bhadra' as const })),
    ...rows.abhijit.map(row => ({ ...bounds(row), kind: isWednesdayAbhijit(row, rows.vara) ? 'wednesday' as const : 'abhijit' as const })),
  ].filter(row => overlaps(row, day))
  const rule = eventRuleForGoal(goal)
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
    if (vetoTithi && selectedStart === undefined) {
      previousSignature = ''
      continue
    }
    const avoidTithi = activeTithis.find(row => row.line?.sign === '−')
    const tithiGood = activeTithis.length > 0 && activeTithis.every(row => row.line?.sign === '+')
    const yogaBonus = activeYogas.length > 0 && activeYogas.every(row => row.line?.sign === '+')
    const tithiRank = avoidTithi ? -1 : Number(tithiGood)

    const schoolPositions = [...new Set(personal.filter(matches).flatMap(part => part.school))].sort()
    const warnings = [...new Set(factors.filter(row => row.kind !== 'abhijit' && matches(row)).map(row => row.kind))]
    const signature = JSON.stringify([warnings, schoolPositions, tithiRank, yogaBonus])
    const previous = windows.at(-1)
    if (previous && signature === previousSignature) {
      previous.lastStart = start
      continue
    }
    previousSignature = signature

    const names = personal.find(part => contains(part, start))?.names
    if (!names) continue
    const changes = [
      ...personal.map(part => ({ at: part.start, label: 'Тара · ' + part.names.join(' / ') })),
      ...[...tithis, ...yogas].map(row => ({ at: row.start, label: row.line?.text ?? row.label })),
      ...factors.flatMap(({ start, end, kind }) => [
        { at: start, label: 'Начинается ' + TARA_FACTOR_LABELS[kind] },
        { at: end, label: 'Заканчивается ' + TARA_FACTOR_LABELS[kind] },
      ]),
    ].filter(change => start < change.at && change.at < event.end)
      .sort((a, b) => a.at - b.at)
    const currentTithi = startFactor(tithis, start)
    const currentYoga = startFactor(yogas, start)
    windows.push({
      firstStart: start, lastStart: start, names, schoolPositions, warnings, fits: taras ? fits : null,
      tithi: currentTithi?.label, yoga: currentYoga?.label,
      tithiRule: (vetoTithi ?? avoidTithi ?? currentTithi)?.line, yogaRule: currentYoga?.line,
      veto: Boolean(vetoTithi), tithiRank, yogaBonus,
      caution: Boolean(warnings.length || schoolPositions.length || vetoTithi || avoidTithi),
      beginsInAbhijit: factors.some(row => row.kind === 'abhijit' && contains(row, start)),
      changes,
    })
  }
  return windows.sort((a, b) => Number(a.caution) - Number(b.caution) || b.tithiRank - a.tithiRank
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
    return 'Стоп-титхи по правилу этого события исключила все окна нужной длительности.'
  }
  return 'Подходящие минуты начала есть, но событие указанной длительности не помещается в пределах выбранных условий.'
}
