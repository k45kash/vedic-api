/** Выбор дня для изготовления изделий садханы (работа с металлом планеты).
 *
 * Логика школы: у каждого металла есть основной день (день его планеты) и
 * резервные дни (по дружбе планет). Любой стоп-фактор (неподходящий день,
 * плохая тара, рикта-титхи, Амавасья) полностью исключает день — выбор идёт
 * только из хороших дней. Для доработок (isFinishing) резервные дни
 * оцениваются выше, чем для основного действия.
 */
import SADHANA from '../content/sadhana.json'
import { taraFor } from './tara'
import { nakName } from './nakshatra'
import type { Paksha, WeekdayRu } from './types'

export type MetalDef = (typeof SADHANA)['metals'][number]

export interface SadhanaScoreInput {
  metalId: string        // id из sadhana.json
  janmaNo?: number       // Джанма-накшатра того, для кого изделие
  dayNakNo?: number      // накшатра дня
  weekday?: WeekdayRu
  tithi?: number         // 1..15
  paksha?: Paksha
  isFinishing?: boolean  // false — основное действие, true — доработки
}

export type SadhanaVerdictLevel = 'great' | 'vgood' | 'good' | 'ok'

export type SadhanaScoreResult =
  | { status: 'insufficient' }                      // не хватает входных данных
  | { status: 'excluded'; stops: string[] }         // есть стоп-фактор — день не годится
  | {
      status: 'scored'
      pct: number
      verdict: string
      verdictLevel: SadhanaVerdictLevel
      dayLabel: string                              // «основной день металла» / «резервный день»…
      pluses: string[]
      taraLine: string | null
    }

export function listMetals(): MetalDef[] {
  return SADHANA.metals
}

export function sadhanaScore(input: SadhanaScoreInput): SadhanaScoreResult | null {
  const m = SADHANA.metals.find((x) => x.id === input.metalId)
  if (!m) return null

  const stops: string[] = []
  const pluses: string[] = []
  const haveTara = input.janmaNo != null && input.dayNakNo != null

  // 1. День недели относительно металла: основной / резерв / не подходит
  let base: number | null = null
  let dayLabel = ''
  if (input.weekday) {
    if (input.weekday === m.main_day) {
      base = 100
      dayLabel = 'основной день металла'
    } else {
      const res = (m.reserve || []).find((r) => r.day === input.weekday)
      if (res) {
        const crisis = res.note.includes('крайн')
        if (input.isFinishing) {
          base = crisis ? 80 : 90
          dayLabel = 'резервный день (для доработок — полноценный)'
        } else {
          base = crisis ? 55 : 75
          dayLabel = crisis ? 'крайний резерв' : 'резервный день'
        }
      } else {
        stops.push(`День ${input.weekday} не подходит этому металлу`)
      }
    }
  }

  // 2. Тара-бала: Джанма(1), Випат(3), Пратьяри(5), Наидхана(7) и 27-я — исключают
  if (haveTara) {
    const t = taraFor(input.janmaNo!, input.dayNakNo!)
    if (t.n === 1) stops.push('Джанма-тара (спорная) — исключается')
    else if (t.n === 3) stops.push('Випат-тара (потери) — исключается')
    else if (t.n === 5) stops.push('Пратьяри-тара (препятствия) — исключается')
    else if (t.n === 7) stops.push('Наидхана-тара (разрушение) — исключается')
    if (t.schoolAvoid) stops.push('27-я накшатра от Джанмы — исключается (правило школы)')
    if ([2, 4, 6, 8, 9].includes(t.n)) pluses.push(`Тара ${t.name} — благоприятна лично человеку`)
  }

  // 3. Титхи: рикта (4, 9, 14) и Амавасья — исключают; часть титх — бонус
  if (input.tithi) {
    const tn = input.tithi
    const paksha = input.paksha || 'shukla'
    if ([4, 9, 14].includes(tn)) stops.push(`Рикта-титхи ${tn} («пустые руки») — исключается`)
    else if (tn === 15 && paksha === 'krishna') stops.push('Амавасья (новолуние) — исключается')
    else if ([2, 3, 5, 7, 10, 11, 13].includes(tn) || (tn === 15 && paksha === 'shukla')) {
      pluses.push(`Хорошие лунные сутки (${tn})`)
    }
  }

  if (base === null && !input.weekday) return { status: 'insufficient' }
  if (stops.length) return { status: 'excluded', stops }

  // 4. Процент: база дня + бонусы (бонусы у сильной базы весят меньше — потолок 100)
  if (base === null) base = 100
  let pct: number
  if (base >= 90) {
    pct = Math.min(100, base + pluses.length * 3)
    if (base === 100) pct = Math.min(100, 90 + pluses.length * 5)
  } else {
    pct = Math.min(100, base + Math.min(pluses.length * 8, 18))
  }

  let verdict: string, verdictLevel: SadhanaVerdictLevel
  if (pct >= 90) { verdict = 'Отлично'; verdictLevel = 'great' }
  else if (pct >= 75) { verdict = 'Очень хорошо'; verdictLevel = 'vgood' }
  else if (pct >= 60) { verdict = 'Хорошо'; verdictLevel = 'good' }
  else { verdict = 'Приемлемо'; verdictLevel = 'ok' }

  let taraLine: string | null = null
  if (haveTara) {
    const t = taraFor(input.janmaNo!, input.dayNakNo!)
    taraLine = `Накшатра ${nakName(input.dayNakNo!)} → ${t.n}-я тара (${t.name})`
  }

  return { status: 'scored', pct, verdict, verdictLevel, dayLabel, pluses, taraLine }
}
