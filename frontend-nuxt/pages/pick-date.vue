<script setup lang="ts">
// Страница «Подобрать дату» — мухурта под конкретное событие (PLAN §2.5,
// SERVICE-IA §4.3).
//
// Источники данных:
//   POST /api/calendar  → транзиты Луны по накшатрам за весь диапазон
//   POST /api/panchang  → титхи за весь диапазон + восход/закат каждых суток
//   calculators/event-picker.ts (через useJyotish, лениво) → scoreEvent/listEvents
//   utils/kalam.ts → Раху / Гулика / Ямаганда выбранного дня
//
// ОПТИМИЗАЦИЯ ЗАПРОСОВ: оба эндпоинта принимают период, поэтому на весь
// диапазон уходит РОВНО ДВА запроса, а не два на каждый день. Ответы кэшируются
// по ключу «диапазон + место»: смена события пересчитывает баллы локально,
// без похода в сеть.
//
// ЧЕГО ЗДЕСЬ НЕТ И БЫТЬ НЕ ДОЛЖНО: «энергии дня», рейтингов по сферам, даш.
// Йогу и карану API не считает — фактор йоги (вес 1) в модели просто не
// участвует, и об этом сказано прямо, а не подменяется выдумкой.
import {
  useJyotish, listEvents, scoreEvent, splitTithi, weekdayRu,
} from '~/composables/useJyotish'
import type {
  EventDef, EventScoreResult, EventVerdictLevel, Paksha, ScoreLine, WeekdayRu,
} from '~/composables/useJyotish'
import { dayKalams, type KalamKey, type KalamPeriod } from '~/utils/kalam'

definePageMeta({ layout: 'app', middleware: 'auth' })
useHead({ title: 'Подобрать дату — Jyotish' })

// ─── Типы ответов API (проверены живыми запросами, см. отчёт) ────────────────

interface ApiTithi {
  num: number          // сквозной 1..30
  name: string         // «Экадаши»
  paksha: string       // «Шукла» | «Кришна»
  type: string         // Нанда / Бхадра / Джая / Рикта / Пурна
  quality: string
  dt_start: string
  dt_end: string
}
interface ApiDay {
  date: string         // YYYY-MM-DD
  dt_sunrise: string
  dt_sunset: string
  day_dur_h: number
}
interface ApiPanchang { tithis: ApiTithi[]; days: ApiDay[] }
interface ApiNakTransit {
  nk_num: number       // 1..27
  name: string
  ru: string
  lord: string
  gana: string
  dt_start: string
  dt_end: string
}

// ─── Формат ─────────────────────────────────────────────────────────────────

const MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
const MONTHS_SHORT = ['янв', 'фев', 'мар', 'апр', 'мая', 'июн',
  'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
const WEEKDAY_SHORT = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб']

const pad = (n: number) => String(n).padStart(2, '0')
const fmtTime = (d: Date) => `${pad(d.getHours())}:${pad(d.getMinutes())}`
const fmtDate = (d: Date) => `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`
const fmtShort = (d: Date) => `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]}`
const toIso = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

/** API отдаёт локальное время места без смещения — new Date() читает его как
 * локальное время браузера. Для сравнений внутри суток это ровно то, что нужно. */
const at = (iso: string) => new Date(iso)
/** «2026-07-25» → полдень этих суток: безопасно для getDay() в любой зоне. */
const noonOf = (iso: string) => new Date(`${iso}T12:00:00`)

function addDays(d: Date, n: number) {
  const x = new Date(d)
  x.setDate(x.getDate() + n)
  return x
}
function startOfDay(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}
function daysBetween(aIso: string, bIso: string) {
  const a = noonOf(aIso).getTime()
  const b = noonOf(bIso).getTime()
  return Math.round((b - a) / 86_400_000)
}
/** «1 событие / 2 события / 5 событий» — русские формы числительного. */
function plural(n: number, one: string, few: string, many: string) {
  const m10 = n % 10
  const m100 = n % 100
  if (m10 === 1 && m100 !== 11) return one
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few
  return many
}

// ─── Группировка 33 событий ────────────────────────────────────────────────
// В events_muhurta.json категорий нет — только id / label / name / icon.
// Поэтому группы заданы здесь, по смыслу дела. Любое событие, не попавшее
// в список, уедет в «Прочее»: экран не должен молча терять пункты, если
// в справочник добавят новое дело.

const EVENT_GROUPS: Array<{ title: string; ids: string[] }> = [
  { title: 'Семья и дом', ids: ['wedding', 'house', 'namakarana', 'conception', 'construction', 'renovation'] },
  { title: 'Дело и деньги', ids: ['business', 'newproject', 'factory', 'contract', 'finance', 'court', 'conflict', 'sell_stuff'] },
  { title: 'Покупки', ids: ['vehicle', 'buy_electronics', 'buy_clothes'] },
  { title: 'Учёба и творчество', ids: ['education', 'creative'] },
  { title: 'Дорога и отдых', ids: ['travel', 'rest', 'sport'] },
  { title: 'Тело и здоровье', ids: ['medical', 'haircut', 'cosmetic', 'bodycare'] },
  { title: 'Духовная практика', ids: ['spiritual', 'sadhana', 'tapas'] },
  { title: 'Быт и природа', ids: ['cleaning', 'planting', 'aquarium', 'pet_care'] },
]

// ─── Состояние ──────────────────────────────────────────────────────────────

const api = useApi()
const { setPageHeader } = usePageHeader()
const { profile, hasProfile, fetchHoroscope } = useBirthProfile()
const { janmaNakshatra, janmaNakshatraName } = useJyotish()

/** Место расчёта. Своего «текущего города» в профиле нет — берём место
 * рождения; без профиля считаем по Москве (та же логика, что на /today). */
const FALLBACK_PLACE = { city: 'Москва', lat: 55.7558, lon: 37.6176, tz: 3 }
const usesProfilePlace = computed(() => {
  const p = profile.value
  return hasProfile.value && !!p && Number.isFinite(p.lat) && Number.isFinite(p.lon)
})
const place = computed(() => {
  const p = profile.value
  return usesProfilePlace.value && p
    ? { city: p.city || 'место рождения', lat: p.lat, lon: p.lon, tz: p.tz }
    : FALLBACK_PLACE
})

// Событие
const events = ref<EventDef[]>([])
const eventId = ref('wedding')
const query = ref('')
const currentEvent = computed<EventDef | null>(
  () => events.value.find((e) => e.id === eventId.value) ?? null,
)

/** Короткая подпись события для чипа.
 * В справочнике два разных дела носят один и тот же label («Садхана» —
 * это и spiritual, и sadhana). Трогать content/ нельзя, поэтому неуникальные
 * подписи заменяем полным name — иначе в списке стоят две одинаковые кнопки. */
const eventLabel = computed(() => {
  const seen = new Map<string, number>()
  for (const e of events.value) seen.set(e.label, (seen.get(e.label) ?? 0) + 1)
  return (e: EventDef) => ((seen.get(e.label) ?? 0) > 1 ? e.name : e.label)
})

const groupedEvents = computed(() => {
  const all = events.value
  if (!all.length) return []
  const q = query.value.trim().toLowerCase()
  const match = (e: EventDef) => !q
    || e.label.toLowerCase().includes(q)
    || e.name.toLowerCase().includes(q)
  const taken = new Set<string>()
  const out: Array<{ title: string; items: EventDef[] }> = []
  for (const g of EVENT_GROUPS) {
    const items: EventDef[] = []
    for (const id of g.ids) {
      const e = all.find((x) => x.id === id)
      if (!e) continue
      taken.add(id)
      if (match(e)) items.push(e)
    }
    if (items.length) out.push({ title: g.title, items })
  }
  const rest = all.filter((e) => !taken.has(e.id) && match(e))
  if (rest.length) out.push({ title: 'Прочее', items: rest })
  return out
})

// Диапазон дат
const MAX_DAYS = 92
const todayIso = toIso(startOfDay(new Date()))
const from = ref(todayIso)
const to = ref(toIso(addDays(startOfDay(new Date()), 29)))

const rangeLen = computed(() => daysBetween(from.value, to.value) + 1)
const rangeError = computed(() => {
  if (!from.value || !to.value) return 'Укажите обе даты диапазона.'
  if (rangeLen.value < 1) return 'Дата «по» не может быть раньше даты «от».'
  if (rangeLen.value > MAX_DAYS) return `Слишком длинный период: ${rangeLen.value} дн. Максимум — ${MAX_DAYS}.`
  return ''
})
function setPreset(n: number) {
  const start = startOfDay(new Date())
  from.value = toIso(start)
  to.value = toIso(addDays(start, n - 1))
}

// Данные API
const panchang = ref<ApiPanchang | null>(null)
const transits = ref<ApiNakTransit[] | null>(null)
const loading = ref(false)
const error = ref('')
const loadedAt = ref<Date | null>(null)
/** Ключ загруженных данных: пока он совпадает с текущим, в сеть не ходим. */
const loadedKey = ref('')
const dataKey = computed(() => [
  from.value, to.value, place.value.lat, place.value.lon, place.value.tz,
].join('|'))

async function load(force = false) {
  if (rangeError.value) return
  const key = dataKey.value
  if (!force && key === loadedKey.value && panchang.value) return
  loading.value = true
  error.value = ''
  const pl = place.value
  // date_end берём на сутки дальше конца диапазона: иначе API обрежет dt_end
  // последней титхи/накшатры на 23:59:59 и подпись «до …» стала бы неправдой.
  const body = {
    date_start: from.value,
    date_end: toIso(addDays(noonOf(to.value), 1)),
    tz: pl.tz, lat: pl.lat, lon: pl.lon,
  }
  try {
    const [p, t] = await Promise.all([
      api.post<ApiPanchang>('/api/panchang', body),
      api.post<ApiNakTransit[]>('/api/calendar', body),
    ])
    panchang.value = p
    transits.value = Array.isArray(t) ? t : []
    loadedKey.value = key
    loadedAt.value = new Date()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    panchang.value = null
    transits.value = null
    loadedKey.value = ''
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  // Гороскоп нужен только ради джанма-накшатры (фактор тары, вес 4).
  // Без профиля вернёт null — подбор продолжит работать без этого фактора.
  fetchHoroscope()
  listEvents().then((list) => {
    events.value = list
    if (!list.some((e) => e.id === eventId.value)) eventId.value = list[0]?.id ?? ''
  })
  load()
})

watch(dataKey, () => load())

// ─── Разбор диапазона по суткам ─────────────────────────────────────────────

interface DayRow {
  iso: string
  date: Date
  weekday: WeekdayRu
  sunrise: Date | null
  sunset: Date | null
  nak: ApiNakTransit | null
  /** Накшатра, на которую произойдёт смена в течение суток (если есть). */
  nakNext: ApiNakTransit | null
  tithi: ApiTithi | null
  tithiNo: number
  paksha: Paksha
  score: EventScoreResult | null
  /** Заполнено, если сутки посчитать не удалось. */
  problem: string
}

/** Элемент, действующий на восходе, — так титхи и накшатру и относят к суткам. */
function activeAt<T extends { dt_start: string; dt_end: string }>(list: T[], t: Date): T | null {
  return list.find((x) => at(x.dt_start) <= t && t < at(x.dt_end)) ?? null
}
/** Следующий по времени элемент, начинающийся до конца этих суток. */
function nextWithin<T extends { dt_start: string; dt_end: string }>(
  list: T[], after: Date, dayEnd: Date,
): T | null {
  return list.find((x) => at(x.dt_start) > after && at(x.dt_start) < dayEnd) ?? null
}

const rows = ref<DayRow[]>([])
const scoring = ref(false)
/** Гонки: при быстрой смене события считается только последний запуск. */
let runToken = 0

async function recompute() {
  const p = panchang.value
  const t = transits.value
  const ev = eventId.value
  if (!p || !t || !ev) { rows.value = []; return }
  const token = ++runToken
  scoring.value = true

  const janma = janmaNakshatra.value ?? undefined
  const inRange = p.days.filter((d) => d.date >= from.value && d.date <= to.value)

  const built = await Promise.all(inRange.map(async (d): Promise<DayRow> => {
    const date = noonOf(d.date)
    const weekday = weekdayRu(date)
    const sunrise = d.dt_sunrise ? at(d.dt_sunrise) : null
    const sunset = d.dt_sunset ? at(d.dt_sunset) : null
    const dayEnd = new Date(`${d.date}T23:59:59`)
    const mark = sunrise ?? new Date(`${d.date}T06:00:00`)

    const nak = activeAt(t, mark)
    const tithi = activeAt(p.tithis, mark)
    const base: DayRow = {
      iso: d.date, date, weekday, sunrise, sunset,
      nak,
      nakNext: nak ? nextWithin(t, mark, dayEnd) : null,
      tithi,
      tithiNo: 0,
      paksha: 'shukla',
      score: null,
      problem: '',
    }
    if (!nak || !tithi) {
      base.problem = !nak && !tithi
        ? 'расчёт не вернул ни накшатру, ни титхи на эти сутки'
        : !nak ? 'расчёт не вернул накшатру на эти сутки'
          : 'расчёт не вернул титхи на эти сутки'
      return base
    }
    const split = splitTithi(tithi.num)
    base.tithiNo = split.tithi
    base.paksha = split.paksha
    // yogaName не передаём: нитья-йогу API не считает, фактор (вес 1)
    // в знаменатель не попадёт — так честнее, чем подставлять пустую строку.
    base.score = await scoreEvent({
      eventId: ev,
      janmaNo: janma,
      dayNakNo: nak.nk_num,
      weekday,
      tithi: split.tithi,
      paksha: split.paksha,
    })
    if (!base.score) base.problem = 'модель не смогла оценить эти сутки'
    return base
  }))

  if (token !== runToken) return
  rows.value = built
  scoring.value = false
}

watch([panchang, transits, eventId, janmaNakshatra], () => { recompute() })

// ─── Сортировка, сводка, выбор дня ──────────────────────────────────────────

const sortBy = ref<'score' | 'date'>('score')

const sortedRows = computed(() => {
  const list = [...rows.value]
  if (sortBy.value === 'date') return list.sort((a, b) => a.iso.localeCompare(b.iso))
  return list.sort((a, b) => {
    const pa = a.score?.pct ?? -1
    const pb = b.score?.pct ?? -1
    if (pb !== pa) return pb - pa
    // При равном проценте (частый случай нуля из-за max(0, gained)) ранжируем
    // по сырому балансу баллов — иначе «плохо» и «совсем плохо» неразличимы.
    const ga = a.score?.gained ?? -99
    const gb = b.score?.gained ?? -99
    if (gb !== ga) return gb - ga
    return a.iso.localeCompare(b.iso)
  })
})

const scoredRows = computed(() => rows.value.filter((r) => r.score))
const failedRows = computed(() => rows.value.filter((r) => !r.score))

const summary = computed(() => {
  const c: Record<EventVerdictLevel, number> = { great: 0, good: 0, ok: 0, weak: 0 }
  for (const r of scoredRows.value) if (r.score) c[r.score.verdictLevel]++
  return c
})
const vetoCount = computed(() => scoredRows.value.filter((r) => r.score?.vetoMsg).length)

/** Лучшие дни — не более трёх и только те, что реально дотянули до «хорошо». */
const bestIsos = computed(() => new Set(
  sortedRows.value
    .filter((r) => (r.score?.pct ?? 0) >= 55)
    .slice(0, 3)
    .map((r) => r.iso),
))

const selectedIso = ref('')
const selected = computed<DayRow | null>(
  () => rows.value.find((r) => r.iso === selectedIso.value) ?? null,
)
// После каждого пересчёта показываем разбор лучшего дня — чтобы блок
// «Разбор дня» не стоял пустым и объяснял, чем именно хорош победитель.
watch(rows, (list) => {
  if (!list.length) { selectedIso.value = ''; return }
  if (list.some((r) => r.iso === selectedIso.value)) return
  const best = [...list].sort((a, b) => (b.score?.pct ?? -1) - (a.score?.pct ?? -1))[0]
  selectedIso.value = best?.iso ?? ''
})

// ─── Представление одной строки ─────────────────────────────────────────────

const LEVEL_VARIANT: Record<EventVerdictLevel, 'good' | 'bad' | 'neutral'> = {
  great: 'good', good: 'good', ok: 'neutral', weak: 'bad',
}
const LEVEL_SHORT: Record<EventVerdictLevel, string> = {
  great: 'Отличное окно', good: 'Хорошее окно', ok: 'Приемлемо', weak: 'Слабое окно',
}

/** Строка разбора → к какому фактору модели она относится.
 * Классифицируем по началу текста: порядок и формулировки строк заданы
 * в calculators/event-picker.ts и стабильны. Нужно только для компактных
 * чипов — полный текст строки при этом никуда не девается. */
type FactorKind = 'nakshatra' | 'tara' | 'tithi' | 'yoga' | 'day'
function factorKind(line: ScoreLine): FactorKind {
  if (line.text.startsWith('Накшатра ')) return 'nakshatra'
  if (line.text.startsWith('Тара-бала')) return 'tara'
  if (line.text.startsWith('Титхи ')) return 'tithi'
  if (line.text.startsWith('Йога ')) return 'yoga'
  return 'day'
}
const FACTOR_LABEL: Record<FactorKind, string> = {
  nakshatra: 'Накшатра', tara: 'Тара', tithi: 'Титхи', yoga: 'Йога', day: 'День недели',
}
function signVariant(sign: ScoreLine['sign']): 'good' | 'bad' | 'neutral' {
  if (sign === '+') return 'good'
  if (sign === '−' || sign === '⛔') return 'bad'
  return 'neutral'
}
/** Компактные чипы факторов для строки списка: «Накшатра +3», «Тара −4». */
function factorChips(score: EventScoreResult) {
  return score.lines.map((l) => {
    const kind = factorKind(l)
    const delta = l.sign === '+' ? `+${l.weight}` : l.sign === '~' ? '0' : `−${l.weight}`
    return {
      key: kind,
      label: `${FACTOR_LABEL[kind]} ${delta}`,
      variant: signVariant(l.sign),
      veto: l.sign === '⛔',
      title: l.text,
    }
  })
}

const PAKSHA_RU: Record<Paksha, string> = { shukla: 'растущая', krishna: 'убывающая' }

/** Подпись титхи для строки: «Шукла 11 · Экадаши». */
function tithiLabel(r: DayRow) {
  if (!r.tithi) return '—'
  return `${r.tithi.paksha} ${r.tithiNo} · ${r.tithi.name}`
}

// ─── Разбор выбранного дня ──────────────────────────────────────────────────

const KALAM_ICON: Record<KalamKey, 'alert' | 'warn' | 'info'> = {
  rahu: 'alert', gulika: 'warn', yamaganda: 'info',
}
const KALAM_TONE: Record<KalamKey, 'bad' | 'gold' | 'neutral'> = {
  rahu: 'bad', gulika: 'gold', yamaganda: 'neutral',
}

const selectedKalams = computed<KalamPeriod[]>(() => {
  const r = selected.value
  return r?.sunrise && r.sunset ? dayKalams(r.sunrise, r.sunset) : []
})
const selectedKalamItems = computed(() => selectedKalams.value.map((k) => ({
  name: k.name,
  time: `${fmtTime(k.start)} – ${fmtTime(k.end)}`,
  note: 'Традиция советует не начинать в этот отрезок важных дел.',
  icon: KALAM_ICON[k.key],
  tone: KALAM_TONE[k.key],
})))

/** Что именно ограничило оценку сверху — потолок вето из модели. */
const selectedVetoCap = computed(() => {
  const s = selected.value?.score
  if (!s?.vetoMsg) return null
  if (/Амавасья/i.test(s.vetoMsg)) return 20
  if (/[Рр]икта/.test(s.vetoMsg)) return 30
  return 40
})

// ─── Шапка кабинета ─────────────────────────────────────────────────────────

watchEffect(() => {
  setPageHeader({
    title: 'Подобрать дату',
    subtitle: currentEvent.value
      ? `${eventLabel.value(currentEvent.value).toLowerCase()} · ${fmtShort(noonOf(from.value))} – ${fmtShort(noonOf(to.value))}`
      : 'мухурта под событие',
    back: '/me',
    place: { city: place.value.city, time: `${rangeLen.value} дн.` },
  })
})

const updatedLabel = computed(() =>
  loadedAt.value ? `${fmtDate(loadedAt.value)}, ${fmtTime(loadedAt.value)}` : '')
</script>

<template>
  <section class="panel" aria-label="Подбор даты под событие">
    <!-- ═══════════ ВВОД ═══════════ -->
    <div class="grid-53">
      <UiCard
        title="Что подбираем"
        :note="events.length ? `${events.length} ${plural(events.length, 'событие', 'события', 'событий')}` : ''"
      >
        <div class="pd-search">
          <input
            v-model="query"
            type="search"
            class="pd-input"
            placeholder="Найти событие — свадьба, стрижка, договор…"
            aria-label="Поиск события"
          >
        </div>

        <p v-if="!events.length" class="pd-msg">Загружаем справочник событий…</p>
        <p v-else-if="!groupedEvents.length" class="pd-msg">
          Ничего не нашлось по запросу «{{ query }}».
        </p>

        <div v-for="g in groupedEvents" :key="g.title" class="pd-group">
          <div class="pd-group__title">{{ g.title }}</div>
          <div class="pd-group__items">
            <button
              v-for="e in g.items"
              :key="e.id"
              type="button"
              class="pd-ev"
              :class="{ 'is-on': e.id === eventId }"
              :aria-pressed="e.id === eventId"
              :title="e.name"
              @click="eventId = e.id"
            >
              <span class="pd-ev__ic" aria-hidden="true">{{ e.icon }}</span>
              {{ eventLabel(e) }}
            </button>
          </div>
        </div>
      </UiCard>

      <UiCard title="Когда" note="диапазон поиска">
        <div class="pd-range">
          <label class="pd-field">
            <span>От</span>
            <input v-model="from" type="date" class="pd-input">
          </label>
          <label class="pd-field">
            <span>До</span>
            <input v-model="to" type="date" class="pd-input">
          </label>
        </div>
        <div class="pd-presets">
          <button type="button" class="pd-preset" @click="setPreset(14)">2 недели</button>
          <button type="button" class="pd-preset" @click="setPreset(30)">30 дней</button>
          <button type="button" class="pd-preset" @click="setPreset(60)">60 дней</button>
          <button type="button" class="pd-preset" @click="setPreset(90)">90 дней</button>
        </div>

        <UiDisclaimer v-if="rangeError" tone="warn">{{ rangeError }}</UiDisclaimer>
        <UiKv v-else k="Дней в диапазоне" :v="String(rangeLen)" />
        <UiKv k="Место расчёта" :v="place.city" />
        <UiKv
          k="Джанма-накшатра"
          :v="janmaNakshatraName ? `${janmaNakshatraName} (№ ${janmaNakshatra})` : 'не задана'"
          :tone="janmaNakshatraName ? 'good' : undefined"
        />

        <UiDisclaimer>
          Титхи и накшатра относятся к суткам по восходу в месте расчёта —
          так их и определяет традиция. Место берётся
          <template v-if="usesProfilePlace">из профиля рождения</template>
          <template v-else>по умолчанию (профиль рождения не заполнен)</template>.
        </UiDisclaimer>
      </UiCard>
    </div>

    <!-- ═══════════ ГЕЙТ БЕЗ ПРОФИЛЯ ═══════════ -->
    <UiCard v-if="!hasProfile">
      <p class="pd-msg">
        Подбор уже работает — но без личного фактора. Тара-бала (самый весомый
        фактор модели, вес 4 из 11) считается от вашей джанма-накшатры — накшатры
        Луны в момент рождения. Добавьте дату, время и место рождения, и дни
        начнут ранжироваться персонально, а не только по общей панчанге.
      </p>
      <UiButton to="/me">Заполнить данные рождения</UiButton>
    </UiCard>

    <UiCard v-else-if="!janmaNakshatra">
      <p class="pd-msg">
        Данные рождения есть, но гороскоп ещё не посчитан — без него
        джанма-накшатра неизвестна и фактор тара-балы в подборе не участвует.
        Откройте «Обо мне», чтобы обновить расчёт.
      </p>
      <UiButton to="/me">Обо мне</UiButton>
    </UiCard>

    <!-- ═══════════ СОСТОЯНИЯ ЗАГРУЗКИ ═══════════ -->
    <UiCard v-if="error">
      <p class="pd-msg">Не удалось получить расчёт: {{ error }}</p>
      <UiButton @click="load(true)">Повторить</UiButton>
    </UiCard>

    <UiCard v-else-if="loading && !rows.length">
      <p class="pd-msg">
        Считаем панчангу и транзиты Луны на {{ rangeLen }} дн. — двумя запросами
        на весь период…
      </p>
    </UiCard>

    <!-- ═══════════ РЕЗУЛЬТАТ ═══════════ -->
    <template v-else-if="rows.length && currentEvent">
      <UiSectionHead :title="`Итог: ${eventLabel(currentEvent).toLowerCase()}`" />

      <UiCard>
        <UiVerdict
          :score="`${summary.great + summary.good}`"
          :tone="summary.great + summary.good ? 'good' : summary.ok ? 'neutral' : 'bad'"
        >
          <template v-if="summary.great + summary.good">
            подходящих дней из {{ scoredRows.length }} проверенных
          </template>
          <template v-else-if="summary.ok">
            дней с оговорками — сильных окон в этом периоде нет
          </template>
          <template v-else>
            подходящих дней в этом периоде не нашлось
          </template>
          <template #note>
            {{ currentEvent.name }}. Проверено {{ scoredRows.length }} дн. из
            {{ rangeLen }}<template v-if="failedRows.length">, не удалось посчитать
              {{ failedRows.length }}</template>. Отличных — {{ summary.great }},
            хороших — {{ summary.good }}, приемлемых — {{ summary.ok }},
            слабых — {{ summary.weak }}<template v-if="vetoCount">; со стоп-фактором —
              {{ vetoCount }}</template>.
          </template>
        </UiVerdict>

        <UiDisclaimer tone="warn">
          Веса факторов (тара 4, накшатра 3, титхи 2, день недели 2, йога 1)
          и пороги вердиктов — <b>метод школы, а не канон</b>. Другие традиции
          расставляют приоритеты иначе и могут дать другой ответ на тот же день.
          Это ориентир для выбора, а не разрешение и не запрет.
        </UiDisclaimer>

        <UiDisclaimer>
          В оценку <b>не входят</b> нитья-йога и карана: сервис их не считает,
          поэтому фактор йоги (вес 1) в модели не участвует, а стоп-фактор Бхадра
          (Вишти-карана) не виден. Дневные каламы (Раху / Гулика / Ямаганда) на
          балл дня тоже не влияют — это выбор <i>часа</i>, а не дня; они показаны
          в разборе выбранного дня ниже.
        </UiDisclaimer>
      </UiCard>

      <!-- ─────────── РАЗБОР ДНЯ ─────────── -->
      <template v-if="selected">
        <UiSectionHead title="Разбор дня" />
        <UiCard
          :title="`${fmtDate(selected.date)}, ${selected.weekday.toLowerCase()}`"
          :subtitle="currentEvent.name"
        >
          <template v-if="selected.score">
            <UiVerdict
              :score="`${selected.score.pct}%`"
              :tone="LEVEL_VARIANT[selected.score.verdictLevel]"
              :text="selected.score.verdict"
            >
              <template #note>
                Накшатра на восходе — {{ selected.nak?.ru }} (№ {{ selected.nak?.nk_num }},
                управитель {{ selected.nak?.lord }}), титхи — {{ tithiLabel(selected) }}
                ({{ PAKSHA_RU[selected.paksha] }} половина).
                <template v-if="selected.nakNext">
                  В {{ fmtTime(at(selected.nakNext.dt_start)) }} Луна перейдёт
                  в {{ selected.nakNext.ru }} — оценка дня считается по накшатре
                  на восходе.
                </template>
              </template>
            </UiVerdict>

            <UiDisclaimer v-if="selected.score.vetoMsg" tone="warn">
              <b>Стоп-фактор: {{ selected.score.vetoMsg }}.</b>
              Он не просто вычитает баллы — он ограничивает итог сверху
              потолком {{ selectedVetoCap }} %, чтобы удачные остальные факторы
              не «перекрыли» жёсткое противопоказание.
            </UiDisclaimer>

            <div class="pd-lines">
              <div
                v-for="(l, i) in selected.score.lines"
                :key="i"
                class="pd-line"
                :class="`pd-line--${signVariant(l.sign)}`"
              >
                <span class="pd-line__sign" aria-hidden="true">{{ l.sign }}</span>
                <span class="pd-line__text">{{ l.text }}</span>
                <span class="pd-line__w">
                  {{ l.sign === '+' ? '+' : l.sign === '~' ? '' : '−' }}{{ l.sign === '~' ? '0' : l.weight }}
                </span>
              </div>
            </div>

            <UiProOnly>
              <UiKv
                k="Арифметика"
                :v="`${selected.score.gained} из ${selected.score.total} возможных → ${Math.round((Math.max(0, selected.score.gained) / selected.score.total) * 100)} %`"
              />
              <UiKv
                v-if="selected.score.vetoMsg"
                k="Потолок вето"
                :v="`${selectedVetoCap} % — итог срезан до ${selected.score.pct} %`"
                tone="bad"
              />
              <UiKv
                k="Факторы в знаменателе"
                :v="`${selected.score.lines.length} из 5 (йога не считается сервисом)`"
              />
            </UiProOnly>
          </template>

          <p v-else class="pd-msg">
            Эти сутки посчитать не удалось: {{ selected.problem }}.
          </p>

          <!-- Списки справочника показываем как есть. Это не украшение:
               модель сверяет титхи ПО НОМЕРУ, поэтому пункты, записанные словом
               («Амавасья», «Пурнима»), в баллы не попадают — они учтены только
               там, где для события заведён отдельный стоп-фактор. Пусть это
               будет видно глазами, а не спрятано за процентом. -->
          <div class="pd-subhead">Что справочник говорит об этом событии</div>
          <UiKv
            v-if="currentEvent.good_nakshatras?.length"
            k="Благоприятные накшатры" :v="currentEvent.good_nakshatras.join(', ')"
            tone="good"
          />
          <UiKv
            v-if="currentEvent.avoid_nakshatras?.length"
            k="Избегаемые накшатры" :v="currentEvent.avoid_nakshatras.join(', ')"
            tone="bad"
          />
          <UiKv
            v-if="currentEvent.good_tithis?.length"
            k="Благоприятные титхи" :v="currentEvent.good_tithis.join(', ')"
            tone="good"
          />
          <UiKv
            v-if="currentEvent.avoid_tithis?.length"
            k="Избегаемые титхи" :v="currentEvent.avoid_tithis.join(', ')"
            tone="bad"
          />
          <UiKv
            v-if="currentEvent.good_days?.length"
            k="Благоприятные дни" :v="currentEvent.good_days.join(', ')"
            tone="good"
          />
          <UiKv
            v-if="currentEvent.avoid_days?.length"
            k="Избегаемые дни" :v="currentEvent.avoid_days.join(', ')"
            tone="bad"
          />
          <UiDisclaimer>
            Баллы модель ставит по номеру титхи, накшатре и дню недели. Пункты
            списков, записанные словом («Амавасья», «Пурнима», «гандантовые»,
            «по ряду школ»), в арифметику не попадают — они учтены только там,
            где для события заведён отдельный стоп-фактор. Сверьте список глазами.
          </UiDisclaimer>

          <template v-if="selectedKalamItems.length">
            <div class="pd-subhead">В какие часы этого дня не начинать</div>
            <UiWarnList :items="selectedKalamItems" />
            <UiDisclaimer>
              Светлое время суток ({{ selected.sunrise ? fmtTime(selected.sunrise) : '—' }} —
              {{ selected.sunset ? fmtTime(selected.sunset) : '—' }}) делится на 8 равных
              частей, номер части задаёт день недели. Школы расходятся в точке отсчёта
              восхода и в схеме для Гулики — это ориентир, а не запрет.
              <b>В балл дня эти отрезки не входят.</b>
            </UiDisclaimer>
          </template>

          <UiProOnly>
            <div class="pd-subhead">Что проверить астрологу вручную</div>
            <UiReasonList
              :items="(currentEvent.advisor || []).map((textItem) => ({ text: textItem, tone: 'info' }))"
            />
            <UiKv v-if="currentEvent.house" k="Дома" :v="currentEvent.house" />
            <UiKv v-if="currentEvent.karaka" k="Карака" :v="currentEvent.karaka" />
            <UiKv v-if="currentEvent.months" k="Месяцы" :v="currentEvent.months" />
          </UiProOnly>
        </UiCard>
      </template>

      <!-- ─────────── СПИСОК ДНЕЙ ─────────── -->
      <UiSectionHead title="Все дни диапазона" :flag="scoring ? 'считаем…' : undefined" />
      <UiCard>
        <template #head>
          <div>
            <h2 class="card__title">Дни диапазона</h2>
            <div class="card__sub">
              и хорошие, и плохие — чтобы было видно, почему день не подошёл
            </div>
          </div>
          <div class="pd-sort" role="group" aria-label="Сортировка">
            <button
              type="button" :class="{ 'is-on': sortBy === 'score' }"
              :aria-pressed="sortBy === 'score'" @click="sortBy = 'score'"
            >По оценке</button>
            <button
              type="button" :class="{ 'is-on': sortBy === 'date' }"
              :aria-pressed="sortBy === 'date'" @click="sortBy = 'date'"
            >По дате</button>
          </div>
        </template>

        <div class="pd-list">
          <button
            v-for="r in sortedRows"
            :key="r.iso"
            type="button"
            class="pd-row"
            :class="{
              'is-best': bestIsos.has(r.iso),
              'is-sel': r.iso === selectedIso,
              'is-dead': !r.score,
            }"
            :aria-pressed="r.iso === selectedIso"
            @click="selectedIso = r.iso"
          >
            <span class="pd-row__date">
              <b>{{ fmtShort(r.date) }}</b>
              <span class="pd-row__wd">{{ WEEKDAY_SHORT[r.date.getDay()] }}</span>
            </span>

            <span class="pd-row__astro">
              <span class="pd-row__nak">{{ r.nak?.ru ?? '—' }}</span>
              <span class="pd-row__tithi">{{ tithiLabel(r) }}</span>
            </span>

            <template v-if="r.score">
              <span class="pd-row__bar" aria-hidden="true">
                <span
                  class="pd-row__fill"
                  :class="`pd-row__fill--${LEVEL_VARIANT[r.score.verdictLevel]}`"
                  :style="{ width: `${Math.max(r.score.pct, 2)}%` }"
                />
              </span>
              <span class="pd-row__pct">{{ r.score.pct }}%</span>
              <span class="pd-row__verdict">
                <UiChip :variant="LEVEL_VARIANT[r.score.verdictLevel]">
                  {{ LEVEL_SHORT[r.score.verdictLevel] }}
                </UiChip>
                <UiChip v-if="bestIsos.has(r.iso)" variant="good" icon="check">лучший</UiChip>
              </span>
              <span class="pd-row__factors">
                <UiChip
                  v-for="(c, i) in factorChips(r.score)"
                  :key="i"
                  :variant="c.variant"
                  :title="c.title"
                >
                  <template v-if="c.veto">⛔ </template>{{ c.label }}
                </UiChip>
                <!-- Стоп-фактор виден в строке всегда, а не только в разборе:
                     он не должен растворяться в общей оценке (HANDOFF §5.1). -->
                <UiChip v-if="r.score.vetoMsg" variant="bad" :title="r.score.vetoMsg">
                  ⛔ стоп-фактор
                </UiChip>
              </span>
            </template>

            <span v-else class="pd-row__fail">{{ r.problem }}</span>
          </button>
        </div>
      </UiCard>

      <UiNoteBar :updated="updatedLabel">
        Подбор построен на двух запросах к расчёту — транзиты Луны по накшатрам
        и титхи за весь период {{ fmtDate(noonOf(from)) }} — {{ fmtDate(noonOf(to)) }}
        для места «{{ place.city }}» — и весовой модели школы из справочника
        мухурты<template v-if="janmaNakshatra">, включая тара-балу от вашей
          джанма-накшатры ({{ janmaNakshatraName }})</template><template v-else>;
          фактор тара-балы отключён — джанма-накшатра неизвестна</template>.
        Йога и карана в расчёт не входят.
      </UiNoteBar>

      <UiDisclaimer>
        Итог — <b>оценка дня, а не разрешение или запрет</b>. «Слабое окно»
        традиция читает как повод отнестись внимательнее и выбрать хороший час,
        а не как причину отменить дело. Точный расчёт под конкретное событие,
        с мухурта-картой и проверкой домов, делает астролог.
      </UiDisclaimer>
    </template>
  </section>
