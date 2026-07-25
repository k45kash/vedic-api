// Единая точка входа в calculators/ и content/ для страниц кабинета.
// Страницы НЕ должны импортировать '~calc'/'~content' напрямую — иначе легко
// затащить в бандл 300-килобайтный JSON одним неосторожным импортом.
//
// Политика размеров (см. docs/HANDOFF.md §2 «Важно про размер»):
//   СТАТИЧЕСКИ  — модули, чьи JSON суммарно небольшие:
//     types (0), nakshatra (~1 КБ), tara (~19 КБ), sadhana (~7 КБ),
//     api-adapter (0), chart (signs 17 + houses 30 + placements 53 ≈ 100 КБ).
//   ЛЕНИВО (dynamic import → отдельный чанк):
//     kuta         → nakshatras.json          279 КБ
//     event-picker → events_muhurta.json 101 КБ + tithi.json 27 КБ
//     плюс «сырые» крупные справочники контента: planet_in_nakshatra 293 КБ,
//     nakshatras 279 КБ, planet_stories 134 КБ, padas 128 КБ, yogakarma 79 КБ,
//     muhurta30 55 КБ, panchanga 28 КБ, glossary 21 КБ.

import type { ChartPlanetRow } from '~calc/chart'
import type { AshtaKutaResult } from '~calc/kuta'
import type { EventDef, EventScoreInput, EventScoreResult } from '~calc/event-picker'

// ─── Статические реэкспорты ─────────────────────────────────────────────────

export {
  nakshatraFromLongitude, nakName, nakLabel, rulerOf, isGandantaNakshatra,
  NAK_NAMES, NAK_SIZE,
} from '~calc/nakshatra'
export { taraFor, taraFavorable, taraChakra, TARA_TABLE } from '~calc/tara'
export { analyzeChart, houseForSign, signForHouse, dignity, planetsInHouse } from '~calc/chart'
export { sadhanaScore, listMetals } from '~calc/sadhana'
export { janmaFromHoroscope, chartFromHoroscope, splitTithi, tithiFromPanchang, weekdayRu } from '~calc/api-adapter'
export { WEEKDAYS_RU, PLANETS_RU, PLANET_SLUG } from '~calc/types'

export type {
  ChartPlanetRow, ChartPlanetInput, Dignity, SignDef, HouseDef,
} from '~calc/chart'
export type { TaraResult, TaraChakraCell, TaraStrength } from '~calc/tara'
export type { NakshatraPosition } from '~calc/nakshatra'
export type { AshtaKutaResult, KutaFactor } from '~calc/kuta'
export type { EventDef, EventScoreInput, EventScoreResult, EventVerdictLevel } from '~calc/event-picker'
export type { SadhanaScoreInput, SadhanaScoreResult, MetalDef } from '~calc/sadhana'
export type { Paksha, Quality, PlanetRu, WeekdayRu, ScoreLine } from '~calc/types'

// Нужны внутри композабла — импортируем в дополнение к реэкспорту.
import { analyzeChart } from '~calc/chart'
import { chartFromHoroscope } from '~calc/api-adapter'
import { taraFor, taraChakra } from '~calc/tara'

// ─── Ленивые обёртки над «тяжёлыми» калькуляторами ──────────────────────────
// Возвращают Promise: модуль подгружается отдельным чанком при первом вызове,
// дальше отдаётся из кэша модулей браузера.

/** Ашта-кута (21 из 36 баллов). Тянет nakshatras.json (279 КБ). */
export async function ashtaKutaPartial(brideNo: number, groomNo: number): Promise<AshtaKutaResult> {
  const m = await import('~calc/kuta')
  return m.ashtaKutaPartial(brideNo, groomNo)
}

/** Список 33 событий мухурты. Тянет events_muhurta.json (101 КБ). */
export async function listEvents(): Promise<EventDef[]> {
  const m = await import('~calc/event-picker')
  return m.listEvents()
}

/** Балльная оценка дня под событие. Тянет events_muhurta.json + tithi.json. */
export async function scoreEvent(input: EventScoreInput): Promise<EventScoreResult | null> {
  const m = await import('~calc/event-picker')
  return m.scoreEvent(input)
}

// ─── Ленивые загрузчики крупных JSON из content/ ────────────────────────────
// Каждый — отдельный чанк. Импорт c { default: … } потому, что Vite отдаёт
// JSON как ES-модуль с default-экспортом.

