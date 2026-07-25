// Стоп-факторы дня: Раху-калам, Гулика-калам (Мандикалам), Ямаганда-калам.
//
// В content/panchanga.json лежат только ОПИСАНИЯ этих периодов, правил расчёта
// времени там нет — поэтому расчёт живёт здесь.
//
// МЕТОД (наиболее распространённый). Светлое время суток — от восхода до
// заката — делится на 8 равных частей (при «идеальных» 6:00–18:00 это ровно
// 1 ч 30 мин). Каждому стоп-фактору на каждый день недели соответствует своя
// по счёту часть.
//
// ИСТОЧНИКИ (сверено вручную в июле 2026):
//
//  1) Prokerala, «Rahu Kalam» — https://www.prokerala.com/astrology/rahukalam/
//     «Rahu kaal is calculated by dividing the number of hours between
//     astrological sunrise & sunset by 8». Их таблица при восходе 6:00 и
//     закате 18:00 (часть = 1,5 ч):
//        Вс 16:30–18:00 → 8-я   Пн 07:30–09:00 → 2-я   Вт 15:00–16:30 → 7-я
//        Ср 12:00–13:30 → 5-я   Чт 13:30–15:00 → 6-я   Пт 10:30–12:00 → 4-я
//        Сб 09:00–10:30 → 3-я
//
//  2) AnytimeAstro, «Tuesday Rahu Kalam Time, Yamagandam And Gulika Kaal
//     Timing» — https://www.anytimeastro.com/blog/astrology/tuesday-rahukalam-and-yamagandam-time/
//     Вторник: Раху 15:00–16:30 (7-я), Ямагандам 09:00–10:30 (3-я),
//     Гулика 12:00–13:30 (5-я) — совпадает с таблицами ниже.
//
//  3) Shubh Panchang, «Rahu Kaal, Yamagandam and Gulika Kaal explained» —
//     https://shubhpanchang.com/blog/rahu-kaal-yamagandam-and-gulika-kaal-explained
//     Подтверждает деление светлого дня на 8 частей и «свою» часть на каждый
//     день недели; для Гулики — обратный отсчёт от субботы (Сб 1-я … Вс 7-я).
//
// РАСХОЖДЕНИЯ ШКОЛ, которые UI обязан пометить честно:
//   • часть традиций отсчитывает не от астрономического восхода, а от
//     «панчанга-восхода» (центр диска / с поправкой на рефракцию);
//   • для Гулики встречается и ночная схема (деление тёмного времени);
//   • Ямаганда местами называется Ямагхата и считается иначе.
// Поэтому в интерфейсе рядом с расчётом стоит дисклеймер «по распространённому
// методу», а не «канон».

/** Номер части (1..8) светлого дня по дню недели, индекс = Date.getDay() (0 = Вс). */
const PART_BY_WEEKDAY = {
  rahu: [8, 2, 7, 5, 6, 4, 3],
  yamaganda: [5, 4, 3, 2, 1, 7, 6],
  gulika: [7, 6, 5, 4, 3, 2, 1],
} as const

export type KalamKey = keyof typeof PART_BY_WEEKDAY

export interface KalamPeriod {
  key: KalamKey
  /** Отображаемое имя периода. */
  name: string
  /** Номер части светлого дня, 1..8. */
  part: number
  start: Date
  end: Date
}

const NAMES: Record<KalamKey, string> = {
  rahu: 'Раху-калам',
  gulika: 'Гулика-калам',
  yamaganda: 'Ямаганда-калам',
}

/** Порядок вывода: сперва самый известный стоп-фактор. */
const ORDER: KalamKey[] = ['rahu', 'gulika', 'yamaganda']

/**
 * Три ежедневных стоп-фактора для конкретных восхода и заката.
 * sunrise / sunset — Date в ЛОКАЛЬНОМ времени места расчёта (именно так их
 * отдаёт /api/panchang: строки вида «2026-07-25T04:21:58» без смещения).
 * Возвращает пустой массив, если даты некорректны или закат не позже восхода.
 */
export function dayKalams(sunrise: Date, sunset: Date): KalamPeriod[] {
  const from = sunrise.getTime()
  const to = sunset.getTime()
  if (!Number.isFinite(from) || !Number.isFinite(to) || to <= from) return []

  const part = (to - from) / 8
  const wd = sunrise.getDay() // 0 = воскресенье, как в таблицах выше

  return ORDER.map((key) => {
    const n = PART_BY_WEEKDAY[key][wd]
    return {
      key,
      name: NAMES[key],
      part: n,
      start: new Date(from + (n - 1) * part),
      end: new Date(from + n * part),
    }
  })
}

/** Идёт ли период прямо сейчас (для отметки «сейчас» в списке). */
export function isKalamActive(p: KalamPeriod, now: Date = new Date()): boolean {
  const t = now.getTime()
  return t >= p.start.getTime() && t < p.end.getTime()
}
