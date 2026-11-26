// Shared reactive state for a "birth" form used across pages.
// Defaults: Stavropol 17 May 1990 14:30 UTC+3.
export type PositionMode = 'apparent' | 'geometric'

export interface BirthForm {
  date: string   // yyyy-MM-dd
  time: string   // HH:mm
  lat: number
  lon: number
  tz: number
  position_mode: PositionMode
  city: string
}

export function useBirthForm(overrides: Partial<BirthForm> = {}) {
  return reactive<BirthForm>({
    date: '1990-05-17',
    time: '14:30',
    lat: 45.0428,
    lon: 41.9734,
    tz: 3,
    city: 'Ставрополь',
    position_mode: 'apparent',
    ...overrides,
  })
}

// Convert "YYYY-MM-DD" + "HH:mm" into the {year,month,day,hour,minute} shape the API expects.
export function birthToPayload(form: BirthForm) {
  const [y, m, d]   = form.date.split('-').map(Number)
  const [hh, mm]    = form.time.split(':').map(Number)
  return {
    position_mode: form.position_mode,
    year:   y,
    month:  m,
    day:    d,
    hour:   hh,
    minute: mm,
    tz:     form.tz,
    lat:    form.lat,
    lon:    form.lon,
  }
}
