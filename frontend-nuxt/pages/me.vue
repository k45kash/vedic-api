<script setup lang="ts">
// Страница «Обо мне» — натальная карта пользователя на реальных данных.
//
// Источники: профиль рождения (composables/useBirthProfile) + ответ
// POST /api/horoscope + калькуляторы (analyzeChart/dignity) + справочник
// накшатр (content/nakshatras.json, грузится лениво — 279 КБ).
//
// Чего здесь НЕТ и быть не может:
//   • персональных оценок «N/10» — считать не из чего (пометка Б6).
// Лучше пустое место, чем правдоподобная выдумка (docs/SERVICE-IA.md §9).
//
// Проф-глубина (задача 2.9) — три блока под режимом «Астролог»:
//   • наватара-чакра (calculators/tara.ts → taraChakra, уже готова);
//   • аспекты и соединения (content/yogakarma.json через calculators/drishti.ts);
//   • текущие маха- и антар-даша (границы считает бэкенд, трактовки — оттуда же).
// Оба тяжёлых справочника грузятся отдельными чанками и только когда режим
// «Астролог» действительно включён.
import {
  useJyotish, dignity, isGandantaNakshatra,
  nakshatraFromLongitude, NAK_NAMES,
  loadNakshatras, loadPlanetInNakshatra,
  planetAspects, planetConjunctions, dashaReading, drishtiTexts,
} from '~/composables/useJyotish'
import type { AspectRow, ConjunctionRow, DashaReading, PlanetRu } from '~/composables/useJyotish'
import type { HoroPlanet } from '~/composables/useBirthProfile'

definePageMeta({ layout: 'app', middleware: 'auth' })
useHead({ title: 'Обо мне — Jyotish' })

const { setPageHeader } = usePageHeader()
const { isPro } = useAudience()
const {
  profile, horoscope, loading, error, hasProfile,
  lagnaReliable, moonUncertain, moonUncertainReason, moonNakshatraCandidates,
  fetchHoroscope,
} = useBirthProfile()
const { chart, janmaNakshatra, janmaNakshatraName, taraChakraForProfile } = useJyotish()
// Имя `http`, а не `api`: внутри planetRows уже есть локальная `api` —
// строка планеты из ответа гороскопа, и одинаковые имена только путали бы.
const http = useApi()

// ─── Справочники символов ───────────────────────────────────────────────────

const SIGN_GLYPH = ['♈︎', '♉︎', '♊︎', '♋︎', '♌︎', '♍︎', '♎︎', '♏︎', '♐︎', '♑︎', '♒︎', '♓︎']
const PLANET_GLYPH: Record<string, string> = {
  'Солнце': '☉︎', 'Луна': '☾︎', 'Марс': '♂︎', 'Меркурий': '☿︎', 'Юпитер': '♃︎',
  'Венера': '♀︎', 'Сатурн': '♄︎', 'Раху': '☊︎', 'Кету': '☋︎',
}
const SIGN_ABBR: Record<string, string> = {
  'Овен': 'Ови', 'Телец': 'Тел', 'Близнецы': 'Бли', 'Рак': 'Рак',
  'Лев': 'Лев', 'Дева': 'Дев', 'Весы': 'Вес', 'Скорпион': 'Скр',
  'Стрелец': 'Стр', 'Козерог': 'Коз', 'Водолей': 'Вод', 'Рыбы': 'Рыб',
}
// В ответе API гана приходит латиницей, в справочнике накшатр — кириллицей.
const GANA_RU: Record<string, string> = {
  Devata: 'Дэва', Deva: 'Дэва', Manushya: 'Манушья', Rakshasa: 'Ракшаса',
}
const DIGNITY_RU = { exalted: 'экзальтация', own: 'свой знак', debilitated: 'падение' } as const
const DIGNITY_SHORT = { exalted: 'ex', own: 'own', debilitated: 'deb' } as const
const MONTHS_RU = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
]
const ORDINAL_F = ['', '1-я', '2-я', '3-я', '4-я']

// ─── Профиль: гейт и редактирование ─────────────────────────────────────────

const editing = ref(false)
const showForm = computed(() => !hasProfile.value || editing.value)

onMounted(() => { if (hasProfile.value) fetchHoroscope() })

function onSaved() {
  // Форма сама вызвала fetchHoroscope(); закрываем её только при успехе.
  if (!error.value) editing.value = false
}

// ─── Шапка страницы ─────────────────────────────────────────────────────────

const birthLine = computed(() => {
  const p = profile.value
  if (!p?.date) return 'данные рождения не заполнены'
  const [y, m, d] = p.date.split('-').map(Number)
  const date = Number.isFinite(y) ? `${d} ${MONTHS_RU[(m || 1) - 1]} ${y}` : p.date
  const time = p.timeUnknown ? 'время неизвестно' : p.time
  return [[date, time].filter(Boolean).join(', '), p.city].filter(Boolean).join(' · ')
})

// Имя не выдумываем: без него — нейтральный заголовок.
watchEffect(() => {
  const name = profile.value?.name?.trim()
  setPageHeader({
    title: name ? `Добро пожаловать, ${name}` : 'Моя карта',
    subtitle: hasProfile.value ? birthLine.value : 'заполните данные рождения',
  })
})

// ─── Позиции планет ─────────────────────────────────────────────────────────

const apiPlanets = computed<Map<string, HoroPlanet>>(
  () => new Map((horoscope.value?.planets ?? []).map((p) => [p.name, p])),
)

const moon = computed(() => apiPlanets.value.get('Луна') ?? null)
const moonRow = computed(() => chart.value?.find((r) => r.planet === 'Луна') ?? null)

