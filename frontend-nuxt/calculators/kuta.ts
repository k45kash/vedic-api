/** Ашта-кута (совместимость пары) — 36 баллов из 8 кут.
 *
 * Две точки входа:
 *   • ashtaKutaPartial(brideNo, groomNo) — 21 балл по одним накшатрам Луны
 *     (Гана 6, Йони 4, Тара 3, Нади 8). Историческая функция, не менять:
 *     на ней сидит useJyotish.ts.
 *   • ashtaKutaFull(bride, groom) — все 36. Дополнительно нужен знак Луны
 *     (раши, 1..12) обоих партнёров: Варна 1, Вашья 2, Граха-майтри 5, Бхакут 7.
 *
 * Ни одна кута не оценивает Мангала-дошу, 7-е дома и навамшу — итог из 36
 * это ориентир, а не приговор (см. поле `disclaimer` в AshtaKutaFullResult).
 */
import NAKSHATRAS from '../content/nakshatras.json'
import SIGNS from '../content/signs.json'
import { taraFavorable } from './tara'

type Nak = (typeof NAKSHATRAS)[number]

export type KutaKey = 'varna' | 'vashya' | 'tara' | 'yoni' | 'grahaMaitri' | 'gana' | 'bhakuta' | 'nadi'

export interface KutaFactor {
  key: KutaKey
  label: string
  score: number | null // null — не удалось определить по данным
  max: number
  note: string
  dosha?: boolean      // нади-доша / бхакут-доша
  /** Оговорка «школы расходятся» — UI обязан её показать, если поле есть. */
  school?: string
}

export interface AshtaKutaResult {
  factors: KutaFactor[]
  total: number        // сумма посчитанных кут
  max: number          // 21 (частичный расчёт)
  fullMax: number      // 36 (полный ашта-кута)
  nadiDosha: boolean
}

const nakByNo = (no: number): Nak => NAKSHATRAS[no - 1]

/** «Конь (мужской)» → «Конь» */
const yoniAnimal = (s: string) => (s || '').replace(/\s*\(.*\)/, '').trim()

/** Нади — из структурного поля `dosha`, а НЕ из прозы `compat`.
 *
 * Раньше нади выдёргивалась регулярным выражением из свободного текста
 * `compat` («…Нади — Ади…»), и это давало неверный результат: в прозе нади
 * ошибочна у девяти накшатр (Мригашира, Ардра, Пушья, Ашлеша, Магха,
 * У.Пхалгуни, Вишакха, У.Ашадха, П.Бхадрапада) и ещё у шести записана как
 * «Анта/Антья», из-за чего строковое сравнение не находило совпадения и
 * нади-доша терялась. А нади — самая дорогая кута, 8 баллов из 36.
 *
 * Поле `dosha` при этом верное на все 27 — сверено с канонической схемой
 * (Ади-Мадхья-Антья / Антья-Мадхья-Ади по группам). Оно записано в
 * аюрведической номенклатуре, которая соответствует нади один в один.
 */
const DOSHA_TO_NADI: Record<string, string> = {
  'Вата': 'Ади',
  'Питта': 'Мадхья',
  'Капха': 'Антья',
}

const nadiOf = (d: Nak): string | null => {
  const dosha = String((d as { dosha?: string }).dosha || '').trim()
  const byDosha = DOSHA_TO_NADI[dosha]
  if (byDosha) return byDosha
  // Запасной путь для записей без `dosha`: проза, с нормализацией «Анта/Антья».
  const m = (d.compat || '').match(/Нади\s*[—-]\s*([А-Яа-я/]+)/)
  if (!m) return null
  const raw = m[1]
  if (raw.includes('Антья') || raw.includes('Анта')) return 'Антья'
  if (raw.includes('Мадхья')) return 'Мадхья'
  if (raw.includes('Ади')) return 'Ади'
  return raw
}

