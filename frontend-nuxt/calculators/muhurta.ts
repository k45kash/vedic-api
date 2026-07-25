/** 30 мухурт суток: времена из /api/panchang + описания из content/muhurta30.json.
 *
 * МЕТОД. Сутки от восхода до следующего восхода делятся на 30 частей:
 * 15 дневных (восход → закат) и 15 ночных (закат → следующий восход).
 * Каждая часть = 1/15 своей половины, поэтому «48 минут» — номинал: летом
 * дневная мухурта длиннее часа, ночная — около получаса.
 *
 * Так же это описано и в самих данных: `intro` в muhurta30.json говорит про
 * деление суток от восхода до восхода, где первые 15 приходятся на светлую
 * часть, вторые 15 — на тёмную, а `time_note` прямо оговаривает, что точная
 * длительность зависит от долготы дня. Расхождения между данными и расчётом
 * бэкенда (Panchangam.calc_muhurtas_day) здесь нет — времена берём как есть,
 * своей арифметики над ними не делаем.
 *
 * ⚠️ РАСХОЖДЕНИЕ ИМЁН. Таблица имён в расчётном ядре (Panchangam.MUHURTAS) и
 * в контентной базе — два разных традиционных списка. Порядок и роль позиций
 * совпадают, но имена по нормализации ниже расходятся в 14 позициях из 30:
 * часть — разночтение транслитерации (1 Рудра/Раудра, 4 Питру/Питри,
 * 23 Видхата/Видхатри), часть — другое имя того же отрезка (5 Васу/Савитри,
 * 9 Хутасана/Раухина, 10 Пурухута/Бала, 12 Нактанкара/Ниррита,
 * 24 Канда/Ратринатха, 28 Дьюмадгадьюти/Тапас, 30 Самудрам/Ваю).
 * Поэтому: описание берётся из контента по НОМЕРУ мухурты, а имя расчётного
 * ядра показывается рядом как вариант, а не подменяется молча.
 *
 * Файл тянет muhurta30.json (55 КБ) — подключается только ленивым import()
 * через composables/useJyotish.ts.
 */
import MUHURTA30 from '../content/muhurta30.json'

interface RawMuhurta {
  n: number
  name: string
  skt: string
  lord: string
  theme: string
  meaning: string
  choose: string
  birth: string
  prashna: string
  deity_full: string
  sources: string
}

const M30 = MUHURTA30 as unknown as {
  intro: string
  time_note: string
  muhurtas: RawMuhurta[]
  src: string
}

/** Одна мухурта в ответе /api/panchang → days[].muhurtas[]. */
export interface ApiMuhurta {
  num: number            // 1..30
  name: string           // имя по таблице расчётного ядра
  quality: string        // «Благоприятная» … — оттуда же
  day_night: string      // «день» | «ночь»
  dt_start: string       // локальное время места, без смещения
  dt_end: string
}

export interface DayMuhurta {
  n: number
  /** Имя из контентной базы — основное. */
  name: string
  /** Имя из таблицы расчёта; отличается от `name` в 11 позициях из 30. */
  calcName: string
  nameDiffers: boolean
  skt: string
  lord: string
  theme: string
  meaning: string
  choose: string
  birth: string
  prashna: string
  deity: string
  sources: string
  /** Качество по таблице расчётного ядра (в контентной базе его нет). */
  quality: string
  night: boolean
  start: Date
  end: Date
  /** Длительность в минутах — она заметно разная днём и ночью. */
  minutes: number
  /** 8-я дневная — Абхиджит, отрезок вокруг местного полудня. */
  abhijit: boolean
}

/** API отдаёт локальное время места без смещения — трактуем как локальное. */
const at = (iso: string) => new Date(iso)

/** Мухурты суток: описания из контента подставляются к временам расчёта.
 * Записи, для которых в контенте нет номера, пропускаются — выдумывать нечего. */
export function dayMuhurtas(list: ApiMuhurta[]): DayMuhurta[] {
  const byNo = new Map(M30.muhurtas.map((m) => [m.n, m]))
  const out: DayMuhurta[] = []
  for (const api of list) {
    const c = byNo.get(api.num)
    if (!c) continue
    const start = at(api.dt_start)
    const end = at(api.dt_end)
    out.push({
      n: api.num,
      name: c.name,
      calcName: api.name,
      nameDiffers: !sameName(c.name, api.name),
      skt: c.skt,
      lord: c.lord,
      theme: c.theme,
      meaning: c.meaning,
      choose: c.choose,
      birth: c.birth,
      prashna: c.prashna,
      deity: c.deity_full,
      sources: c.sources,
      quality: api.quality,
      night: api.day_night === 'ночь',
      start,
      end,
      minutes: Math.round((end.getTime() - start.getTime()) / 60000),
      abhijit: api.num === 8,
    })
  }
  return out
}

/** Имена считаем одинаковыми, если различаются только уточнением в скобках,
 * ё/е или пробелами: «Ахи» ≈ «Ахи (Сарпа)», «Ахир Будхнья» ≈ «Ахирбудхнья». */
function sameName(a: string, b: string): boolean {
  const norm = (s: string) => s
    .toLowerCase()
    .replace(/\(.*?\)/g, '')
    .replace(/ё/g, 'е')
    .replace(/[^а-я]/g, '')
  const x = norm(a)
  const y = norm(b)
  return x === y || x.startsWith(y) || y.startsWith(x)
}

/** Идущая сейчас мухурта; null — момент вне суток этого расчёта. */
export function currentMuhurta(list: DayMuhurta[], now: Date): DayMuhurta | null {
  return list.find((m) => now >= m.start && now < m.end) ?? null
}

export const MUHURTA_TEXTS = {
  intro: M30.intro,
  timeNote: M30.time_note,
  src: M30.src,
}