/** При неизвестном времени Луна проходит до ~15,4° за сутки: если она стоит
 * ближе половины этого окна к границе знака, знак Луны тоже под вопросом. */
const moonSignUncertain = computed(() => {
  const m = moon.value
  if (!m || lagnaReliable.value) return false
  return m.deg_in_sign < 7.7 || m.deg_in_sign > 30 - 7.7
})

// ─── Плитки-показатели ──────────────────────────────────────────────────────
// Четвёртая плитка — управитель накшатры (поле nk.lord). Маха-даша, которая
// стояла тут в макете, живёт ниже отдельной секцией: там ей есть что показать
// (границы периода, подпериод, трактовка), а в плитку помещалось одно имя.

const tiles = computed(() => {
  const h = horoscope.value
  if (!h) return []
  const out: Array<{ key: string; label: string; value: string; meta: string; glyph: string }> = []

  out.push(lagnaReliable.value
    ? {
        key: 'lagna',
        label: 'Восходящий знак',
        value: h.lagna.sign_ru,
        meta: `лагна · управитель ${h.lagna.lord}`,
        glyph: SIGN_GLYPH[h.lagna.sign_num - 1] ?? '',
      }
    : {
        key: 'lagna',
        label: 'Восходящий знак',
        value: '—',
        meta: 'нужно время рождения',
        glyph: '',
      })

  const m = moon.value
  if (m) {
    const d = dignity('Луна', m.sign_num)
    out.push({
      key: 'moon-sign',
      label: 'Лунный знак',
      value: m.sign_ru,
      meta: d
        ? `Луна: ${DIGNITY_RU[d]}`
        : `управитель ${moonRow.value?.signData.ruler ?? '—'}`,
      glyph: SIGN_GLYPH[m.sign_num - 1] ?? '',
    })
  }

  out.push({
    key: 'nakshatra',
    label: 'Накшатра Луны',
    value: h.nk.ru,
    meta: `${ORDINAL_F[h.nk.pada] ?? h.nk.pada} пада · гана ${GANA_RU[h.nk.gana] ?? h.nk.gana}`,
    glyph: '☾︎',
  })

  out.push({
    key: 'nak-lord',
    label: 'Управитель накшатры',
    value: h.nk.lord,
    meta: 'по циклу Вимшоттари',
    glyph: PLANET_GLYPH[h.nk.lord] ?? '✧',
  })

  return out
})

// ─── Накшатра Луны: статья (ленивая загрузка 279 КБ) ────────────────────────

const nak = ref<any | null>(null)
const nakLoading = ref(false)

watch(janmaNakshatra, async (no) => {
  if (!no) { nak.value = null; return }
  nakLoading.value = true
  try {
    const all = await loadNakshatras()
    nak.value = all[no - 1] ?? null
  } catch {
    nak.value = null
  } finally {
    nakLoading.value = false
  }
}, { immediate: true })

const nakSub = computed(() => {
  const n = nak.value
  if (!n) return ''
  return [n.dev, n.symbol && `«${n.symbol}»`, n.span].filter(Boolean).join(' · ')
})

const nakMeta = computed(() => {
  const h = horoscope.value
  const n = nak.value
  if (!h) return ''
  const parts: string[] = []
  if (lagnaReliable.value) parts.push(`Лагна: ${h.lagna.sign_ru}`)
  parts.push(`Луна в ${h.nk.ru}, пада ${h.nk.pada}`)
  if (n?.gana) parts.push(`Гана: ${n.gana}`)
  if (n?.purushartha) parts.push(`Цель: ${n.purushartha}`)
  return parts.join(' · ')
})

const nakBadgeIcon = computed(() => {
  const lord = horoscope.value?.nk.lord
  if (lord === 'Луна') return 'moon' as const
  if (lord === 'Солнце') return 'sun' as const
  return 'sparkle' as const
})

const padaText = computed(() => {
  const h = horoscope.value
  const n = nak.value
  if (!h || !Array.isArray(n?.padas)) return ''
  return n.padas[h.nk.pada - 1] ?? ''
})

const gandanta = computed(() => {
  const no = janmaNakshatra.value
  if (!no || !isGandantaNakshatra(no)) return ''
  return typeof nak.value?.gandanta === 'string' ? nak.value.gandanta : ''
})

// ─── Планеты по домам и знакам ──────────────────────────────────────────────
// Ретроградность (вакри) API теперь отдаёт полем retro — показываем факт
// движения, без трактовки: описания из content/retrograde.json пока не
// подключены, а сочинять их нельзя. Узлы у истинного расчёта иногда идут
// прямо, хотя описания традиции называют их «всегда ретроградными» (А2).

/** Сколько планет видно в режиме «Пользователь»; остальные — только «Астролог». */
const SIMPLE_PLANETS = 5

const planetRows = computed(() => {
  const rows = chart.value
  if (!rows) return []
  return rows.map((r, i) => {
    const api = apiPlanets.value.get(r.planet)
    const pos: string[] = []
    // Дом производен от Лагны — при неизвестном времени он бессмыслен.
    if (lagnaReliable.value) pos.push(`${r.house}-й дом`)
    pos.push(r.signData.name)
    if (isPro.value && api) {
      pos.push(api.deg_in_sign_dms)
      pos.push(`${api.nakshatra_ru} ${api.pada}`)
    }
    return {
      key: r.planet,
      name: r.planet,
      glyph: PLANET_GLYPH[r.planet] ?? api?.abbr ?? '',
      position: pos.join(' · '),
      retro: r.retro,
      dignity: r.dignity ? DIGNITY_SHORT[r.dignity] : null,
      houseText: lagnaReliable.value ? r.inHouseText : '',
      signText: r.inSignText,
      pro: i >= SIMPLE_PLANETS,
    }
  })
})

