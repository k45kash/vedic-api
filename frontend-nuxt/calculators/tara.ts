/** Тара-бала: личная благоприятность дня по Джанма-накшатре и накшатре дня.
 *
 * Метод: позиция накшатры дня от Джанмы (1..27) циклами по 9 тар.
 * Неблагоприятные тары (3 Випат, 5 Пратьяри, 7 Наидхана) ослабевают от группы к группе.
 */
import TARA from '../content/tara_bala.json'
import TARA_SCHOOL from '../content/tara_school.json'
import TARA_DANA from '../content/tara_dana.json'
import type { Quality } from './types'
import { nakName, rulerOf } from './nakshatra'

export type TaraStrength = 'full' | 'partial' | 'mild'

export interface TaraResult {
  n: number               // номер тары 1..9
  name: string            // Джанма, Сампат, Випат…
  quality: Quality
  short: string           // краткое значение («беда, потери»)
  full: string            // развёрнутое описание
  pos: number             // 1..27 — позиция накшатры дня от Джанмы
  group: 1 | 2 | 3        // Джанмаркша (1–9) / Кармаркша (10–18) / Адханаркша (19–27)
  strength: TaraStrength  // сила негатива: full — весь день, partial — ~8ч, mild — почти нейтрально
  schoolAvoid: boolean    // правило школы: 27-я накшатра от Джанмы — избегать
  school?: (typeof TARA_SCHOOL)[keyof typeof TARA_SCHOOL] // детали школы (theme, energy, good, bad…)
}

/** Тара дня. Входы — номера накшатр 1..27 (janma — натальная Луна, day — транзитная). */
export function taraFor(janmaNo: number, dayNo: number): TaraResult {
  const diff = (((dayNo - janmaNo) % 27) + 27) % 27 // 0..26
  const pos = diff + 1
  const t = diff % 9
  const group = (pos <= 9 ? 1 : pos <= 18 ? 2 : 3) as 1 | 2 | 3
  const base = TARA[t]

  let strength: TaraStrength = 'full'
  if (base.q === 'bad') {
    strength = group === 1 ? 'full' : group === 2 ? 'partial' : 'mild'
  }

  return {
    n: base.n,
    name: base.name,
    quality: base.q as Quality,
    short: base.d,
    full: base.full,
    pos,
    group,
    strength,
    schoolAvoid: pos === 27,
    school: (TARA_SCHOOL as Record<string, any>)[String(base.n)],
  }
}

/** Благоприятна ли тара в направлении x→y (для Тара-куты считается в обе стороны). */
export function taraFavorable(fromNo: number, toNo: number): boolean {
  const diff = (((toNo - fromNo) % 27) + 27) % 27
  return TARA[diff % 9].q !== 'bad'
}

export interface TaraChakraCell {
  pos: number          // 1..27 от Джанмы
  nakNo: number        // 1..27
  nakName: string
  taraN: number        // 1..9
  taraName: string
  quality: Quality
  ruler: string        // управитель накшатры (Вимшоттари)
  dana: string         // традиционное пожертвование (упайя) для смягчения
  group: 1 | 2 | 3
  schoolAvoid: boolean
}

/** Навата́ра-чакра: все 27 накшатр от Джанмы с тарами (для таблицы 9×3). */
export function taraChakra(janmaNo: number): TaraChakraCell[] {
  const cells: TaraChakraCell[] = []
  for (let pos = 1; pos <= 27; pos++) {
    const nakNo = ((janmaNo - 1 + pos - 1) % 27) + 1
    const t = (pos - 1) % 9
    cells.push({
      pos,
      nakNo,
      nakName: nakName(nakNo),
      taraN: TARA[t].n,
      taraName: TARA[t].name,
      quality: TARA[t].q as Quality,
      ruler: rulerOf(nakNo),
      dana: TARA_DANA[t],
      group: (pos <= 9 ? 1 : pos <= 18 ? 2 : 3) as 1 | 2 | 3,
      schoolAvoid: pos === 27,
    })
  }
  return cells
}

export { TARA as TARA_TABLE }
