/** Карта «дома и знаки» (Whole Sign): раскладка планет по домам от Лагны
 * и сборка трактовок из справочных данных.
 */
import SIGNS from '../content/signs.json'
import HOUSES from '../content/houses.json'
import PLACEMENTS from '../content/placements.json'
import { PLANET_SLUG, PLANETS_RU, type PlanetRu } from './types'

export type SignDef = (typeof SIGNS)['signs'][number]
export type HouseDef = (typeof HOUSES)['houses'][number]

export type Dignity = 'exalted' | 'debilitated' | 'own' | null

export interface ChartPlanetInput {
  name: PlanetRu
  sign: number          // знак 1..12 (Овен = 1)
  retro?: boolean
}

export interface ChartPlanetRow {
  planet: PlanetRu
  sign: number
  signData: SignDef
  house: number         // 1..12 от Лагны (Whole Sign)
  houseData: HouseDef
  dignity: Dignity
  retro: boolean
  inHouseText: string   // трактовка «планета в доме» из placements
  inSignText: string    // трактовка «планета в знаке» из placements
}

/** Дом, в котором стоит знак, при данной Лагне (Whole Sign). */
export function houseForSign(lagnaSign: number, signNo: number): number {
  return ((signNo - lagnaSign + 12) % 12) + 1
}

/** Знак, попадающий в данный дом, при данной Лагне (Whole Sign). */
export function signForHouse(lagnaSign: number, houseNo: number): number {
  return ((lagnaSign - 1 + houseNo - 1) % 12) + 1
}

/** Достоинство планеты в знаке: экзальтация / падение / свой знак.
 * В signs.json поля exalt/debil — строки вида «Солнце (10°)», поэтому поиск подстрокой. */
export function dignity(planet: PlanetRu, signNo: number): Dignity {
  const s = SIGNS.signs[signNo - 1]
  if ((s.exalt || '').includes(planet)) return 'exalted'
  if ((s.debil || '').includes(planet)) return 'debilitated'
  if (s.ruler === planet) return 'own'
  return null
}

/** Полный разбор карты: планеты по знакам + Лагна → дома, достоинства, трактовки. */
export function analyzeChart(lagnaSign: number, planets: ChartPlanetInput[]): ChartPlanetRow[] {
  const houseBy = new Map(HOUSES.houses.map((h) => [h.n, h]))
  const order = PLANETS_RU as readonly PlanetRu[]
  return [...planets]
    .sort((a, b) => order.indexOf(a.name) - order.indexOf(b.name))
    .map((p) => {
      const houseNo = houseForSign(lagnaSign, p.sign)
      const slug = PLANET_SLUG[p.name]
      return {
        planet: p.name,
        sign: p.sign,
        signData: SIGNS.signs[p.sign - 1],
        house: houseNo,
        houseData: houseBy.get(houseNo)!,
        dignity: dignity(p.name, p.sign),
        retro: !!p.retro,
        inHouseText: (PLACEMENTS.houses as Record<string, string[]>)[slug]?.[houseNo - 1] ?? '',
        inSignText: (PLACEMENTS.signs as Record<string, string[]>)[slug]?.[p.sign - 1] ?? '',
      }
    })
}

/** Планеты, стоящие в данном доме. */
export function planetsInHouse(
  lagnaSign: number,
  planets: ChartPlanetInput[],
  houseNo: number,
): ChartPlanetInput[] {
  return planets.filter((p) => houseForSign(lagnaSign, p.sign) === houseNo)
}
