// Постоянный профиль рождения пользователя + кэш ответа /api/horoscope.
//
// Отличие от useBirthForm.ts: тот — эфемерная форма «посчитать что-нибудь»
// на старых страницах (index/panchang/calendar/sade-sati), живёт ровно столько,
// сколько открыта страница. Здесь — ОДИН профиль пользователя, который
// переживает перезагрузку (localStorage) и переиспользуется всеми экранами
// нового кабинета, чтобы не дёргать API на каждой странице.
//
// Режим «по Луне» (timeUnknown): время рождения неизвестно — считаем на полдень,
// но помечаем лагну и дома недостоверными (см. lagnaReliable / moonUncertain).

// ─── Типы ответа /api/horoscope ──────────────────────────────────────────────
// Собирается в nakshatra_calculator.calculate(). Описано ровно то, что реально
// приходит; структурно совместимо с HoroscopeResponse из calculators/api-adapter.ts
// (тот покрывает лишь nk / lagna.sign_num / planets — здесь полный набор).

/** Накшатра Луны: справочник utils.NAKSHATRAS + пада и градус внутри накшатры. */
export interface HoroNakshatra {
  num: number                   // 1..27
  name: string                  // «Dhanishtha»
  ru: string                    // «Дхаништха»
  lord: string                  // управитель по Вимшоттари, «Марс»
  gana: string                  // 'Devata' | 'Manushya' | 'Rakshasa'
  symbol: string
  pada: number                  // 1..4
  degrees_in_nakshatra: number  // 0..13.333
}

/** Один дом в раскладке Whole Sign от Лагны. */
export interface HoroHouse {
  house: number                 // 1..12
  sign_num: number              // 1..12 (Овен = 1)
  sign: string                  // «Virgo»
  sign_ru: string               // «Дева»
  lord: string
  meaning: string
}

export interface HoroLagna {
  trop_asc: number
  sid_asc: number
  asc_dms: string
  sign_num: number
  sign: string
  sign_ru: string
  lord: string
  element: string
  deg_in_sign: number
  deg_in_sign_dms: string
  houses: HoroHouse[]
}

export interface HoroPlanet {
  idx: number
  name: string                  // русское имя: «Солнце»… (ключ для калькуляторов)
  abbr: string                  // символ ☉ ☽ …
  available: boolean
  trop: number
  sid: number
  sid_dms: string
  sign_num: number              // 1..12
  sign: string
  sign_ru: string
  deg_in_sign: number
  deg_in_sign_dms: string
  nakshatra: string
  nakshatra_ru: string
  pada: number
  nk_lord: string
  house: number                 // 1..12, Whole Sign от Лагны
  /** API его сейчас НЕ отдаёт; поле оставлено, т.к. adapter и chart.ts его читают. */
  retro?: boolean
}

/** Диагностика границы накшатры (nakshatra_calculator.check_boundary).
 * is_boundary = dist_deg < 0.25°. Поля topo/aya_compare заполняются
 * ТОЛЬКО когда is_boundary === true, иначе null / {}. */
export interface HoroBoundary {
  dist_deg: number              // расстояние Луны до ближайшей границы накшатры
  dist_arcsec: number
  is_boundary: boolean
  topo: null | {
    delta_arcsec: number
    nk_geo: string
    nk_topo: string
    changes: boolean            // топоцентрическая поправка меняет накшатру
  }
  aya_compare: Record<string, { label: string; aya: number; nk: string; pada: number }>
  /** Есть только при is_boundary: согласны ли Lahiri / KP / TrueChitra. */
  ayas_agree?: boolean
}

export interface HoroscopeResult {
  input: { date: string; time: string; tz: number; lat: number; lon: number }
  jd: number
  aya: number
  moon_trop: number
  moon_sid: number              // сидерическая долгота Луны, 0..360
  moon_dms: string
  method: string
  nk: HoroNakshatra
  lagna: HoroLagna
  boundary: HoroBoundary
  planets: HoroPlanet[]
}

// ─── Профиль ────────────────────────────────────────────────────────────────

export interface BirthProfile {
  /** Необязательное имя — только для приветствия в UI. */
  name: string
  date: string        // YYYY-MM-DD
  time: string        // HH:mm (при timeUnknown игнорируется)
  timeUnknown: boolean
  lat: number
  lon: number
  tz: number          // смещение UTC в часах
  city: string
}

