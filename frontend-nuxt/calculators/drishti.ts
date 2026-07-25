/** Дришти (аспекты), юти (соединения) и описания периодов Вимшоттари.
 *
 * Всё содержательное берётся из `content/yogakarma.json` — здесь только
 * геометрия Whole Sign и сопоставление с записями справочника. Ничего,
 * чего нет в данных, модуль не добавляет:
 *   • список аспектов каждой планеты читается из строк вида
 *     «4-й дом от себя (особый)» — смещение парсится из самой записи,
 *     а не задаётся таблицей «по памяти»;
 *   • пометка «(по ряду школ)» из данных доезжает до UI флагом `disputed`
 *     (актуально для 5-го и 9-го аспектов узлов);
 *   • пары соединений ищутся среди 36 записей справочника; нет записи —
 *     строки не будет.
 *
 * ВАЖНО про метод: аспект считается по знакам (раши-дришти в раскладке
 * Whole Sign) и только полный — градусной силы (дришти-бала) и частичных
 * аспектов в данных нет, поэтому их здесь нет тоже. Соединением считается
 * стоянка в одном знаке, без орбиса в градусах.
 *
 * Файл тянет yogakarma.json (79 КБ), поэтому подключается только ленивым
 * import() через composables/useJyotish.ts.
 */
import YOGAKARMA from '../content/yogakarma.json'
import SIGNS from '../content/signs.json'
import { houseForSign } from './chart'
import { PLANETS_RU, type PlanetRu } from './types'

// ─── Разбор справочника ─────────────────────────────────────────────────────

interface RawAspectPlanet { id: string; name: string; aspects: string[]; desc: string }
interface RawPair { p: string; tag: string; d: string }
interface RawDashaPlanet { id: string; name: string; years: number; desc: string }

const YK = YOGAKARMA as unknown as {
  aspects: { intro: string; note: string; planets: RawAspectPlanet[]; src: string }
  conjunctions: { intro: string; pairs: RawPair[]; src: string }
  dashas: { intro: string; note: string; planets: RawDashaPlanet[]; order_note: string; src: string }
  antardashas: {
    intro: string
    rel_legend: Record<string, string>
    planets: Array<{ id: string; name: string }>
    antar: Record<string, Record<string, { name: string; rel: string; text: string }>>
    src: string
  }
}

/** id планеты в справочнике («guru») → русское имя («Юпитер»). */
const NAME_BY_ID = new Map<string, string>(YK.aspects.planets.map((p) => [p.id, p.name]))
/** Обратное соответствие: имя из ответа API → id справочника. */
const ID_BY_NAME = new Map<string, string>(YK.aspects.planets.map((p) => [p.name, p.id]))

export function planetIdOf(name: string): string | null {
  return ID_BY_NAME.get(name) ?? null
}
export function planetNameOf(id: string): string | null {
  return NAME_BY_ID.get(id) ?? null
}

// ─── Аспекты ────────────────────────────────────────────────────────────────

export interface AspectTarget {
  /** Номер дома от планеты: 3, 4, 5, 7, 8, 9, 10. */
  offset: number
  /** Подпись ровно как в справочнике: «5-й дом от себя (особый)». */
  label: string
  /** В справочнике эта строка помечена «(по ряду школ)» — школы расходятся. */
  disputed: boolean
  /** Знак, на который приходится аспект (1..12). */
  sign: number
  signName: string
  /** Дом от Лагны; null — лагна недостоверна, дома считать нельзя. */
  house: number | null
  /** Планеты, стоящие в этом знаке (кроме самой аспектирующей). */
  hits: PlanetRu[]
}

export interface AspectRow {
  planet: PlanetRu
  /** Знак и дом самой планеты. */
  sign: number
  signName: string
  house: number | null
  /** Общий текст справочника про аспекты этой планеты. */
  desc: string
  targets: AspectTarget[]
  /** Хотя бы один аспект помечен «(по ряду школ)». */
  hasDisputed: boolean
}

export interface DrishtiInput {
  name: PlanetRu
  sign: number
}

/** «7-й дом от себя (полный)» → 7. Ничего не нашли — запись пропускаем. */
function offsetOf(label: string): number | null {
  const m = /^(\d+)/.exec(label.trim())
  if (!m) return null
  const n = Number(m[1])
  return n >= 1 && n <= 12 ? n : null
}

const signName = (no: number) => SIGNS.signs[no - 1]?.name ?? ''

/** Знак, отстоящий на `offset` домов вперёд от знака `from` (Whole Sign). */
function signAt(from: number, offset: number): number {
  return ((from - 1 + offset - 1) % 12) + 1
}

/** Аспекты всех планет карты.
 * `lagnaSign` = null — время рождения неизвестно: знаки остаются верными,
 * номера домов не считаются вовсе (docs/PLAN.md 2.3). */