const hiddenPlanets = computed(() => Math.max(0, planetRows.value.length - SIMPLE_PLANETS))

// ─── Планеты в накшатрах (content/planet_in_nakshatra.json, 293 КБ) ─────────
// 27 × 9 = 243 трактовки «планета в накшатре»: синтез природы планеты с шакти,
// деватой и природой стоянки (docs/NAKSHATRA-ARTICLE-MODEL.md §19).
// Файл тяжёлый, поэтому: (1) только динамический import через loadPlanetInNakshatra,
// (2) запрос уходит не при открытии страницы, а когда секция доезжает до экрана.

interface PlanetInNak {
  planet: string
  relation: string
  core: string
  notes: string[]
  special: string | null
}

const pinData = ref<Record<string, PlanetInNak[]> | null>(null)
const pinLoading = ref(false)
const pinFailed = ref(false)
/** Маячок перед секцией: по его появлению во вьюпорте стартует загрузка. */
const pinAnchor = ref<HTMLElement | null>(null)

async function loadPin() {
  if (pinData.value || pinLoading.value) return
  pinLoading.value = true
  pinFailed.value = false
  try {
    pinData.value = await loadPlanetInNakshatra()
  } catch {
    pinFailed.value = true
  } finally {
    pinLoading.value = false
  }
}

// Триггер считаем по геометрии, а не через IntersectionObserver: секция может
// оказаться в нулевом/скрытом вьюпорте (превью, фоновая вкладка), и тогда IO
// не сработает вовсе — пользователь остался бы с пустой секцией навсегда.
let pinCheckedAt = 0

function pinMaybeLoad() {
  if (pinData.value || pinLoading.value) { pinStopWatching(); return }
  const el = pinAnchor.value
  if (!el) return
  const top = el.getBoundingClientRect().top
  const limit = (window.innerHeight || document.documentElement.clientHeight || 0) + 300
  if (top > limit) return
  pinStopWatching()
  loadPin()
}

// Троттлим по времени, а не через requestAnimationFrame: в фоновой вкладке rAF
// не вызывается, и загрузка молча не состоялась бы.
function pinOnScroll() {
  const now = Date.now()
  if (now - pinCheckedAt < 120) return
  pinCheckedAt = now
  pinMaybeLoad()
}

function pinStopWatching() {
  if (!import.meta.client) return
  window.removeEventListener('scroll', pinOnScroll)
  window.removeEventListener('resize', pinOnScroll)
}

watch(pinAnchor, (el) => {
  if (!import.meta.client) return
  pinStopWatching()
  if (!el || pinData.value) return
  window.addEventListener('scroll', pinOnScroll, { passive: true })
  window.addEventListener('resize', pinOnScroll, { passive: true })
  // Секция стоит внизу длинной страницы: при открытии она почти всегда за
  // экраном и 293 КБ не запрашиваются. Но на очень высоком экране она может
  // быть видна сразу — тогда грузим честно сразу.
  nextTick(pinMaybeLoad)
})

onBeforeUnmount(pinStopWatching)

/** Отношение планеты к управителю накшатры → тон чипа и короткая подпись. */
function relationChip(relation: string): { variant: 'good' | 'bad' | 'neutral'; label: string } {
  const r = (relation || '').toLowerCase()
  if (r.startsWith('своя')) return { variant: 'good', label: 'своя накшатра' }
  if (r.startsWith('дружествен')) return { variant: 'good', label: 'дружественный управитель' }
  if (r.startsWith('напряж')) return { variant: 'bad', label: 'напряжённый управитель' }
  return { variant: 'neutral', label: 'нейтральный управитель' }
}

// Сводим написания к общему виду: «Уттарашадха» (API) ↔ «Уттара Ашадха» (content),
// «Пурвабхадра» ↔ «Пурва Бхадрапада» — отсюда схлопывание пробелов и удвоений
// плюс сравнение по префиксу ниже.
const normNak = (s: string) => s
  .toLowerCase().replace(/ё/g, 'е').replace(/[^а-я]/g, '')
  .replace(/(.)\1+/g, '$1')

/** Ключ накшатры в справочнике (1..27) для планеты из ответа API.
 * Считаем из сидерической долготы — это точно и не зависит от того, как API
 * пишет имя («Пурвабхадра» против «Пурва Бхадрапада» в content/). Имя — только
 * запасной путь, если долготы вдруг не окажется. */
function nakNoOf(p: HoroPlanet): number | null {
  if (Number.isFinite(p.sid)) return nakshatraFromLongitude(p.sid).no
  const a = normNak(p.nakshatra_ru ?? '')
  if (!a) return null
  const i = NAK_NAMES.findIndex((n) => {
    const b = normNak(n)
    return b === a || b.startsWith(a) || a.startsWith(b)
  })
  return i >= 0 ? i + 1 : null
}

/** В простом режиме показываем только светила: Солнце и Луна — то, что человек
 * про себя действительно читает. Остальные семь — проф-глубина («Астролог»),
 * как и задумано в модели статьи накшатры. */
const PIN_SIMPLE = new Set(['Солнце', 'Луна'])

