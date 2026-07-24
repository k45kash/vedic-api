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
import { nakName } from './nakshatra'
import type { Paksha, ScoreLine, WeekdayRu } from './types'

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
    const nm = nakName(input.dayNakNo)
    const good = (ev.good_nakshatras || []).some((x) => nm.includes(x) || x.includes(nm))
    const bad = (ev.avoid_nakshatras || []).some((x) => nm.includes(x) || x.includes(nm))
    if (good) {
      gained += WEIGHTS.nakshatra
      lines.push({ sign: '+', weight: WEIGHTS.nakshatra, text: `Накшатра ${nm} — благоприятна для события` })
    } else if (bad) {
      gained -= WEIGHTS.nakshatra
      vetoCap = Math.min(vetoCap, 40)
      if (!vetoMsg) vetoMsg = 'Избегаемая накшатра для события'
      lines.push({ sign: '⛔', weight: WEIGHTS.nakshatra, text: `Накшатра ${nm} — в списке избегаемых для события (стоп-фактор)` })
    } else {
      lines.push({ sign: '~', weight: 0, text: `Накшатра ${nm} — нейтральна (не в списках)` })
    }
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
  }

  // 3. День недели
  if (input.weekday) {
    total += WEIGHTS.day
    const gd = (ev.good_days || []).some((x) => x.includes(input.weekday!))
    const bd = (ev.avoid_days || []).some((x) => x.includes(input.weekday!))
    if (gd) {
      gained += WEIGHTS.day
      lines.push({ sign: '+', weight: WEIGHTS.day, text: `${input.weekday} — благоприятный день для события` })
    } else if (bd) {
      gained -= WEIGHTS.day
      lines.push({ sign: '−', weight: WEIGHTS.day, text: `${input.weekday} — в списке избегаемых дней` })
    } else {
      lines.push({ sign: '~', weight: 0, text: `${input.weekday} — нейтральный день` })
    }
  }

  // 4. Титхи (с пакшей); Амавасья и рикта — стоп-факторы
  if (input.tithi) {
    total += WEIGHTS.tithi
    const tn = input.tithi
    const paksha = input.paksha || 'shukla'
    let tname = TITHI.tithis[tn - 1]?.name || `титхи ${tn}`
    if (tn === 15) tname = paksha === 'krishna' ? 'Амавасья (новолуние)' : 'Пурнима (полнолуние)'
    const pakshaLabel = paksha === 'krishna' ? 'убывающая' : 'растущая'
    const gt = (ev.good_tithis || []).some((x) => parseInt(x) === tn)
    const bt = (ev.avoid_tithis || []).some((x) => parseInt(x) === tn)

    if (tn === 15 && paksha === 'krishna' && MUNDANE_IDS.includes(ev.id)) {
      gained -= WEIGHTS.tithi
      vetoCap = Math.min(vetoCap, 20)
      vetoMsg = 'Амавасья (новолуние) — стоп-фактор для мирских дел'
      lines.push({ sign: '⛔', weight: WEIGHTS.tithi, text: 'Титхи 15 — Амавасья (новолуние): стоп-фактор, перебивает остальное' })
    } else if ([4, 9, 14].includes(tn) && RIKTA_SENSITIVE_IDS.includes(ev.id)) {
      gained -= WEIGHTS.tithi
      vetoCap = Math.min(vetoCap, 30)
      if (!vetoMsg) vetoMsg = 'Рикта-титхи («пустые руки») — сильно неблагоприятна для начинаний'
      lines.push({ sign: '⛔', weight: WEIGHTS.tithi, text: `Титхи ${tn} (${tname}, ${pakshaLabel}) — рикта («пустые руки»): стоп-фактор для начинаний` })
    } else if (gt) {
      gained += WEIGHTS.tithi
      lines.push({ sign: '+', weight: WEIGHTS.tithi, text: `Титхи ${tn} (${tname}, ${pakshaLabel}) — благоприятна` })
    } else if (bt) {
      gained -= WEIGHTS.tithi
      lines.push({ sign: '−', weight: WEIGHTS.tithi, text: `Титхи ${tn} (${tname}, ${pakshaLabel}) — в списке избегаемых` })
    } else {
      lines.push({ sign: '~', weight: 0, text: `Титхи ${tn} (${tname}, ${pakshaLabel}) — нейтральна` })
    }
  }

  // 5. Йога дня (только бонус — отсутствие в списке не штрафуется)
  if (input.yogaName && input.yogaName.trim()) {
    total += WEIGHTS.yoga
    const y = input.yogaName.trim().toLowerCase()
    const gy = (ev.good_yogas || []).some(
      (x) => x.toLowerCase().includes(y) || y.includes(x.toLowerCase()),
    )
    if (gy) {
      gained += WEIGHTS.yoga
      lines.push({ sign: '+', weight: WEIGHTS.yoga, text: `Йога «${input.yogaName}» — в числе благоприятных` })
    } else {
      lines.push({ sign: '~', weight: 0, text: `Йога «${input.yogaName}» — не в списке благоприятных (проверьте вручную)` })
    }
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
