/** Ашта-кута (совместимость пары) — частичный расчёт по накшатрам Луны.
 *
 * Точно считаются 4 куты из 8: Гана (6), Йони (4), Тара (3), Нади (8) — 21 балл.
 * Остальные 4 (Варна 1, Вашья 2, Граха-майтри 5, Бхакут 7) требуют раши Луны
 * обоих партнёров — их добавит расчёт при интеграции с API (знак Луны там есть).
 */
import NAKSHATRAS from '../content/nakshatras.json'
import { taraFavorable } from './tara'

type Nak = (typeof NAKSHATRAS)[number]

export interface KutaFactor {
  key: 'gana' | 'yoni' | 'tara' | 'nadi'
  label: string
  score: number | null // null — не удалось определить по данным
  max: number
  note: string
  dosha?: boolean      // нади-доша
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

/** Нади зашита в поле compat: «…Нади — Ади…» */
const nadiOf = (d: Nak): string | null => {
  const m = (d.compat || '').match(/Нади\s*[—-]\s*([А-Яа-я/]+)/)
  return m ? m[1] : null
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