const STORAGE_KEY = 'vedic_birth_profile'

/** Время, на которое считаем гороскоп, если время рождения неизвестно. */
const FALLBACK_TIME = '12:00'

/** Ширина накшатры, градусы. */
const NAK_SIZE = 360 / 27

/** Максимальная суточная скорость Луны (перигей), градусы/сутки.
 * Реальный разброс 11,8–15,4°/сут — берём верх, чтобы окно неопределённости
 * при неизвестном времени было консервативным, а не оптимистичным. */
const MOON_MAX_DEG_PER_DAY = 15.4

export function emptyBirthProfile(): BirthProfile {
  return { name: '', date: '', time: '', timeUnknown: false, lat: 0, lon: 0, tz: 0, city: '' }
}

/** Профиль → тело запроса POST /api/horoscope.
 * При timeUnknown подставляем полдень: это середина суток, максимальная ошибка
 * по времени ±12 ч (лагна становится бессмысленной, Луна — ±7,7°). */
export function birthProfileToPayload(p: BirthProfile) {
  const [y, m, d] = p.date.split('-').map(Number)
  const [hh, mm] = (p.timeUnknown ? FALLBACK_TIME : p.time || FALLBACK_TIME).split(':').map(Number)
  return { year: y, month: m, day: d, hour: hh, minute: mm, tz: p.tz, lat: p.lat, lon: p.lon }
}

/** Сигнатура профиля: меняется — кэш гороскопа считается протухшим.
 * name не входит: это чисто UI-поле, на расчёт не влияет. */
function signature(p: BirthProfile): string {
  return [p.date, p.timeUnknown ? 'unknown' : p.time, p.timeUnknown ? 1 : 0,
    p.lat, p.lon, p.tz, p.city].join('|')
}

interface StoredState {
  profile: BirthProfile
  horoscope: HoroscopeResult | null
  sig: string | null
}

