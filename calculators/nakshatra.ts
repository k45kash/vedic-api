/** Базовые операции с накшатрами: определение по долготе, ярлыки, ганданта. */
import NAMES from '../content/nakshatra_names.json'
import RULERS_SEQ from '../content/nak_rulers_seq.json'
import RULER_SHORT from '../content/nak_ruler_short.json'
import GANDANTA from '../content/gandanta_padas.json'

export const NAK_SIZE = 360 / 27 // 13°20′

export interface NakshatraPosition {
  no: number            // 1..27
  name: string
  pada: number          // 1..4
  degInNakshatra: number
  ruler: string         // управитель по Вимшоттари
}

/** Сидерическая долгота (0..360, аянамша уже вычтена — как в API) → накшатра и пада. */
export function nakshatraFromLongitude(sidLon: number): NakshatraPosition {
  const lon = ((sidLon % 360) + 360) % 360
  const idx = Math.floor(lon / NAK_SIZE) % 27
  const deg = lon % NAK_SIZE
  const pada = Math.floor(deg / (NAK_SIZE / 4)) + 1
  return { no: idx + 1, name: NAMES[idx], pada, degInNakshatra: deg, ruler: rulerOf(idx + 1) }
}

/** Управитель накшатры по циклу Вимшоттари (Кету → Венера → … → Меркурий). */
export function rulerOf(no: number): string {
  return RULERS_SEQ[(no - 1) % 9]
}

export function nakName(no: number): string {
  return NAMES[no - 1]
}

/** Ярлык для селектов: «1. Ашвини (Ке)» */
export function nakLabel(no: number): string {
  return `${no}. ${NAMES[no - 1]} (${RULER_SHORT[(no - 1) % 9]})`
}

/** Гандантовые накшатры (стыки вода→огонь): 1, 9, 10, 18, 19, 27. */
export function isGandantaNakshatra(no: number): boolean {
  return String(no) in GANDANTA
}

export { NAMES as NAK_NAMES }