export function planetAspects(planets: DrishtiInput[], lagnaSign: number | null): AspectRow[] {
  const bySign = new Map<number, PlanetRu[]>()
  for (const p of planets) {
    const list = bySign.get(p.sign) ?? []
    list.push(p.name)
    bySign.set(p.sign, list)
  }

  const order = PLANETS_RU as readonly PlanetRu[]
  const rows: AspectRow[] = []

  for (const p of [...planets].sort((a, b) => order.indexOf(a.name) - order.indexOf(b.name))) {
    const def = YK.aspects.planets.find((d) => d.name === p.name)
    if (!def) continue // планеты нет в справочнике — строку не рисуем

    const targets: AspectTarget[] = []
    for (const label of def.aspects) {
      const offset = offsetOf(label)
      if (offset === null) continue
      const sign = signAt(p.sign, offset)
      targets.push({
        offset,
        label,
        disputed: /по ряду школ/i.test(label),
        sign,
        signName: signName(sign),
        house: lagnaSign ? houseForSign(lagnaSign, sign) : null,
        hits: (bySign.get(sign) ?? []).filter((n) => n !== p.name),
      })
    }
    if (!targets.length) continue

    rows.push({
      planet: p.name,
      sign: p.sign,
      signName: signName(p.sign),
      house: lagnaSign ? houseForSign(lagnaSign, p.sign) : null,
      desc: def.desc,
      targets: targets.sort((a, b) => a.offset - b.offset),
      hasDisputed: targets.some((t) => t.disputed),
    })
  }
  return rows
}

// ─── Соединения (юти) ───────────────────────────────────────────────────────

export interface ConjunctionRow {
  /** Пара в том написании, как она стоит в справочнике: «Солнце + Меркурий». */
  pair: string
  a: PlanetRu
  b: PlanetRu
  /** Именованная йога, если справочник её называет («Будха-Адитья-йога»). */
  tag: string
  text: string
  sign: number
  signName: string
  house: number | null
  /** Все планеты этого знака — соединение читают целиком, а не по парам. */
  group: PlanetRu[]
}

/** Ключ пары независимо от порядка: «Луна|Солнце». */
const pairKey = (a: string, b: string) => [a, b].sort().join('|')

const PAIR_BY_KEY = new Map<string, RawPair>(
  YK.conjunctions.pairs.map((r) => {
    const [a, b] = r.p.split('+').map((s) => s.trim())
    return [pairKey(a, b), r] as const
  }),
)

/** Соединения: планеты в одном знаке, попарно, с описанием из справочника.
 * Орбиса в градусах нет — соединением считается общий знак (так устроены
 * и сами записи справочника). */
export function conjunctions(planets: DrishtiInput[], lagnaSign: number | null): ConjunctionRow[] {
  const order = PLANETS_RU as readonly PlanetRu[]
  const bySign = new Map<number, PlanetRu[]>()
  for (const p of planets) {
    const list = bySign.get(p.sign) ?? []
    list.push(p.name)
    bySign.set(p.sign, list)
  }

  const rows: ConjunctionRow[] = []
  for (const [sign, names] of [...bySign.entries()].sort((x, y) => x[0] - y[0])) {
    if (names.length < 2) continue
    const group = [...names].sort((a, b) => order.indexOf(a) - order.indexOf(b))
    for (let i = 0; i < group.length; i++) {
      for (let j = i + 1; j < group.length; j++) {
        const rec = PAIR_BY_KEY.get(pairKey(group[i], group[j]))
        if (!rec) continue // такой пары в справочнике нет — молчим
        rows.push({
          pair: rec.p,
          a: group[i],
          b: group[j],
          tag: rec.tag || '',
          text: rec.d,
          sign,
          signName: signName(sign),
          house: lagnaSign ? houseForSign(lagnaSign, sign) : null,
          group,
        })
      }
    }
  }
  return rows
}

// ─── Периоды Вимшоттари: описания ───────────────────────────────────────────

export interface DashaReading {
  maha: { id: string; name: string; years: number; desc: string } | null
  antar: { id: string; name: string; rel: string; relLabel: string; text: string } | null
}

/** Описания текущей маха-даши и антар-даши по id планет из /api/horoscope
 * (`dasha_current.mahadasha.lord_id` / `antardasha.lord_id`).
 * Сами даты и границы периодов считает бэкенд — здесь только трактовки. */
export function dashaReading(mahaId: string | null, antarId: string | null): DashaReading {
  const maha = mahaId ? YK.dashas.planets.find((p) => p.id === mahaId) ?? null : null
  const antarRec = mahaId && antarId ? YK.antardashas.antar[mahaId]?.[antarId] ?? null : null
  return {
    maha: maha ? { id: maha.id, name: maha.name, years: maha.years, desc: maha.desc } : null,
    antar: antarRec
      ? {
          id: antarId!,
          name: antarRec.name,
          rel: antarRec.rel,
          relLabel: YK.antardashas.rel_legend[antarRec.rel] ?? '',
          text: antarRec.text,
        }
      : null,
  }
}

// ─── Тексты справочника, которые показывает UI ──────────────────────────────

export const DRISHTI_TEXTS = {
  aspectsIntro: YK.aspects.intro,
  aspectsNote: YK.aspects.note,
  aspectsSrc: YK.aspects.src,
  conjunctionsIntro: YK.conjunctions.intro,
  conjunctionsSrc: YK.conjunctions.src,
  dashasIntro: YK.dashas.intro,
  dashasNote: YK.dashas.note,
  dashasOrder: YK.dashas.order_note,
  dashasSrc: YK.dashas.src,
  antarIntro: YK.antardashas.intro,
  antarSrc: YK.antardashas.src,
}
