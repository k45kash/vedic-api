/** Подбор события (мухурта): весовая оценка дня для конкретного дела.
 *
 * Баллы: тара 4, накшатра 3, титхи 2, день недели 2, йога 1.
 * Стоп-факторы (избегаемая накшатра, Амавасья, рикта-титхи) не просто вычитают
 * баллы, а ограничивают итоговый процент сверху (vetoCap).
 */
import EVENTS from '../content/events_muhurta.json'
import TITHI from '../content/tithi.json'
import WEIGHTS from '../content/picker_weights.json'
import { taraFor } from './tara'
import { nakName, isGandantaNakshatra } from './nakshatra'
import type { Paksha, ScoreLine, WeekdayRu } from './types'

/** Совпадает ли запись справочника титх с текущей титхи.
 *
 * Записи в `events_muhurta.json` бывают двух видов: номер («11») и название
 * («Амавасья», «Пурнима (по ряду школ)»). Раньше сверка шла через `parseInt`,
 * из-за чего словесные записи молча отбрасывались — а это ровно две самые
 * значимые титхи, и встречаются они в 42 местах. Например для стрижки
 * Амавасья указана в `avoid_tithis`, но день всё равно получал «отличное окно».
 *
 * Новолуние и полнолуние — это одна и та же 15-я титхи, различает их пакша.
 */
function tithiMatches(entry: string, tn: number, paksha: Paksha): boolean {
  const s = String(entry).trim().toLowerCase()
  const num = parseInt(s, 10)
  if (!Number.isNaN(num)) return num === tn
  if (s.includes('амавас')) return tn === 15 && paksha === 'krishna'
  if (s.includes('пурним')) return tn === 15 && paksha === 'shukla'

  // Категория титхи («рикта», «Нанда-титхи 1,6,11 …»). Состав категорий не
  // выдумываем и не держим таблицей в коде — берём поле `cat` из tithi.json.
  const cat = tithiCategory(s)
  if (cat) return cat.has(tn)

  // Запись может перечислять номера прямо в тексте — тогда читаем их все.
  const nums = s.match(/\d+/g)
  if (nums) return nums.some((n) => Number(n) === tn)

  return false
}

/** Номера титх категории («Нанда», «Рикта», …) по полю `cat` из tithi.json.
 * Собирается один раз при первом обращении. */
let tithiCats: Map<string, Set<number>> | null = null
function tithiCategory(entry: string): Set<number> | null {
  if (!tithiCats) {
    tithiCats = new Map()
    for (const t of ((TITHI as any)?.tithis ?? []) as Array<{ n?: number; cat?: string }>) {
      const key = String(t?.cat ?? '').trim().toLowerCase()
      const n = Number(t?.n)
      if (!key || !Number.isFinite(n)) continue
      if (!tithiCats.has(key)) tithiCats.set(key, new Set())
      tithiCats.get(key)!.add(n)
    }
  }
  for (const [key, nums] of tithiCats) {
    if (entry.includes(key)) return nums
  }
  return null
}

/** Совпадает ли запись справочника накшатр с накшатрой дня.
 *
 * Кроме имён в списках встречается категория «гандантовые» — стыки водных и
 * огненных знаков. Она тоже отбрасывалась: подстрока не совпадает ни с одним
 * названием. Разворачиваем её через уже готовую `isGandantaNakshatra`.
 */
function nakshatraMatches(entry: string, nakNo: number, nakNm: string): boolean {
  const s = String(entry).trim().toLowerCase()
  if (s.includes('гандант')) return isGandantaNakshatra(nakNo)
  return nakNm.includes(entry) || entry.includes(nakNm)
}

export type EventDef = (typeof EVENTS)['events'][number]

export interface EventScoreInput {
  eventId: string        // id из events_muhurta.json (wedding, business…)
  janmaNo?: number       // Джанма-накшатра 1..27 (для Тара-балы)
  dayNakNo?: number      // накшатра дня 1..27
  weekday?: WeekdayRu
  tithi?: number         // 1..15 (номер внутри пакши)
  paksha?: Paksha
  yogaName?: string      // название йоги дня (необязательно)
}

export type EventVerdictLevel = 'great' | 'good' | 'ok' | 'weak'