const json = <T>(p: Promise<{ default: T }>): Promise<T> => p.then((m) => m.default)

/** 27 накшатр, ~60 полей каждая — 279 КБ. */
export const loadNakshatras = () => json<any[]>(import('~content/nakshatras.json'))
/** 243 трактовки «планета в накшатре» — 293 КБ. */
export const loadPlanetInNakshatra = () => json<any>(import('~content/planet_in_nakshatra.json'))
/** 108 пад — 128 КБ. */
export const loadPadas = () => json<any>(import('~content/padas.json'))
/** 9 катх планет с мантрами и 108 именами — 134 КБ. */
export const loadPlanetStories = () => json<any>(import('~content/planet_stories.json'))
/** Йога-карма — 79 КБ. */
export const loadYogakarma = () => json<any>(import('~content/yogakarma.json'))
/** 30 мухурт — 55 КБ. */
export const loadMuhurta30 = () => json<any>(import('~content/muhurta30.json'))
/** Панчанга: пять элементов и стоп-факторы — 28 КБ. */
export const loadPanchanga = () => json<any>(import('~content/panchanga.json'))
/** 15 титх — 27 КБ. */
export const loadTithi = () => json<any>(import('~content/tithi.json'))
/** 33 события мухурты — 101 КБ. */
export const loadEventsMuhurta = () => json<any>(import('~content/events_muhurta.json'))
/** Глоссарий, 14 групп / 38 терминов — 21 КБ. */
export const loadGlossary = () => json<any>(import('~content/glossary.json'))
/** 17 дисклеймеров достоверности — 8 КБ. */
export const loadDisclaimers = () => json<any>(import('~content/disclaimers.json'))
/** Тексты интерфейса — 15 КБ. */
export const loadUiTexts = () => json<any>(import('~content/ui_texts.json'))
/** Ретроградность планет — 11 КБ. */
export const loadRetrograde = () => json<any>(import('~content/retrograde.json'))
/** Геометрия SVG-карты — 2,6 КБ. */
export const loadChartGeometry = () => json<any>(import('~content/chart_geometry.json'))

// ─── Композабл: расчёты поверх текущего профиля рождения ────────────────────

export function useJyotish() {
  const { horoscope, hasProfile, lagnaReliable, moonUncertain } = useBirthProfile()

  /** Джанма-накшатра (номер накшатры Луны, 1..27). null — профиля/ответа нет. */
  const janmaNakshatra = computed<number | null>(() => horoscope.value?.nk.num ?? null)
  const janmaNakshatraName = computed<string | null>(() => horoscope.value?.nk.ru ?? null)
  const janmaPada = computed<number | null>(() => horoscope.value?.nk.pada ?? null)

  /** Знак Лагны 1..12. Осмысленно только при lagnaReliable === true. */
  const lagnaSign = computed<number | null>(() => horoscope.value?.lagna.sign_num ?? null)

  /** Полный разбор карты: планеты по знакам и домам + трактовки.
   * ВАЖНО: поля house / houseData / inHouseText производны от Лагны, поэтому
   * при lagnaReliable === false они недостоверны — UI обязан их скрыть.
   * Знак, достоинство и inSignText остаются валидными (кроме Луны, которая
   * за сутки может сменить знак). */
  const chart = computed<ChartPlanetRow[] | null>(() => {
    const h = horoscope.value
    if (!h) return null
    // HoroscopeResult структурно совместим с HoroscopeResponse адаптера.
    const { lagnaSign: sign, planets } = chartFromHoroscope(h)
    return analyzeChart(sign, planets)
  })

  /** Наватара-чакра (27 накшатр от Джанмы) для текущего профиля. */
  const taraChakraForProfile = computed(() => {
    const j = janmaNakshatra.value
    return j ? taraChakra(j) : null
  })

  /** Тара-бала дня: накшатра дня (1..27) → результат относительно Джанмы. */
  function taraForDay(dayNakNo: number) {
    const j = janmaNakshatra.value
    return j ? taraFor(j, dayNakNo) : null
  }

  return {
    horoscope,
    hasProfile,
    lagnaReliable,
    moonUncertain,
    janmaNakshatra,
    janmaNakshatraName,
    janmaPada,
    lagnaSign,
    chart,
    taraChakraForProfile,
    taraForDay,
  }
}