export function useBirthProfile() {
  const api = useApi()

  const profile = useState<BirthProfile | null>('vedic:birthProfile', () => null)
  const horoscope = useState<HoroscopeResult | null>('vedic:birthHoroscope', () => null)
  // Сигнатура профиля, для которого получен horoscope.
  const horoscopeSig = useState<string | null>('vedic:birthHoroscopeSig', () => null)
  const loading = useState<boolean>('vedic:birthLoading', () => false)
  const error = useState<string>('vedic:birthError', () => '')
  const restored = useState<boolean>('vedic:birthRestored', () => false)

  // ─── localStorage ─────────────────────────────────────────────────────────

  function restore() {
    if (!import.meta.client || restored.value) return
    restored.value = true
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (!raw) return
      const s = JSON.parse(raw) as StoredState
      if (!s?.profile) return
      profile.value = { ...emptyBirthProfile(), ...s.profile }
      // Кэш гороскопа принимаем только если он посчитан для ЭТОГО профиля.
      if (s.horoscope && s.sig && s.sig === signature(profile.value)) {
        horoscope.value = s.horoscope
        horoscopeSig.value = s.sig
      }
    } catch {
      // битый JSON — просто игнорируем, профиль останется пустым
    }
  }

  function persist() {
    if (!import.meta.client) return
    try {
      if (!profile.value) { localStorage.removeItem(STORAGE_KEY); return }
      const s: StoredState = {
        profile: profile.value,
        horoscope: horoscope.value,
        sig: horoscopeSig.value,
      }
      localStorage.setItem(STORAGE_KEY, JSON.stringify(s))
    } catch {
      // приватный режим / переполненная квота — молча продолжаем без кэша
    }
  }

  // Восстановление при первом обращении к композаблу на клиенте.
  restore()

  // ─── Производные ──────────────────────────────────────────────────────────

  const hasProfile = computed(() => {
    const p = profile.value
    if (!p) return false
    if (!p.date) return false
    if (!p.timeUnknown && !p.time) return false
    return Number.isFinite(p.lat) && Number.isFinite(p.lon) && Number.isFinite(p.tz)
  })

  const timeUnknown = computed(() => !!profile.value?.timeUnknown)

  /** Можно ли доверять лагне и домам.
   * При неизвестном времени асцендент проходит все 12 знаков за сутки —
   * дом любой планеты произволен, поэтому UI обязан прятать эти блоки. */
  const lagnaReliable = computed(() => hasProfile.value && !timeUnknown.value)

  /** Накшатры, в которых Луна МОГЛА находиться при рождении.
   * Известное время → ровно одна. Неизвестное → окно ±(макс. скорость / 2)
   * вокруг положения на полдень, что почти всегда даёт 2 кандидата. */
  const moonNakshatraCandidates = computed<number[]>(() => {
    const h = horoscope.value
    if (!h) return []
    if (!timeUnknown.value) return [h.nk.num]
    const half = MOON_MAX_DEG_PER_DAY / 2
    const from = Math.floor((h.moon_sid - half) / NAK_SIZE)
    const to = Math.floor((h.moon_sid + half) / NAK_SIZE)
    const out: number[] = []
    for (let i = from; i <= to; i++) out.push(((i % 27) + 27) % 27 + 1)
    return out
  })

  /** Накшатра Луны под вопросом.
   * — при известном времени: только если API пометил boundary.is_boundary
   *   (Луна ближе 0,25° к границе) — там же смотрим topo.changes и ayas_agree;
   * — при неизвестном: если окно ±12 ч перекрывает границу накшатры. */
  const moonUncertain = computed(() => {
    const h = horoscope.value
    if (!h) return false
    if (timeUnknown.value) return moonNakshatraCandidates.value.length > 1
    const b = h.boundary
    return !!b?.is_boundary || b?.topo?.changes === true || b?.ayas_agree === false
  })

  const moonUncertainReason = computed<'time-unknown' | 'boundary' | null>(() => {
    if (!moonUncertain.value) return null
    return timeUnknown.value ? 'time-unknown' : 'boundary'
  })

  // ─── Действия ─────────────────────────────────────────────────────────────

  /** Сохранить профиль. Кэш гороскопа сбрасывается, если изменилось
   * хоть одно влияющее на расчёт поле. */
  function saveProfile(data: Partial<BirthProfile>) {
    const next: BirthProfile = { ...emptyBirthProfile(), ...(profile.value || {}), ...data }
    // При «время неизвестно» не тащим за собой старое введённое время.
    if (next.timeUnknown) next.time = ''
    const changed = !profile.value || signature(profile.value) !== signature(next)
    profile.value = next
    if (changed) {
      horoscope.value = null
      horoscopeSig.value = null
      error.value = ''
    }
    persist()
    return next
  }

  function clearProfile() {
    profile.value = null
    horoscope.value = null
    horoscopeSig.value = null
    error.value = ''
    if (import.meta.client) {
      try { localStorage.removeItem(STORAGE_KEY) } catch { /* ignore */ }
    }
  }

  /** Принудительный запрос /api/horoscope. */
  async function refresh(): Promise<HoroscopeResult | null> {
    if (!hasProfile.value || !profile.value) {
      error.value = 'Профиль рождения не заполнен'
      return null
    }
    loading.value = true
    error.value = ''
    const sig = signature(profile.value)
    try {
      const res = await api.post<HoroscopeResult>(
        '/api/horoscope',
        birthProfileToPayload(profile.value),
      )
      horoscope.value = res
      horoscopeSig.value = sig
      persist()
      return res
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
      return null
    } finally {
      loading.value = false
    }
  }

  // Чтобы параллельные вызовы fetchHoroscope() с разных компонентов
  // не породили несколько одинаковых запросов.
  let inFlight: Promise<HoroscopeResult | null> | null = null

  /** Идемпотентно: если для текущего профиля данные уже есть — вернёт кэш. */
  async function fetchHoroscope(): Promise<HoroscopeResult | null> {
    if (!hasProfile.value || !profile.value) return null
    const sig = signature(profile.value)
    if (horoscope.value && horoscopeSig.value === sig) return horoscope.value
    if (inFlight) return inFlight
    inFlight = refresh().finally(() => { inFlight = null })
    return inFlight
  }

  return {
    profile,
    horoscope,
    loading,
    error,
    hasProfile,
    timeUnknown,
    lagnaReliable,
    moonUncertain,
    moonUncertainReason,
    moonNakshatraCandidates,
    saveProfile,
    clearProfile,
    fetchHoroscope,
    refresh,
  }
}