const pinRows = computed(() => {
  const h = horoscope.value
  const data = pinData.value
  if (!h || !data) return []
  const out: Array<{
    key: string; name: string; glyph: string; position: string
    chip: { variant: 'good' | 'bad' | 'neutral'; label: string }
    core: string; notes: string[]; special: string; pro: boolean
  }> = []
  for (const p of h.planets) {
    if (!p.available) continue
    const no = nakNoOf(p)
    if (!no) continue
    const rec = (data[String(no)] ?? []).find((r) => r.planet === p.name)
    // Трактовки для пары «планета × накшатра» нет — строку просто не рисуем.
    if (!rec?.core) continue
    out.push({
      key: p.name,
      name: p.name,
      glyph: PLANET_GLYPH[p.name] ?? p.abbr ?? '',
      position: `${NAK_NAMES[no - 1]} · ${ORDINAL_F[p.pada] ?? p.pada} пада`,
      chip: relationChip(rec.relation),
      core: rec.core,
      notes: Array.isArray(rec.notes) ? rec.notes : [],
      special: rec.special ?? '',
      pro: !PIN_SIMPLE.has(p.name),
    })
  }
  return out
})

const pinHidden = computed(() => pinRows.value.filter((r) => r.pro).length)

// ─── Проф-глубина: наватара-чакра ───────────────────────────────────────────
// Сама чакра считается синхронно (tara.ts статичен, 19 КБ уже в бандле).
// Единственное, чего не хватает для подсветки, — накшатра Луны СЕГОДНЯ:
// её отдаёт /api/calendar. Запрос уходит только в режиме «Астролог» и только
// один раз; не получилось — блок остаётся без подсветки, а не пропадает.

interface ApiNakTransit { nk_num: number; ru: string; dt_start: string; dt_end: string }

const todayNak = ref<{ no: number; ru: string } | null>(null)
let todayNakRequested = false

async function loadTodayNak() {
  if (todayNakRequested || !import.meta.client) return
  const p = profile.value
  // Место для транзита Луны роли почти не играет (накшатра — величина
  // геоцентрическая), но берём профиль, если он есть: так же, как на «Сегодня».
  const lat = Number.isFinite(p?.lat) ? p!.lat : 55.7558
  const lon = Number.isFinite(p?.lon) ? p!.lon : 37.6176
  const tz = Number.isFinite(p?.tz) ? p!.tz : 3
  todayNakRequested = true
  const now = new Date()
  const iso = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  try {
    const rows = await http.post<ApiNakTransit[]>('/api/calendar', {
      date_start: iso(now),
      date_end: iso(new Date(now.getTime() + 86400_000)),
      tz, lat, lon,
    })
    const hit = (rows ?? []).find((r) => new Date(r.dt_start) <= now && now < new Date(r.dt_end))
      ?? rows?.[0]
    todayNak.value = hit ? { no: hit.nk_num, ru: hit.ru } : null
  } catch {
    todayNak.value = null // подсветки не будет — это честнее, чем угадывать
  }
}

// ─── Проф-глубина: аспекты, соединения, периоды (yogakarma.json, 79 КБ) ─────

const aspects = ref<AspectRow[]>([])
const conjunctions = ref<ConjunctionRow[]>([])
const dasha = ref<DashaReading | null>(null)
const ykTexts = ref<{ aspectsNote: string; aspectsSrc: string; conjunctionsSrc: string; dashasSrc: string } | null>(null)
const ykLoading = ref(false)
const ykFailed = ref(false)

/** Планеты карты для расчёта аспектов: имя + знак, больше ничего не нужно. */
const drishtiInput = computed(() =>
  (horoscope.value?.planets ?? [])
    .filter((p) => p.available)
    .map((p) => ({ name: p.name as PlanetRu, sign: p.sign_num })),
)

/** Текущий период Вимшоттари из ответа /api/horoscope.
 * Поле появилось на бэкенде позже описания HoroscopeResult, поэтому читаем
 * через каст — структура проверена живым ответом (см. отчёт). */
const dashaCurrent = computed<any | null>(() => (horoscope.value as any)?.dasha_current ?? null)

async function loadYogakarma() {
  if (ykLoading.value || !drishtiInput.value.length) return
  ykLoading.value = true
  ykFailed.value = false
  try {
    // Дома считаем только при достоверной Лагне — иначе номера домов
    // произвольны, и в аспектах останутся одни знаки.
    const lagna = lagnaReliable.value ? horoscope.value?.lagna.sign_num ?? null : null
    const [a, c, t] = await Promise.all([
      planetAspects(drishtiInput.value, lagna),
      planetConjunctions(drishtiInput.value, lagna),
      drishtiTexts(),
    ])
    aspects.value = a
    conjunctions.value = c
    ykTexts.value = t
    const d = dashaCurrent.value
    dasha.value = d
      ? await dashaReading(d.mahadasha?.lord_id ?? null, d.antardasha?.lord_id ?? null)
      : null
  } catch {
    ykFailed.value = true
  } finally {
    ykLoading.value = false
  }
}

// Проф-блоки в вёрстке всегда присутствуют (их прячет CSS), поэтому грузить
// их данные надо не при монтировании, а при реальном включении режима.
watch([isPro, horoscope], ([pro, h]) => {
  if (!pro || !h) return
  loadTodayNak()
  loadYogakarma()
}, { immediate: true })

// ─── Дома (только при достоверной Лагне) ────────────────────────────────────

const houseRows = computed(() => {
  const h = horoscope.value
  if (!h || !lagnaReliable.value) return []
  const byHouse = new Map<number, string[]>()
  for (const p of h.planets) {
    if (!p.available) continue
    const list = byHouse.get(p.house) ?? []
    list.push(p.name)
    byHouse.set(p.house, list)
  }
  return (h.lagna.houses ?? []).map((hh) => ({
    ...hh,
    planets: byHouse.get(hh.house) ?? [],
  }))
})