export interface EventScoreResult {
  pct: number                 // 0..100 итоговая благоприятность
  verdict: string
  verdictLevel: EventVerdictLevel
  lines: ScoreLine[]          // построчный разбор факторов
  vetoMsg: string | null      // активный стоп-фактор
  gained: number
  total: number               // сумма весов заполненных факторов
  event: EventDef
}

/** События, для которых Амавасья — жёсткий стоп. */
const MUNDANE_IDS = ['wedding', 'house', 'travel', 'business', 'vehicle', 'contract',
  'construction', 'namakarana', 'conception', 'education', 'finance']

/** События, для которых рикта-титхи (4, 9, 14) — жёсткий стоп. */
const RIKTA_SENSITIVE_IDS = ['wedding', 'house', 'business', 'education', 'namakarana',
  'conception', 'contract']

export function listEvents(): EventDef[] {
  return EVENTS.events
}

export function evaluateEventTithi(ev: EventDef, tn: number, paksha: Paksha): {
  line: ScoreLine; cap: number; veto?: string
} {
  let tname = TITHI.tithis[tn - 1]?.name || `титхи ${tn}`
  if (tn === 15) tname = paksha === 'krishna' ? 'Амавасья (новолуние)' : 'Пурнима (полнолуние)'
  const pakshaLabel = paksha === 'krishna' ? 'убывающая' : 'растущая'
  const gt = (ev.good_tithis || []).some((x) => tithiMatches(x, tn, paksha))
  const bt = (ev.avoid_tithis || []).some((x) => tithiMatches(x, tn, paksha))

  const weight = WEIGHTS.tithi
  if (tn === 15 && paksha === 'krishna' && MUNDANE_IDS.includes(ev.id)) {
    return {
      cap: 20, veto: 'Амавасья (новолуние) — стоп-фактор для мирских дел',
      line: { sign: '⛔', weight, text: 'Титхи 15 — Амавасья (новолуние): стоп-фактор, перебивает остальное' },
    }
  }
  const label = `Титхи ${tn} (${tname}, ${pakshaLabel})`
  if ([4, 9, 14].includes(tn) && RIKTA_SENSITIVE_IDS.includes(ev.id)) {
    return {
      cap: 30, veto: 'Рикта-титхи («пустые руки») — сильно неблагоприятна для начинаний',
      line: { sign: '⛔', weight, text: `${label} — рикта («пустые руки»): стоп-фактор для начинаний` },
    }
  }
  if (gt) return { cap: 100, line: { sign: '+', weight, text: `${label} — благоприятна` } }
  if (bt) return { cap: 100, line: { sign: '−', weight, text: `${label} — в списке избегаемых` } }
  return { cap: 100, line: { sign: '~', weight: 0, text: `${label} — нейтральна` } }
}

export function evaluateEventYoga(ev: EventDef, yogaName: string): ScoreLine {
  const normalize = (name: string) => name.trim().toLowerCase()
    .replace(/\s*\([^)]*\)$/, '').replace(/[-– ]йога$/, '').trim()
  const name = normalize(yogaName)
  return (ev.good_yogas || []).some(entry => normalize(entry) === name)
    ? { sign: '+', weight: WEIGHTS.yoga, text: `Йога «${yogaName}» — в числе благоприятных` }
    : { sign: '~', weight: 0, text: `Йога «${yogaName}» — не в списке благоприятных (проверьте вручную)` }
}

export function evaluateEventNakshatra(ev: EventDef, nakNo: number): ScoreLine {
  const name = nakName(nakNo)
  const weight = WEIGHTS.nakshatra
  if (ev.good_nakshatras?.some(entry => nakshatraMatches(entry, nakNo, name))) {
    return { sign: '+', weight, text: `Накшатра ${name} — благоприятна для события` }
  }
  if (ev.avoid_nakshatras?.some(entry => nakshatraMatches(entry, nakNo, name))) {
    return { sign: '⛔', weight, text: `Накшатра ${name} — в списке избегаемых для события (стоп-фактор)` }
  }
  return { sign: '~', weight: 0, text: `Накшатра ${name} — нейтральна (не в списках)` }
}