export function ganaKuta(a: Nak, b: Nak): KutaFactor {
  const ga = a.gana.split(' ')[0], gb = b.gana.split(' ')[0]
  let score = 6, note = '—'
  if (ga === gb) { score = 6; note = 'одна гана — гармония' }
  else if ((ga === 'Дэва' && gb === 'Манушья') || (ga === 'Манушья' && gb === 'Дэва')) {
    score = 5; note = 'дэва + манушья — хорошо'
  } else if ((ga === 'Манушья' && gb === 'Ракшаса') || (ga === 'Ракшаса' && gb === 'Манушья')) {
    score = 1; note = 'манушья + ракшаса — напряжение'
  } else if ((ga === 'Дэва' && gb === 'Ракшаса') || (ga === 'Ракшаса' && gb === 'Дэва')) {
    score = 0; note = 'дэва + ракшаса — сложно'
  }
  return { key: 'gana', label: 'Гана', score, max: 6, note }
}

export function yoniKuta(a: Nak, b: Nak): KutaFactor {
  const ya = yoniAnimal(a.yoni), yb = yoniAnimal(b.yoni)
  const enemyA = yoniAnimal(a.yoni_enemy || '')
  const enemyB = yoniAnimal(b.yoni_enemy || '')
  let score: number, note: string
  if (ya === yb) { score = 4; note = `одна йони (${ya}) — максимум` }
  else if ((enemyA && yb.includes(enemyA)) || (enemyB && ya.includes(enemyB))) {
    score = 0; note = `враждебные йони (${ya} / ${yb})`
  } else { score = 2; note = `разные йони — нейтрально (${ya} / ${yb})` }
  return { key: 'yoni', label: 'Йони', score, max: 4, note }
}

export function nadiKuta(a: Nak, b: Nak): KutaFactor {
  const na = nadiOf(a), nb = nadiOf(b)
  if (!na || !nb) return { key: 'nadi', label: 'Нади', score: null, max: 8, note: 'нади не распознана в данных' }
  if (na === nb) return { key: 'nadi', label: 'Нади', score: 0, max: 8, note: `одна нади (${na}) — НАДИ-ДОША (серьёзное препятствие)`, dosha: true }
  return { key: 'nadi', label: 'Нади', score: 8, max: 8, note: `разные нади (${na} / ${nb}) — благоприятно` }
}

export function taraKuta(brideNo: number, groomNo: number): KutaFactor {
  const t1 = taraFavorable(brideNo, groomNo)
  const t2 = taraFavorable(groomNo, brideNo)
  const score = (t1 ? 1.5 : 0) + (t2 ? 1.5 : 0)
  const note = t1 && t2 ? 'обе тары благоприятны' : t1 || t2 ? 'одна тара благоприятна' : 'обе тары неблагоприятны'
  return { key: 'tara', label: 'Тара', score, max: 3, note }
}

/** Частичный ашта-кута по накшатрам Луны невесты и жениха (1..27). */
export function ashtaKutaPartial(brideNo: number, groomNo: number): AshtaKutaResult {
  const a = nakByNo(brideNo), b = nakByNo(groomNo)
  const factors = [ganaKuta(a, b), yoniKuta(a, b), taraKuta(brideNo, groomNo), nadiKuta(a, b)]
  const total = factors.reduce((s, f) => s + (f.score ?? 0), 0)
  return {
    factors,
    total,
    max: 21,
    fullMax: 36,
    nadiDosha: factors.some((f) => f.dosha),
  }
}

// ════════════════════════════════════════════════════════════════════════════
//  Куты, считающиеся от знака Луны (раши). Варна 1, Вашья 2, Граха-майтри 5,
//  Бхакут 7 — вместе 15 баллов, доводят расчёт до полных 36.
//
//  Источники таблиц (сверено 2026-07, совпадающие места у ≥2 независимых):
//   [1] Drik Panchang, Ashta Kuta tutorial —
//       drikpanchang.com/tutorials/jyotisha/kundali-match/ashta-kuta/varna-kuta.html
//       …/vashya-kuta.html
//   [2] mohitmrinal.com/blog/four.php — сводные таблицы Варна / Граха-майтри / Бхакут
//   [3] astroyogi.com/blog/vasya-koota-in-kundli-matching.aspx и
//       tumblr @nadi-astrology-blog «Vasya Koota in Horoscope Matching» — разбивка
//       раши по группам вашьи и оси матрицы (строки — невеста)
//   [4] prokerala.com/astrology/kundali-matching (система Guna Milan) — эталонный
//       калькулятор, по нему снята матрица вашьи и сверены все четыре куты
//   [5] aaps.space/kundli-matching — правила Варны, Вашьи, Граха-майтри, Бхакута
// ════════════════════════════════════════════════════════════════════════════

