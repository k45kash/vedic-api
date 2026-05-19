// Number → "12°34'56\""
export function toDMS(deg: number): string {
  if (deg == null || isNaN(deg)) return '—'
  const d = Math.floor(deg)
  const mf = (deg - d) * 60
  const m = Math.floor(mf)
  const s = Math.round((mf - m) * 60)
  return `${d}°${String(m).padStart(2, '0')}'${String(s).padStart(2, '0')}"`
}