// Северо-индийская карта: 12 секторов внутри квадрата 220×220.
const CHART_POINTS: Record<string, [number, number]> = {
  O: [110, 110], TL: [4, 4], TR: [216, 4], BR: [216, 216], BL: [4, 216],
  TC: [110, 4], RC: [216, 110], BC: [110, 216], LC: [4, 110],
  I1: [57, 57], I2: [163, 57], I3: [163, 163], I4: [57, 163],
}
const CHART_CELLS: string[][] = [
  ['O', 'I2', 'TC', 'I1'], ['TL', 'TC', 'I1'], ['TL', 'I1', 'LC'], ['O', 'I4', 'LC', 'I1'],
  ['LC', 'I4', 'BL'], ['I4', 'BC', 'BL'], ['O', 'I3', 'BC', 'I4'], ['I3', 'BR', 'BC'],
  ['RC', 'BR', 'I3'], ['O', 'I2', 'RC', 'I3'], ['TR', 'RC', 'I2'], ['TC', 'TR', 'I2'],
]

const chartCells = computed(() => {
  const rows = houseRows.value
  if (!rows.length) return []
  return CHART_CELLS.map((names, i) => {
    const pts = names.map((n) => CHART_POINTS[n])
    const cx = pts.reduce((s, p) => s + p[0], 0) / pts.length
    const cy = pts.reduce((s, p) => s + p[1], 0) / pts.length
    const house = rows[i]
    return {
      key: i + 1,
      poly: pts.map((p) => p.join(',')).join(' '),
      isLagna: i === 0,
      cx,
      cy,
      label: `${i + 1} · ${SIGN_ABBR[house?.sign_ru ?? ''] ?? ''}`,
      glyphs: (house?.planets ?? []).map((n) => PLANET_GLYPH[n] ?? n.slice(0, 2)).join(' '),
    }
  })
})

// ─── Готовые тексты из content/ (задача 2.8) ────────────────────────────────
// Дисклеймеры достоверности и вводные абзацы не пишем в разметке: они живут
// в content/disclaimers.json и content/ui_texts.json, а сюда попадают по ключу.

const { disclaimer } = useDisclaimers()
const { t } = useUiTexts()
</script>

