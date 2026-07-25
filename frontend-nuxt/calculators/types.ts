/** Общие типы калькуляторов. Все номера накшатр — 1..27, знаков — 1..12, домов — 1..12. */

export type Quality = 'good' | 'bad' | 'neutral'
export type Paksha = 'shukla' | 'krishna'

export const WEEKDAYS_RU = [
  'Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота',
] as const
export type WeekdayRu = (typeof WEEKDAYS_RU)[number]

export const PLANETS_RU = [
  'Солнце', 'Луна', 'Марс', 'Меркурий', 'Юпитер', 'Венера', 'Сатурн', 'Раху', 'Кету',
] as const
export type PlanetRu = (typeof PLANETS_RU)[number]

/** Русское имя планеты → slug, которым ключуются placements.json / retrograde.json */
export const PLANET_SLUG: Record<PlanetRu, string> = {
  Солнце: 'surya', Луна: 'chandra', Марс: 'mangala', Меркурий: 'budha',
  Юпитер: 'guru', Венера: 'shukra', Сатурн: 'shani', Раху: 'rahu', Кету: 'ketu',
}

/** Строка вердикта с классом интенсивности — UI сам решает, как красить. */
export interface ScoreLine {
  sign: '+' | '−' | '~' | '⛔'
  weight: number
  text: string
}
