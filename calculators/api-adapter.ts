/** Адаптеры: ответы Vedic Astrology API (FastAPI, PycharmProjects/Vedic) →
 * входы калькуляторов. Ручной ввод из старого HTML заменяется этими функциями.
 *
 * API: POST /api/horoscope (натальная карта), POST /api/panchang (титхи за период),
 *      POST /api/calendar (транзиты Луны по накшатрам).
 */
import { WEEKDAYS_RU, type Paksha, type PlanetRu, type WeekdayRu } from './types'
import type { ChartPlanetInput } from './chart'

/** Часть ответа /api/horoscope, которая нужна калькуляторам. */
export interface HoroscopeResponse {
  nk: { num: number; ru: string; pada: number; lord: string }
  lagna: { sign_num: number }
  planets: Array<{
    name: string        // русское имя («Солнце»…)
    sign_num: number
    house: number
    nakshatra_ru: string
    pada: number
    retro?: boolean
  }>
}

/** Титхи из /api/panchang: num — сквозной 1..30 (16..30 — Кришна-пакша). */
export interface PanchangTithi {
  num: number
  name: string
  paksha: string        // «Шукла» | «Кришна»
  dt_start: string
  dt_end: string
}

/** Джанма-накшатра (1..27) из гороскопа. */
export function janmaFromHoroscope(res: HoroscopeResponse): number {
  return res.nk.num
}

/** Планеты гороскопа → вход analyzeChart. */
export function chartFromHoroscope(res: HoroscopeResponse): {
  lagnaSign: number
  planets: ChartPlanetInput[]
} {
  return {
    lagnaSign: res.lagna.sign_num,
    planets: res.planets.map((p) => ({
      name: p.name as PlanetRu,
      sign: p.sign_num,
      retro: !!p.retro,
    })),
  }
}

/** Сквозной номер титхи 1..30 → номер внутри пакши (1..15) + пакша.
 * 15 = Пурнима (shukla), 30 = Амавасья (krishna → tithi 15). */
export function splitTithi(num30: number): { tithi: number; paksha: Paksha } {
  if (num30 > 15) return { tithi: num30 - 15, paksha: 'krishna' }
  return { tithi: num30, paksha: 'shukla' }
}

export function tithiFromPanchang(t: PanchangTithi): { tithi: number; paksha: Paksha } {
  return splitTithi(t.num)
}

/** День недели по местной дате (0 = воскресенье, как Date.getDay()). */
export function weekdayRu(date: Date): WeekdayRu {
  return WEEKDAYS_RU[date.getDay()]
}