type SignDef = (typeof SIGNS)['signs'][number]

const signByNo = (n: number): SignDef => SIGNS.signs[n - 1]
const signRu = (n: number): string => signByNo(n)?.name ?? `знак ${n}`
/** Управитель раши (для Граха-майтри и разбора бхакут-доши). */
const signLord = (n: number): string => signByNo(n)?.ruler ?? ''

// ─── Варна-кута (макс 1) ────────────────────────────────────────────────────
// 4 варны по стихии знака Луны [1][2][5]:
//   Брахман — водные (Рак, Скорпион, Рыбы)
//   Кшатрий — огненные (Овен, Лев, Стрелец)
//   Вайшья  — земные (Телец, Дева, Козерог)
//   Шудра   — воздушные (Близнецы, Весы, Водолей)
// Балл: варна жениха НЕ НИЖЕ варны невесты → 1, иначе 0.

const VARNA_RANK: Record<number, 1 | 2 | 3 | 4> = {
  1: 3, 5: 3, 9: 3,    // Кшатрий
  2: 2, 6: 2, 10: 2,   // Вайшья
  3: 1, 7: 1, 11: 1,   // Шудра
  4: 4, 8: 4, 12: 4,   // Брахман
}
const VARNA_RU: Record<1 | 2 | 3 | 4, string> = {
  4: 'Брахман', 3: 'Кшатрий', 2: 'Вайшья', 1: 'Шудра',
}

export function varnaKuta(brideSign: number, groomSign: number): KutaFactor {
  const rb = VARNA_RANK[brideSign], rg = VARNA_RANK[groomSign]
  if (!rb || !rg) {
    return { key: 'varna', label: 'Варна', score: null, max: 1, note: 'знак Луны не распознан' }
  }
  const ok = rg >= rb
  const note = rg === rb
    ? `одна варна (${VARNA_RU[rb]}) — засчитывается`
    : ok
      ? `варна жениха выше (${VARNA_RU[rg]} против ${VARNA_RU[rb]}) — засчитывается`
      : `варна невесты выше (${VARNA_RU[rb]} против ${VARNA_RU[rg]}) — балл не даётся`
  return {
    key: 'varna',
    label: 'Варна',
    score: ok ? 1 : 0,
    max: 1,
    note,
    school: ok ? undefined :
      'Часть школ при «низкой» варне жениха разрешает пересчитать варну по управителям ' +
      'раши (Юпитер/Венера — брахман, Марс/Солнце — кшатрий, Луна — вайшья, ' +
      'Меркурий/Сатурн — шудра). Здесь применено основное правило — по знаку Луны.',
  }
}

// ─── Вашья-кута (макс 2) ────────────────────────────────────────────────────
// Группы «власти» по знаку Луны [1][3][4]. Стрелец и Козерог делятся пополам,
// поэтому нужен градус Луны в знаке; без него берём первую половину и помечаем.
//   Чатушпада (четвероногие): Овен, Телец, Стрелец 15–30°, Козерог 0–15°
//   Нара (люди):              Близнецы, Дева, Весы, Водолей, Стрелец 0–15°
//   Джалачара (водные):       Рак, Рыбы, Козерог 15–30°
//   Ваначара (дикие звери):   Лев
//   Кита (насекомые):         Скорпион

type VashyaKey = 'chatushpada' | 'nara' | 'jalachara' | 'vanachara' | 'keeta'

const VASHYA_RU: Record<VashyaKey, string> = {
  chatushpada: 'Чатушпада (четвероногие)',
  nara: 'Нара (люди)',
  jalachara: 'Джалачара (водные)',
  vanachara: 'Ваначара (дикие звери)',
  keeta: 'Кита (насекомые)',
}

/** Строки — группа невесты, столбцы — группа жениха (матрица несимметрична).
 *
 * Смысл баллов: 2 — одна группа; 1 — раши невесты «вашья» (управляема) для раши
 * жениха; ½ — «бхакшья» (пища); 0 — влияния нет.
 *
 * Таблица снята эмпирически со всех 25 клеток калькулятора Prokerala Guna Milan
 * (сверка 2026-07, по паре дат на каждую клетку). Причина, почему не взята
 * веб-таблица: опубликованные варианты противоречат друг другу, а самый
 * растиражированный содержит явную опечатку — классическое «½ балла» перенесено
 * как «1.5» (в том же тексте словесное правило говорит именно про ½).
 *
 * Расхождение школ осталось в трёх клетках (см. VASHYA_DISPUTED):
 *   чатушпада×ваначара, ваначара×джалачара, кита×нара.
 */