<template>
  <section class="panel" aria-label="Обо мне">
    <!-- ─── Гейт: профиля нет или его правят ─────────────────────────────── -->
    <template v-if="showForm">
      <UiCard
        title="Данные рождения"
        subtitle="Дата, время и место рождения — по ним строится вся карта. Без них показывать нечего."
      >
        <div class="profile-form">
          <BirthProfileForm
            :submit-label="hasProfile ? 'Сохранить и пересчитать' : 'Построить карту'"
            @saved="onSaved"
          />
        </div>
        <p v-if="hasProfile" style="margin:14px 0 0">
          <a href="#" @click.prevent="editing = false">← Вернуться к карте</a>
        </p>
      </UiCard>

      <UiDisclaimer>
        Если точное время рождения неизвестно — отметьте это в форме. Накшатра Луны
        и панчанга останутся рабочими, а лагна и дома будут честно недоступны,
        вместо приблизительных.
      </UiDisclaimer>
    </template>

    <!-- ─── Карта ────────────────────────────────────────────────────────── -->
    <template v-else>
      <UiCard v-if="error" title="Не удалось построить карту">
        <p style="margin:0 0 14px;font-size:14px">{{ error }}</p>
        <UiButton @click="fetchHoroscope()">Повторить</UiButton>
      </UiCard>

      <UiCard v-else-if="!horoscope">
        <p class="hint" style="margin:0">
          {{ loading ? 'Считаем карту…' : 'Карта ещё не рассчитана.' }}
        </p>
      </UiCard>

      <template v-else>
        <div class="grid-4">
          <UiTile
            v-for="tile in tiles"
            :key="tile.key"
            :label="tile.label"
            :value="tile.value"
            :meta="tile.meta"
            :glyph="tile.glyph"
          />
        </div>

        <p style="margin:14px 0 0">
          <a href="#" @click.prevent="editing = true">Изменить данные рождения</a>
        </p>

        <!-- режим «по Луне»: лагна и дома недоступны -->
        <UiDisclaimer v-if="!lagnaReliable" tone="warn">
          Время рождения не указано — <b>асцендент (лагна) и дома рассчитать нельзя</b>:
          за сутки лагна проходит все двенадцать знаков, поэтому любой дом был бы
          произвольным. Карта показана «по Луне»: накшатра, знаки планет и
          достоинства остаются рабочими.
        </UiDisclaimer>

        <!-- накшатра Луны под вопросом -->
        <UiDisclaimer v-if="moonUncertain">
          <template v-if="moonUncertainReason === 'time-unknown'">
            Без времени рождения положение Луны определено с точностью до суток,
            поэтому накшатра может оказаться другой — вероятнее всего одной из:
            <b>{{ moonNakshatraCandidates.join(', ') }}</b> (номера по порядку).
            <template v-if="moonSignUncertain">
              По той же причине под вопросом и знак Луны — она стоит близко к границе знака.
            </template>
            Уточните время рождения, и неопределённость снимется.
          </template>
          <template v-else>
            Луна на момент рождения стоит у самой границы накшатры, поэтому у разных
            аянамш и при поправке на место наблюдения накшатра может отличаться.
            Это стоит перепроверить с астрологом.
          </template>
        </UiDisclaimer>

        <!-- ─── Накшатра ────────────────────────────────────────────────── -->
        <UiSectionHead title="Ваша накшатра" />
        <div class="grid-53">
          <UiCard>
            <UiHero
              :no="String(horoscope.nk.num).padStart(2, '0')"
              :name="horoscope.nk.ru"
              :sub="nakSub"
              :meta="nakMeta"
            >
              <template #badge>
                <UiBadge :icon="nakBadgeIcon">управитель {{ horoscope.nk.lord }}</UiBadge>
              </template>
              <template v-if="nak?.shakti">
                <b>Шакти:</b> {{ nak.shakti }}
              </template>
              <template v-else-if="nakLoading">
                <span class="hint">Загружаем описание накшатры…</span>
              </template>
              <template #footer>
                <span class="hint">
                  Полная статья накшатры (катха, божество, пады, карьера, упайи)
                  появится в справочнике — раздел в работе.
                </span>
              </template>
            </UiHero>

            <div v-if="nak" style="margin-top:16px">
              <UiKv k="Символ" :v="nak.symbol" />
              <UiKv k="Божество" :v="nak.devata" />
              <UiKv k="Гана" :v="nak.gana" />
              <UiKv k="Управитель" :v="nak.ruler" />
              <UiKv k="Стихия" :v="nak.element" />
            </div>

            <UiProOnly>
              <div v-if="nak" style="margin-top:14px;border-top:1px solid var(--line);padding-top:14px">
                <UiKv k="Варна" :v="nak.varna" />
                <UiKv k="Йони" :v="nak.yoni" />
                <UiKv k="Доша" :v="nak.dosha" />
                <UiKv k="Природа" :v="nak.nature" />
                <p v-if="padaText" class="hint" style="margin:12px 0 0">{{ padaText }}</p>
                <!-- Доша — то самое поле, из которого читается нади (А1). Экрана
                     совместимости в кабинете пока нет, поэтому пометка стоит там,
                     где нади вообще упоминается. -->
                <UiMethodNote id="А1" />
              </div>
            </UiProOnly>
          </UiCard>

          <UiMantra
            v-if="nak?.devata_mantra_skt"
            title="Ваша мантра и упайя"
            :devanagari="nak.devata_mantra_skt"
            :translit="nak.devata_mantra_iast"
            :note="`${nak.devata_mantra_ru} — мантра божества накшатры ${horoscope.nk.ru}`"
          >
            <p v-if="nak.upaya" style="margin:14px 0 0;font-size:13.5px;line-height:1.55">
              {{ nak.upaya }}
            </p>
          </UiMantra>
          <UiCard v-else>
            <p class="hint" style="margin:0">
              {{ nakLoading ? 'Загружаем мантру накшатры…' : 'Мантра появится вместе со справочником накшатр.' }}
            </p>
          </UiCard>
        </div>

        <UiDisclaimer v-if="gandanta">
          {{ gandanta }} Ганданта — узел перехода между стихиями: тема глубокой
          перестройки и роста, а не приговор. Толкование лучше разобрать с астрологом.
        </UiDisclaimer>
        <p v-if="nak?.note" class="hint" style="margin:10px 0 0">{{ nak.note }}</p>

        <!-- ─── Планеты ─────────────────────────────────────────────────── -->
        <UiSectionHead>
          Планеты по домам и знакам
          <UiMethodNote id="А2" />
        </UiSectionHead>
        <UiCard>
          <UiProRow
            v-for="row in planetRows"
            :key="row.key"
            :name="row.name"
            :glyph="row.glyph"
            :position="row.position"
            :dignity="row.dignity"
            :pro="row.pro"
          >
            <template #position>
              {{ row.position }}
              <UiChip v-if="row.retro" variant="neutral" class="pin-chip">вакри (ретроградна)</UiChip>
            </template>
            {{ row.houseText || row.signText }}
            <UiProOnly v-if="row.houseText && row.signText">
              <p class="hint" style="margin:8px 0 0">{{ row.signText }}</p>
            </UiProOnly>
          </UiProRow>

          <UiProOnly>
            <p class="hint" style="margin:14px 0 0">
              <template v-if="lagnaReliable">Дома — Whole Sign от Лагны. </template>
              Достоинство определяется по знаку, без точного градуса экзальтации.
              Ретроградность (вакри) показана как факт движения; расчёт ведётся
              по истинному узлу, поэтому Раху и Кету у нас иногда идут прямо,
              хотя традиция называет их «всегда ретроградными».
            </p>
          </UiProOnly>
          <p v-if="hiddenPlanets" class="hint hint--simple" style="margin:14px 0 0">
            Ещё {{ hiddenPlanets }} планет и карта домов — в режиме «Астролог».
          </p>
        </UiCard>
        <UiDisclaimer :entry="disclaimer('placements')" />

        <!-- ─── Планеты в накшатрах (243 трактовки, ленивые 293 КБ) ──────── -->
        <div ref="pinAnchor" class="pin-anchor" aria-hidden="true" />
        <UiSectionHead title="Планеты в накшатрах" />
        <UiCard>
          <p class="hint" style="margin:0 0 16px">
            Не «планета в знаке», а планета в той стоянке, где она реально стоит:
            её природа проходит через шакти, девату и природу накшатры, а тон задаёт
            отношение к управителю стоянки.
          </p>

          <template v-if="pinRows.length">
            <UiProRow
              v-for="row in pinRows"
              :key="row.key"
              :name="row.name"
              :glyph="row.glyph"
              :pro="row.pro"
            >
              <template #position>
                {{ row.position }}
                <UiChip :variant="row.chip.variant" class="pin-chip">{{ row.chip.label }}</UiChip>
              </template>

              {{ row.core }}

              <UiProOnly v-if="row.special || row.notes.length">
                <p v-if="row.special" class="pin-special">★ {{ row.special }}</p>
                <ul v-if="row.notes.length" class="pin-notes">
                  <li v-for="(n, i) in row.notes" :key="i">{{ n }}</li>
                </ul>
              </UiProOnly>

              <p v-if="row.key === 'Луна' && moonUncertain" class="hint" style="margin:8px 0 0">
                Накшатра Луны под вопросом (см. выше) — вместе с ней под вопросом
                и эта трактовка.
              </p>
            </UiProRow>

            <p v-if="pinHidden" class="hint hint--simple" style="margin:14px 0 0">
              Ещё {{ pinHidden }} планет в своих накшатрах — в режиме «Астролог».
              Там же — отношение к управителю подробно и особые точки.
            </p>
          </template>

          <template v-else>
            <p class="hint" style="margin:0">
              <template v-if="pinLoading">Загружаем трактовки «планета в накшатре»…</template>
              <template v-else-if="pinFailed">Не удалось загрузить справочник трактовок.</template>
              <template v-else-if="pinData">
                Для положений планет в этой карте трактовок в справочнике нет.
              </template>
              <template v-else>
                Справочник трактовок (293 КБ) подгружается отдельно — он не нужен
                остальной странице.
              </template>
            </p>
            <p v-if="!pinLoading && !pinData" style="margin:14px 0 0">
              <UiButton variant="ghost" @click="loadPin()">
                {{ pinFailed ? 'Повторить' : 'Показать трактовки' }}
              </UiButton>
            </p>
          </template>
        </UiCard>
        <UiDisclaimer>
          Трактовки «планета в накшатре» — синтез (природа планеты × шакти, девата
          и природа накшатры × отношение к управителю), а не цитата из трактата:
          рабочая версия для сверки с учителем. Особые точки экзальтации и падения —
          классика. Полная картина складывается из всей карты, а не из одной строки.
        </UiDisclaimer>

        <!-- ─── Проф-глубина: наватара-чакра ─────────────────────────────── -->
        <UiProOnly v-if="taraChakraForProfile && janmaNakshatraName">
          <UiSectionHead flag="Астролог">
            Наватара-чакра
            <UiMethodNote id="А8" />
          </UiSectionHead>
          <UiCard>
            <p class="hint" style="margin:0 0 16px">
              Двадцать семь накшатр, разложенные от вашей джанма-накшатры по
              девяти тарам в три цикла. Тара повторяется каждые девять накшатр,
              поэтому у каждой накшатры своё место в вашей личной сетке — от неё
              и считается тара-бала дня.
            </p>
            <ProNavatara
              :cells="taraChakraForProfile"
              :janma-name="janmaNakshatraName"
              :today-no="todayNak?.no ?? null"
              :today-name="todayNak?.ru"
              :janma-uncertain="moonUncertain"
            />
            <UiDisclaimer>
              Убывание силы неблагоприятных тар от цикла к циклу (Джанмаркша →
              Кармаркша → Адханаркша) и правило 27-й накшатры — методы школы,
              из которой пришли эти данные, а не общий канон: часть школ
              называет в этой роли 22-ю или 23-ю накшатру.
            </UiDisclaimer>
          </UiCard>
        </UiProOnly>

        <!-- ─── Проф-глубина: аспекты и соединения ───────────────────────── -->
        <UiProOnly>
          <UiSectionHead flag="Астролог">
            Аспекты и соединения
            <UiMethodNote id="А12" />
          </UiSectionHead>
          <UiCard>
            <!-- Вводный абзац — из content/ui_texts.json (yogakarma_intro):
                 он описывает ровно эти три слоя, включая периоды ниже. -->
            <p v-if="t('yogakarma_intro')" class="hint" style="margin:0 0 10px">
              {{ t('yogakarma_intro') }}
            </p>
            <p class="hint" style="margin:0 0 16px">
              Дришти — «взгляд» планеты: все планеты смотрят на 7-й дом от себя,
              у Марса, Юпитера и Сатурна есть дополнительные особые аспекты.
              Счёт ведётся по знакам в раскладке Whole Sign.
            </p>

            <ProAspects
              v-if="aspects.length"
              :rows="aspects"
              :conjunctions="conjunctions"
              :lagna-reliable="lagnaReliable"
              :note="ykTexts?.aspectsNote"
              :glyphs="PLANET_GLYPH"
            />
            <p v-else class="hint" style="margin:0">
              <template v-if="ykLoading">Загружаем справочник аспектов…</template>
              <template v-else-if="ykFailed">Не удалось загрузить справочник аспектов.</template>
              <template v-else>Справочник аспектов (79 КБ) подгружается отдельным файлом.</template>
            </p>
            <p v-if="ykFailed" style="margin:14px 0 0">
              <UiButton variant="ghost" @click="loadYogakarma()">Повторить</UiButton>
            </p>

            <UiDisclaimer>
              Показаны только <b>полные</b> аспекты и только по знакам: градусной
              силы аспекта (дришти-бала) и частичных аспектов в данных нет, поэтому
              их здесь нет тоже. Соединением считается стоянка в одном знаке — без
              орбиса в градусах, поэтому планеты в разных концах знака попадут
              в одну строку. Пятый и девятый аспекты Раху и Кету помечены «по ряду
              школ» — так они записаны в самом справочнике.
            </UiDisclaimer>
            <UiDisclaimer :entry="disclaimer('aspects')" />
            <UiDisclaimer v-if="conjunctions.length" :entry="disclaimer('conjunctions')" />
            <p v-if="ykTexts?.aspectsSrc" class="hint" style="margin:10px 0 0">
              Источник: {{ ykTexts.aspectsSrc }}
            </p>
          </UiCard>
        </UiProOnly>

        <!-- ─── Проф-глубина: текущий период Вимшоттари ──────────────────── -->
        <UiProOnly v-if="dashaCurrent?.mahadasha">
          <UiSectionHead flag="Астролог">
            Периоды Вимшоттари
            <UiMethodNote id="А3" />
          </UiSectionHead>
          <UiCard>
            <ProDasha
              :maha="dashaCurrent.mahadasha"
              :antar="dashaCurrent.antardasha"
              :reading="dasha"
              :as-of="dashaCurrent.as_of"
              :moon-uncertain="moonUncertain"
            />
            <p v-if="ykLoading && !dasha" class="hint" style="margin:12px 0 0">
              Загружаем трактовки периодов…
            </p>
            <UiDisclaimer>
              Даши — часть натальной карты, а не отдельный «календарь событий»:
              период окрашивает темы своей планеты, а что именно произойдёт,
              зависит от её силы, дома и всей карты. Здесь показан только текущий
              период с подпериодом — полное дерево периодов появится вместе
              с разделом карты.
            </UiDisclaimer>
            <UiDisclaimer :entry="disclaimer('dashas')" />
            <UiDisclaimer v-if="dashaCurrent?.antardasha" :entry="disclaimer('antardashas')" />
          </UiCard>
        </UiProOnly>

        <!-- ─── Дома (проф-глубина, только при достоверной Лагне) ────────── -->
        <UiProOnly v-if="lagnaReliable">
          <UiSectionHead title="Карта домов" flag="Астролог" />
          <div class="grid-2">
            <UiCard>
              <svg
                class="chart"
                viewBox="0 0 220 220"
                role="img"
                :aria-label="`Карта домов, северный стиль: лагна в знаке ${horoscope.lagna.sign_ru}`"
              >
                <rect
                  x="4" y="4" width="212" height="212" rx="4"
                  fill="none" stroke="var(--line-2)" stroke-width="1.4"
                />
                <template v-for="cell in chartCells" :key="cell.key">
                  <polygon
                    :points="cell.poly"
                    fill="none"
                    :stroke="cell.isLagna ? 'var(--accent)' : 'var(--line-2)'"
                  />
                  <text
                    :x="cell.cx" :y="cell.cy - 3"
                    text-anchor="middle" font-size="7.5"
                    :fill="cell.isLagna ? 'var(--accent)' : 'var(--muted)'"
                  >{{ cell.label }}</text>
                  <text
                    v-if="cell.glyphs"
                    :x="cell.cx" :y="cell.cy + 8"
                    text-anchor="middle" font-size="10" fill="var(--ink)"
                  >{{ cell.glyphs }}</text>
                </template>
              </svg>
              <p class="hint" style="text-align:center;margin:12px 0 0">
                Северный стиль · дома Whole Sign от Лагны {{ horoscope.lagna.sign_ru }}
                ({{ horoscope.lagna.deg_in_sign_dms }})
              </p>
            </UiCard>

            <UiCard title="Дома и знаки" :heading-level="3">
              <UiKv v-for="h in houseRows" :key="h.house" :k="`${h.house}-й дом`">
                {{ h.sign_ru }} · упр. {{ h.lord }}<template v-if="h.planets.length">
                  · {{ h.planets.join(', ') }}</template>
              </UiKv>
            </UiCard>
          </div>
          <UiDisclaimer :entry="disclaimer('chart-full')" />
        </UiProOnly>

        <UiDisclaimer :entry="disclaimer('chart-analysis')" />

        <!-- Тексты кабинета — пересказ классики, поэтому ссылка на
             первоисточники доступна с экрана, а не только из документации. -->
        <UiSources />
      </template>
    </template>
  </section>
