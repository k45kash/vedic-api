// Общие типы экрана «Карта». Вынесены в отдельный модуль, потому что
// <script setup> не умеет экспортировать типы, а страница и оба компонента
// должны говорить об одних и тех же структурах.

export type DignityKey = 'exalted' | 'debilitated' | 'own' | null

/** Метка планеты внутри клетки карты. */
export interface WheelPlanet {
  name: string
  /** Короткая метка: «Са», «Ра» (из исходника коллеги, CF_PL_SHORT). */
  short: string
  retro?: boolean
  stationary?: boolean
  dignity?: DignityKey
}

/** Одна клетка карты: дом, стоящий в нём знак и планеты. */
export interface WheelHouse {
  /** Номер дома 1..12 от выбранной точки отсчёта (Лагна или Луна). */
  house: number
  /** Знак 1..12 (Овен = 1). */
  sign: number
  /** Короткое имя знака: «Скорп». */
  signShort: string
  /** Группа дома из houses.json: Кендра / Трикона / Духстана / Упачая. */
  group?: string | null
  planets: WheelPlanet[]
}

/** Строка таблицы положений. */
export interface PositionRow {
  planet: string
  glyph: string
  signRu: string
  signShort: string
  /** Дом 1..12 от точки отсчёта; null — не рассчитывается. */
  house: number | null
  nakshatra: string
  pada: number
  nakLord: string
  dignity: DignityKey
  retro: boolean
  stationary: boolean
  /** «21°58'22"» — как отдаёт API. */
  degDms: string
  speed: number | null
}