const VASHYA_SCORE: Record<VashyaKey, Record<VashyaKey, number>> = {
  //             жених:  чатушпада  нара  джалачара  ваначара  кита
  chatushpada: { chatushpada: 2, nara: 1,   jalachara: 1,   vanachara: 0,   keeta: 1 },
  nara:        { chatushpada: 1, nara: 2,   jalachara: 0.5, vanachara: 0,   keeta: 1 },
  jalachara:   { chatushpada: 1, nara: 0.5, jalachara: 2,   vanachara: 1,   keeta: 1 },
  vanachara:   { chatushpada: 0, nara: 0,   jalachara: 1,   vanachara: 2,   keeta: 0 },
  keeta:       { chatushpada: 1, nara: 0,   jalachara: 1,   vanachara: 0,   keeta: 2 },
}

/** Клетки, где школы расходятся: «невеста→жених» → что дают другие таблицы. */
const VASHYA_DISPUTED: Partial<Record<VashyaKey, Partial<Record<VashyaKey, string>>>> = {
  chatushpada: { vanachara: 'часть таблиц даёт здесь ½ (четвероногие — «пища» льва)' },
  vanachara: { jalachara: 'часть таблиц даёт здесь 0 (лев никому не подчиняется)' },
  keeta: { nara: 'часть таблиц даёт здесь 1 (насекомые «вашья» для человека)' },
}

const VASHYA_WHOLE: Record<number, VashyaKey> = {
  1: 'chatushpada', 2: 'chatushpada', 3: 'nara', 4: 'jalachara', 5: 'vanachara',
  6: 'nara', 7: 'nara', 8: 'keeta', 11: 'nara', 12: 'jalachara',
  // 9 (Стрелец) и 10 (Козерог) — только через градус, см. vashyaGroup()
}

/** Группа вашьи по знаку; deg — градус Луны в знаке 0..30 (нужен для 9 и 10). */
export function vashyaGroup(sign: number, deg?: number): { key: VashyaKey | null; exact: boolean } {
  if (sign === 9) {
    if (deg == null) return { key: 'nara', exact: false }
    return { key: deg < 15 ? 'nara' : 'chatushpada', exact: true }
  }
  if (sign === 10) {
    if (deg == null) return { key: 'chatushpada', exact: false }
    return { key: deg < 15 ? 'chatushpada' : 'jalachara', exact: true }
  }
  const k = VASHYA_WHOLE[sign]
  return { key: k ?? null, exact: !!k }
}

export function vashyaKuta(
  brideSign: number, groomSign: number, brideDeg?: number, groomDeg?: number,
): KutaFactor {
  const gb = vashyaGroup(brideSign, brideDeg)
  const gg = vashyaGroup(groomSign, groomDeg)
  if (!gb.key || !gg.key) {
    return { key: 'vashya', label: 'Вашья', score: null, max: 2, note: 'знак Луны не распознан' }
  }
  const score = VASHYA_SCORE[gb.key][gg.key]
  const same = gb.key === gg.key
  const note = same
    ? `обе Луны в группе ${VASHYA_RU[gb.key]} — полное взаимное притяжение`
    : score === 0
      ? `${VASHYA_RU[gb.key]} и ${VASHYA_RU[gg.key]} — взаимного влияния нет`
      : `${VASHYA_RU[gb.key]} (невеста) и ${VASHYA_RU[gg.key]} (жених) — частичное влияние`
  const schoolParts: string[] = []
  const disputed = VASHYA_DISPUTED[gb.key]?.[gg.key]
  if (disputed) {
    schoolParts.push(
      `Таблицы вашьи у школ расходятся именно в этой клетке: ${disputed}. ` +
      'Взят вариант калькулятора Prokerala Guna Milan.',
    )
  }
  if (!gb.exact || !gg.exact) {
    schoolParts.push(
      'Градус Луны не передан, а Стрелец и Козерог делятся пополам между группами — ' +
      'взята первая половина знака, результат приблизителен.',
    )
  }
  return {
    key: 'vashya', label: 'Вашья', score, max: 2, note,
    school: schoolParts.length ? schoolParts.join(' ') : undefined,
  }
}