export function evaluateEventWeekday(ev: EventDef, weekday: WeekdayRu): ScoreLine {
  const weight = WEIGHTS.day
  if (ev.good_days?.some(entry => entry.includes(weekday))) {
    return { sign: '+', weight, text: `${weekday} — благоприятный день для события` }
  }
  if (ev.avoid_days?.some(entry => entry.includes(weekday))) {
    return { sign: '−', weight, text: `${weekday} — в списке избегаемых дней` }
  }
  return { sign: '~', weight: 0, text: `${weekday} — нейтральный день` }
}

export function scoreEvent(input: EventScoreInput): EventScoreResult | null {
  const ev = EVENTS.events.find((e) => e.id === input.eventId)
  if (!ev) return null

  let gained = 0
  let total = 0
  let vetoCap = 100
  let vetoMsg: string | null = null
  const lines: ScoreLine[] = []

  // 1. Накшатра дня — подходит ли делу
  if (input.dayNakNo) {
    total += WEIGHTS.nakshatra
    const line = evaluateEventNakshatra(ev, input.dayNakNo)
    if (line.sign === '+') gained += line.weight
    if (line.sign === '⛔') {
      gained -= line.weight
      vetoCap = Math.min(vetoCap, 40)
      vetoMsg = 'Избегаемая накшатра для события'
    }
    lines.push(line)
  }

  // 2. Тара-бала — лично для человека
  if (input.janmaNo && input.dayNakNo) {
    total += WEIGHTS.tara
    const t = taraFor(input.janmaNo, input.dayNakNo)
    if (t.quality === 'good') {
      gained += WEIGHTS.tara
      lines.push({ sign: '+', weight: WEIGHTS.tara, text: `Тара-бала: ${t.n}-я (${t.name}) — благоприятна лично вам` })
    } else if (t.quality === 'bad') {
      gained -= WEIGHTS.tara
      lines.push({ sign: '−', weight: WEIGHTS.tara, text: `Тара-бала: ${t.n}-я (${t.name}) — неблагоприятна лично вам` })
    } else {
      lines.push({ sign: '~', weight: 0, text: `Тара-бала: ${t.n}-я (${t.name}) — смешанная` })
    }
    if (t.schoolAvoid) {
      lines.push({ sign: '~', weight: 0, text: `Тара-бала: ${t.pos}-я позиция от рождения. По курсу важное начинание лучше отложить.` })
    }
  }

  // 3. День недели
  if (input.weekday) {
    total += WEIGHTS.day
    const line = evaluateEventWeekday(ev, input.weekday)
    if (line.sign === '+') gained += line.weight
    if (line.sign === '−') gained -= line.weight
    lines.push(line)
  }

  if (input.tithi) {
    total += WEIGHTS.tithi
    const { line, cap, veto } = evaluateEventTithi(ev, input.tithi, input.paksha || 'shukla')
    if (line.sign === '+') gained += WEIGHTS.tithi
    if (line.sign === '−' || line.sign === '⛔') gained -= WEIGHTS.tithi
    vetoCap = Math.min(vetoCap, cap)
    if (veto && (cap === 20 || !vetoMsg)) vetoMsg = veto
    lines.push(line)
  }

  if (input.yogaName?.trim()) {
    total += WEIGHTS.yoga
    const yoga = evaluateEventYoga(ev, input.yogaName)
    if (yoga.sign === '+') gained += WEIGHTS.yoga
    lines.push(yoga)
  }

  if (total === 0) return null

  let pct = Math.round((Math.max(0, gained) / total) * 100)
  if (pct > vetoCap) pct = vetoCap

  let verdict: string, verdictLevel: EventVerdictLevel
  if (pct >= 75) { verdict = 'Отличное окно'; verdictLevel = 'great' }
  else if (pct >= 55) { verdict = 'Хорошее окно'; verdictLevel = 'good' }
  else if (pct >= 40) { verdict = 'Приемлемо, с компромиссом'; verdictLevel = 'ok' }
  else { verdict = 'Слабое окно — лучше поискать другой день'; verdictLevel = 'weak' }

  return { pct, verdict, verdictLevel, lines, vetoMsg, gained, total, event: ev }
}