</template>

<style scoped>
.pd-msg {
  margin: 0 0 12px;
  font-size: 14px;
  color: var(--body);
  line-height: 1.6;
}

.pd-subhead {
  margin: 18px 0 10px;
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
}

/* ── Поля ввода ── */
.pd-input {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  color: var(--ink);
  font: inherit;
  font-size: 14px;
  outline: none;
}

.pd-input:focus {
  border-color: var(--accent-line);
}

.pd-search {
  margin-bottom: 14px;
}

.pd-range {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.pd-field {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pd-field > span {
  font-size: 12.5px;
  color: var(--muted);
}

.pd-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 14px;
}

.pd-preset {
  padding: 6px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-pill);
  background: var(--surface-2);
  color: var(--body);
  font-size: 12.5px;
  cursor: pointer;
  transition: border-color var(--d-fast) var(--e-out), color var(--d-fast) var(--e-out);
}

.pd-preset:hover {
  border-color: var(--accent-line);
  color: var(--accent-ink);
}

/* ── Выбор события ── */
.pd-group + .pd-group {
  margin-top: 14px;
}

.pd-group__title {
  font-size: 12px;
  letter-spacing: .04em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 8px;
}

.pd-group__items {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.pd-ev {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 13px;
  border: 1px solid var(--line);
  border-radius: var(--r-pill);
  background: var(--surface-2);
  color: var(--body);
  font-size: 13px;
  cursor: pointer;
  transition: border-color var(--d-fast) var(--e-out),
    background var(--d-fast) var(--e-out), color var(--d-fast) var(--e-out);
}

.pd-ev:hover {
  border-color: var(--accent-line);
  color: var(--accent-ink);
}

.pd-ev.is-on {
  border-color: var(--accent-line);
  background: var(--accent-soft);
  color: var(--accent-ink);
  font-weight: 500;
}

.pd-ev__ic {
  font-size: 14px;
  line-height: 1;
}

/* ── Построчный разбор ── */
.pd-lines {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 14px 0 0;
}

.pd-line {
  display: grid;
  grid-template-columns: 20px 1fr auto;
  align-items: baseline;
  gap: 10px;
  padding: 9px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  font-size: 13.5px;
  line-height: 1.5;
}

.pd-line--good {
  border-color: var(--good-line);
  background: var(--good-soft);
}

.pd-line--bad {
  border-color: var(--bad-line);
  background: var(--bad-soft);
}

.pd-line__sign {
  text-align: center;
  color: var(--muted);
}

.pd-line--good .pd-line__sign { color: var(--good); }
.pd-line--bad .pd-line__sign { color: var(--bad); }

.pd-line__text {
  color: var(--body);
}

.pd-line__w {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: var(--muted);
  white-space: nowrap;
}

.pd-line--good .pd-line__w { color: var(--good); }
.pd-line--bad .pd-line__w { color: var(--bad); }

/* ── Сортировка ── */
.pd-sort {
  margin-left: auto;
  display: inline-flex;
  border: 1px solid var(--line);
  border-radius: var(--r-pill);
  overflow: hidden;
}

.pd-sort button {
  padding: 6px 13px;
  border: 0;
  background: transparent;
  color: var(--muted);
  font-size: 12.5px;
  cursor: pointer;
}

.pd-sort button.is-on {
  background: var(--accent-soft);
  color: var(--accent-ink);
  font-weight: 500;
}

/* ── Список дней ── */
.pd-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pd-row {
  display: grid;
  grid-template-columns: 72px minmax(140px, 1fr) 72px 42px 134px minmax(0, 1.7fr);
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  text-align: left;
  cursor: pointer;
  transition: border-color var(--d-fast) var(--e-out), background var(--d-fast) var(--e-out);
}

.pd-row:hover {
  border-color: var(--accent-line);
}

.pd-row.is-best {
  border-color: var(--gold-line);
  background: var(--gold-soft);
}

.pd-row.is-sel {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.pd-row.is-dead {
  opacity: .7;
}

.pd-row__date {
  display: flex;
  flex-direction: column;
  line-height: 1.3;
}

.pd-row__date b {
  font-size: 13.5px;
  color: var(--ink);
  font-weight: 600;
}

.pd-row__wd {
  font-size: 11.5px;
  color: var(--muted);
}

.pd-row__astro {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.35;
}

.pd-row__nak {
  font-size: 13.5px;
  color: var(--ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pd-row__tithi {
  font-size: 11.5px;
  color: var(--muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pd-row__bar {
  height: 7px;
  border-radius: var(--r-pill);
  background: var(--surface-3);
  overflow: hidden;
}

.pd-row__fill {
  display: block;
  height: 100%;
  border-radius: var(--r-pill);
  background: var(--good);
}

.pd-row__fill--neutral { background: var(--gold); }
.pd-row__fill--bad { background: var(--bad); }

.pd-row__pct {
  font-size: 13px;
  font-weight: 600;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.pd-row__verdict,
.pd-row__factors {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.pd-row__fail {
  grid-column: 3 / -1;
  font-size: 12.5px;
  color: var(--muted);
  font-style: italic;
}

@media (max-width: 1180px) {
  .pd-row {
    grid-template-columns: 70px minmax(130px, 1fr) 70px 44px auto;
  }

  .pd-row__factors {
    grid-column: 1 / -1;
  }
}

@media (max-width: 760px) {
  .pd-range {
    flex-direction: column;
  }

  .pd-row {
    grid-template-columns: 68px 1fr auto;
  }

  .pd-row__bar {
    display: none;
  }

  .pd-row__verdict,
  .pd-row__factors {
    grid-column: 1 / -1;
  }
}
</style>