// ─── Граха-майтри (макс 5) ──────────────────────────────────────────────────
// Дружба управителей знаков Луны. Натуральные (наисаргика) отношения планет
// по Парашаре [2]. Композитную (панчадха, с временными отношениями) дружбу
// классическая ашта-кута не использует — оговорка в поле school.
//   Оба друзья / один управитель → 5 · друг+нейтрал → 4 · оба нейтралы → 3
//   друг+враг → 1 · нейтрал+враг → 0.5 · оба враги → 0
// Матрица из [2] полностью воспроизводится этим правилом — сходимость проверена
// по всем 21 паре планет.

type Rel = 'friend' | 'neutral' | 'enemy'

const NATURAL_FRIENDS: Record<string, { friends: string[]; enemies: string[] }> = {
  Солнце:   { friends: ['Луна', 'Марс', 'Юпитер'],     enemies: ['Венера', 'Сатурн'] },
  Луна:     { friends: ['Солнце', 'Меркурий'],          enemies: [] },
  Марс:     { friends: ['Солнце', 'Луна', 'Юпитер'],    enemies: ['Меркурий'] },
  Меркурий: { friends: ['Солнце', 'Венера'],            enemies: ['Луна'] },
  Юпитер:   { friends: ['Солнце', 'Луна', 'Марс'],      enemies: ['Меркурий', 'Венера'] },
  Венера:   { friends: ['Меркурий', 'Сатурн'],          enemies: ['Солнце', 'Луна'] },
  Сатурн:   { friends: ['Меркурий', 'Венера'],          enemies: ['Солнце', 'Луна', 'Марс'] },
}

/** Как планета `from` относится к планете `to` (натуральная дружба). */
export function naturalRelation(from: string, to: string): Rel | null {
  const r = NATURAL_FRIENDS[from]
  if (!r || !NATURAL_FRIENDS[to]) return null
  if (from === to) return 'friend'
  if (r.friends.includes(to)) return 'friend'
  if (r.enemies.includes(to)) return 'enemy'
  return 'neutral'
}

const REL_RU: Record<Rel, string> = { friend: 'друг', neutral: 'нейтрал', enemy: 'враг' }

function maitriScore(a: Rel, b: Rel): number {
  const set = [a, b].sort().join('+') // enemy < friend < neutral в алфавите
  switch (set) {
    case 'friend+friend': return 5
    case 'friend+neutral': return 4
    case 'neutral+neutral': return 3
    case 'enemy+friend': return 1
    case 'enemy+neutral': return 0.5
    default: return 0 // enemy+enemy
  }
}

export function grahaMaitriKuta(brideSign: number, groomSign: number): KutaFactor {
  const lb = signLord(brideSign), lg = signLord(groomSign)
  const rBG = naturalRelation(lb, lg), rGB = naturalRelation(lg, lb)
  if (!rBG || !rGB) {
    return { key: 'grahaMaitri', label: 'Граха-майтри', score: null, max: 5, note: 'управитель знака не распознан' }
  }
  const school =
    'Взяты натуральные (наисаргика) отношения планет по Парашаре — так считает ' +
    'большинство калькуляторов. Часть школ применяет композитную (панчадха) дружбу ' +
    'с временными отношениями — там балл может отличаться.'
  if (lb === lg) {
    return {
      key: 'grahaMaitri', label: 'Граха-майтри', score: 5, max: 5,
      note: `один управитель обеих Лун (${lb}) — максимум`, school,
    }
  }
  const score = maitriScore(rBG, rGB)
  return {
    key: 'grahaMaitri', label: 'Граха-майтри', score, max: 5,
    note: `${lb} (невеста) → ${lg}: ${REL_RU[rBG]}; ${lg} (жених) → ${lb}: ${REL_RU[rGB]}`,
    school,
  }
}

// ─── Бхакут-кута (макс 7) ───────────────────────────────────────────────────
// Взаимное положение знаков Луны: счёт домов в обе стороны [2][5].
//   1/1, 3/11, 4/10, 7/7 → 7 баллов
//   2/12, 5/9, 6/8       → 0 баллов и бхакут-доша
// Отмены доши (одинаковый управитель раши, дружественные управители, обмен,
// аспект Юпитера на 7-й дом) школы применяют по-разному; здесь балл ставится
// строго по таблице (как у публичных калькуляторов), а условие отмены —
// отдельным флагом, чтобы UI мог честно сказать «доша смягчается».