</template>

<style scoped>
/* Маячок ленивой загрузки секции «Планеты в накшатрах»: должен иметь ненулевую
   высоту, иначе IntersectionObserver в части браузеров его не замечает. */
.pin-anchor { height: 1px; margin-bottom: -1px; }

.pin-chip { margin-left: 6px; vertical-align: middle; }
.pin-special {
  margin: 8px 0 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--gold-ink, var(--muted));
}
.pin-notes {
  margin: 8px 0 0;
  padding-left: 18px;
  font-size: 12.5px;
  line-height: 1.55;
  color: var(--muted);
}
.pin-notes li + li { margin-top: 4px; }

/* Подсказка «…в режиме Астролог» нужна только пользовательскому режиму —
   в прототипе это делал me-more-hint через JS. */
.vd-app.is-pro .hint--simple { display: none; }

/* BirthProfileForm свёрстан на глобальных классах старой раскладки
   (layouts/default.vue), которых в оболочке кабинета нет, — приводим форму
   к токенам кабинета локально, не трогая сам компонент. */
.profile-form :deep(form.birth) {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.profile-form :deep(.row) { display: flex; gap: 16px; flex-wrap: wrap; }
.profile-form :deep(.field) {
  display: flex; flex-direction: column; gap: 6px; flex: 1; min-width: 140px;
}
.profile-form :deep(.field label),
.profile-form :deep(label) {
  font-size: 12.5px; font-weight: 500; color: var(--muted);
}
.profile-form :deep(input[type='text']),
.profile-form :deep(input[type='date']),
.profile-form :deep(input[type='time']),
.profile-form :deep(input[type='number']) {
  padding: 10px 13px;
  border-radius: var(--r-sm, 10px);
  border: 1px solid var(--line);
  background: var(--surface-2);
  color: var(--ink);
  font: inherit;
  font-size: 14px;
  outline: none;
}
.profile-form :deep(input:focus) { border-color: var(--accent-line); }
.profile-form :deep(.note) { font-size: 13px; line-height: 1.5; color: var(--muted); }
.profile-form :deep(.error) { font-size: 13px; color: var(--bad, #c0392b); }
.profile-form :deep(button.primary) {
  align-self: flex-start;
  padding: 10px 22px;
  border: 0;
  border-radius: var(--r-pill, 999px);
  background: var(--accent);
  color: #fff;
  font: inherit;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
}
.profile-form :deep(button.primary:disabled) { opacity: .55; cursor: not-allowed; }
</style>