const BHAKUTA_BAD = new Set([2, 12, 5, 9, 6, 8])

const BHAKUTA_MEANING: Record<number, string> = {
  2: 'двир-двадаша (2/12) — трение вокруг денег и быта',
  12: 'двир-двадаша (2/12) — трение вокруг денег и быта',
  5: 'нава-панчама (5/9) — тема детей и общей дхармы',
  9: 'нава-панчама (5/9) — тема детей и общей дхармы',
  6: 'шаштха-аштама (6/8) — самая тяжёлая пара: здоровье и бытовые конфликты',
  8: 'шаштха-аштама (6/8) — самая тяжёлая пара: здоровье и бытовые конфликты',
}

export function bhakutaKuta(brideSign: number, groomSign: number): KutaFactor {
  if (!signByNo(brideSign) || !signByNo(groomSign)) {
    return { key: 'bhakuta', label: 'Бхакут', score: null, max: 7, note: 'знак Луны не распознан' }
  }
  // Дистанция от Луны невесты к Луне жениха и обратно (1..12, свой знак = 1).
  const dBG = ((groomSign - brideSign + 12) % 12) + 1
  const dGB = ((brideSign - groomSign + 12) % 12) + 1
  const pair = `${Math.min(dBG, dGB)}/${Math.max(dBG, dGB)}`
  const bad = BHAKUTA_BAD.has(dBG)
  const lb = signLord(brideSign), lg = signLord(groomSign)

  if (!bad) {
    return {
      key: 'bhakuta', label: 'Бхакут', score: 7, max: 7,
      note: `${signRu(brideSign)} и ${signRu(groomSign)} — положение ${pair}, благоприятно`,
    }
  }

  // Условия смягчения (не меняют балл, но показываются в UI).
  const sameLord = lb === lg
  const friendly = naturalRelation(lb, lg) === 'friend' && naturalRelation(lg, lb) === 'friend'
  const relief = sameLord
    ? `Смягчение: у обоих раши один управитель (${lb}) — классическая отмена бхакут-доши.`
    : friendly
      ? `Смягчение: управители раши (${lb} и ${lg}) — взаимные друзья, многие школы считают дошу снятой.`
      : ''

  return {
    key: 'bhakuta', label: 'Бхакут', score: 0, max: 7, dosha: true,
    note: `${signRu(brideSign)} и ${signRu(groomSign)} — положение ${pair}: ${BHAKUTA_MEANING[dBG]} — БХАКУТ-ДОША`,
    school:
      (relief ? relief + ' ' : '') +
      'Балл выставлен строго по таблице (0), как в публичных калькуляторах. ' +
      'Школы расходятся: часть при отмене доши возвращает все 7 баллов.',
  }
}

// ─── Полный ашта-кута (36) ──────────────────────────────────────────────────

export interface KutaPerson {
  /** Накшатра Луны, 1..27 (API: horoscope.nk.num для своей карты). */
  nakNo: number
  /** Знак Луны (раши), 1..12 (API: planets[«Луна»].sign_num). */
  moonSign: number
  /** Градус Луны в знаке 0..30 (API: planets[«Луна»].deg_in_sign).
   *  Нужен только Вашье — Стрелец и Козерог делятся пополам. */
  moonDeg?: number
}

export type KutaVerdictLevel = 'excellent' | 'good' | 'acceptable' | 'weak'

export interface AshtaKutaFullResult {
  factors: KutaFactor[]     // все 8, в каноническом порядке Варна → Нади
  total: number             // 0..36
  max: 36
  percent: number           // округлённый процент от 36
  nadiDosha: boolean
  bhakutaDosha: boolean
  /** false, если хотя бы одна кута не посчиталась (score === null) — тогда
   *  `total` заведомо занижен и вердикту верить нельзя. */
  complete: boolean
  /** Уровень вердикта: ≥32 отлично · ≥25 хорошо · ≥18 приемлемо · <18 слабо. */
  level: KutaVerdictLevel
  /** Однострочный вердикт по итогу и дошам. */
  verdict: string
  /** Построчный разбор для UI: по строке на куту + строки про доши. */
  lines: string[]
  /** Оговорки «школы расходятся» из посчитанных кут (уже собранные). */
  caveats: string[]
  /** Что ашта-кута НЕ покрывает. UI обязан это показать (docs/HANDOFF.md §5). */
  notCovered: string[]
  /** Готовая формулировка неполноты — показывать всегда, даже при 36/36. */
  disclaimer: string
}

const NOT_COVERED = [
  'Мангала-доша (Куджа-доша) — положение Марса у обоих; проверяется отдельно',
  'седьмой дом и его управитель в обеих картах — сама тема брака',
  'навамша (D-9) и другие дробные карты — прочность союза',
  'даши и текущие транзиты — время, а не сама совместимость',
  'возраст, здоровье, договорённости и согласие людей — вне джьотиша',
]

const DISCLAIMER =
  'Ашта-кута — только один слой сверки, и даже 36 из 36 не означают «идеальную пару». ' +
  'Система смотрит на Луну обоих и молчит о Мангала-доше, седьмых домах, навамше и дашах. ' +
  'Это ориентир для разговора, а не приговор и не решение за людей.'

function verdictLevel(total: number): KutaVerdictLevel {
  if (total >= 32) return 'excellent'
  if (total >= 25) return 'good'
  if (total >= 18) return 'acceptable'
  return 'weak'
}

/** Полный ашта-кута: 36 баллов по накшатрам и знакам Луны обоих партнёров.
 *
 * Порядок аргументов важен — куты Варна и Вашья несимметричны (жених/невеста).
 */
export function ashtaKutaFull(bride: KutaPerson, groom: KutaPerson): AshtaKutaFullResult {
  const a = nakByNo(bride.nakNo), b = nakByNo(groom.nakNo)

  const factors: KutaFactor[] = [
    varnaKuta(bride.moonSign, groom.moonSign),
    vashyaKuta(bride.moonSign, groom.moonSign, bride.moonDeg, groom.moonDeg),
    taraKuta(bride.nakNo, groom.nakNo),
    yoniKuta(a, b),
    grahaMaitriKuta(bride.moonSign, groom.moonSign),
    ganaKuta(a, b),
    bhakutaKuta(bride.moonSign, groom.moonSign),
    nadiKuta(a, b),
  ]

  const total = factors.reduce((s, f) => s + (f.score ?? 0), 0)
  const nadiDosha = factors.some((f) => f.key === 'nadi' && f.dosha)
  const bhakutaDosha = factors.some((f) => f.key === 'bhakuta' && f.dosha)
  const complete = factors.every((f) => f.score !== null)
  const level = verdictLevel(total)

  const lines = factors.map(
    (f) => `${f.label}: ${f.score ?? '—'} из ${f.max} — ${f.note}`,
  )
  if (!complete) {
    lines.push(
      'Часть кут посчитать не удалось — итог заведомо занижен, ' +
      'вердикту по сумме верить нельзя. Проверьте входные данные.',
    )
  }
  if (nadiDosha) {
    lines.push(
      'Нади-доша: у обоих одна нади. Традиция считает это самым весомым возражением ' +
      'из восьми — но не запретом: смотрят карту целиком и принятые упайи.',
    )
  }
  if (bhakutaDosha) {
    lines.push(
      'Бхакут-доша: знаки Луны стоят в неблагоприятном взаимном положении. ' +
      'Проверьте условия отмены — они указаны в оговорке к куте.',
    )
  }

  const base = `${total} из 36`
  const verdict = !complete
    ? `${base} — расчёт неполный, часть кут не посчиталась; итог не показателен`
    : level === 'excellent' ? `${base} — очень высокая сходимость по ашта-куте`
    : level === 'good' ? `${base} — хорошая сходимость по ашта-куте`
    : level === 'acceptable' ? `${base} — проходной порог (18) взят, но запас небольшой`
    : `${base} — ниже традиционного порога 18; ашта-кута этот союз не поддерживает`

  const caveats = factors.map((f) => f.school).filter((s): s is string => !!s)

  return {
    factors,
    total,
    max: 36,
    percent: Math.round((total / 36) * 100),
    nadiDosha,
    bhakutaDosha,
    complete,
    level,
    verdict,
    lines,
    caveats,
    notCovered: NOT_COVERED,
    disclaimer: DISCLAIMER,
  }
}
