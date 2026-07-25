<script setup lang="ts">
// Страница «Сегодня» — панчанга выбранной даты на реальных данных.
//
// Источники данных:
//   POST /api/panchang  → dt_sunrise, dt_sunset, horas[], muhurtas[] + tithis[]
//   POST /api/calendar  → транзиты Луны по накшатрам (накшатра дня)
//   content/panchanga.json (vara / yoga / karana / stop_factors) — описания
//   content/tithi.json (15 титх × категории) — описания
//   calculators/tara.ts → taraFor(джанма, накшатра дня)
//   utils/kalam.ts → Раху / Гулика / Ямаганда (расчёт + ссылки на источники)
//
// ЧЕГО ЗДЕСЬ НЕТ И БЫТЬ НЕ ДОЛЖНО: «энергии дня», персональных оценок «8/10»,
// рейтинга по сферам — таких моделей у сервиса нет, рисовать их = врать.
// Йога и карана API не отдаёт — карточки помечены «не рассчитывается»,
// значения не выдумываем (docs/HANDOFF.md §5.1: панчангу нельзя разрывать,
// но и подменять недостающее вымыслом нельзя).
import { loadPanchanga, loadTithi, splitTithi, useJyotish } from '~/composables/useJyotish'
import { dayKalams, isKalamActive, type KalamKey, type KalamPeriod } from '~/utils/kalam'

definePageMeta({ layout: 'app', middleware: 'auth' })
useHead({ title: 'Сегодня — Jyotish' })

// ─── Типы ответов API (проверены живыми запросами, см. отчёт) ────────────────

interface ApiTithi {
  num: number          // сквозной 1..30
  name: string         // «Экадаши»
  paksha: string       // «Шукла» | «Кришна»
  type: string         // категория: Нанда / Бхадра / Джая / Рикта / Пурна
  quality: string      // «Очень благоприятная» …
  dt_start: string
  dt_end: string
}
interface ApiHora {
  num: number
  planet: string       // «Сатурн»
  day_night: 'день' | 'ночь'
  dt_start: string
  dt_end: string
}
interface ApiDay {
  date: string
  dt_sunrise: string
  dt_sunset: string
  day_dur_h: number
  muhurtas: Array<{ num: number; name: string; quality: string; day_night: string; dt_start: string; dt_end: string }>
  horas: ApiHora[]
}
interface ApiPanchang { tithis: ApiTithi[]; days: ApiDay[] }
interface ApiNakTransit {
  nk_num: number       // 1..27
  name: string
  ru: string
  lord: string
  gana: string         // Devata | Manushya | Rakshasa
  dt_start: string
  dt_end: string
}

// ─── Формат ─────────────────────────────────────────────────────────────────

const MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']

const pad = (n: number) => String(n).padStart(2, '0')
const fmtTime = (d: Date) => `${pad(d.getHours())}:${pad(d.getMinutes())}`
const fmtDate = (d: Date) => `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`
const toIso = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

/** API отдаёт локальное время места без смещения — new Date() трактует его
 * как локальное время браузера. Для разниц и вывода «ЧЧ:ММ» это то, что нужно. */
const at = (iso: string) => new Date(iso)

function addDays(d: Date, n: number) {
  const x = new Date(d)
  x.setDate(x.getDate() + n)
  return x
}
function startOfDay(d: Date) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}
/** «до 09:04» или «до 11:28, 26 июля», если конец за пределами выбранных суток. */
function untilLabel(endIso: string, base: Date) {
  const e = at(endIso)
  const same = e.getFullYear() === base.getFullYear()
    && e.getMonth() === base.getMonth() && e.getDate() === base.getDate()
  return same ? `до ${fmtTime(e)}` : `до ${fmtTime(e)}, ${e.getDate()} ${MONTHS[e.getMonth()]}`
}

const WEEKDAY_GEN = ['воскресенье', 'понедельник', 'вторник', 'среда',
  'четверг', 'пятница', 'суббота']
/** Глиф управителя дня недели (индекс = Date.getDay()). */
const VARA_GLYPH = ['☉︎', '☾︎', '♂︎', '☿︎', '♃︎', '♀︎', '♄︎']
/** Родительный падеж имени планеты для подписи «день Сатурна». */
const PLANET_GEN: Record<string, string> = {
  'Солнце': 'Солнца', 'Луна': 'Луны', 'Марс': 'Марса', 'Меркурий': 'Меркурия',
  'Юпитер': 'Юпитера', 'Венера': 'Венеры', 'Сатурн': 'Сатурна',
}
const GANA_RU: Record<string, string> = {
  Devata: 'дэва-гана', Manushya: 'манушья-гана', Rakshasa: 'ракшаса-гана',
}

/** «Очень благоприятная» → good, «Неблагоприятная» → bad, прочее → neutral. */
function qualityVariant(q?: string): 'good' | 'bad' | 'neutral' {
  if (!q) return 'neutral'
  if (/неблаго/i.test(q)) return 'bad'
  if (/благоприятн/i.test(q)) return 'good'
  return 'neutral'
}

// ─── Состояние ──────────────────────────────────────────────────────────────

const api = useApi()
const { setPageHeader } = usePageHeader()
const { profile, hasProfile, fetchHoroscope } = useBirthProfile()
const { janmaNakshatra, janmaNakshatraName, taraForDay } = useJyotish()

/** Выбранные сутки (локальная полночь). */
const today = startOfDay(new Date())
const day = ref<Date>(today)
const isToday = computed(() => day.value.getTime() === today.getTime())

/** Место расчёта. Отдельного «текущего города» в профиле нет — берём место
 * рождения, а если профиля нет, считаем общегородскую панчангу по Москве
 * (SERVICE-IA §4.2: без профиля панчанга доступна, но не персональна). */
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

const panchang = ref<ApiPanchang | null>(null)
const transits = ref<ApiNakTransit[] | null>(null)
const loading = ref(false)
const error = ref('')
const loadedAt = ref<Date | null>(null)

// Описания из content/ — ленивые чанки (docs/HANDOFF.md §2).
const panContent = ref<any | null>(null)
const tithiContent = ref<any | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  const pl = place.value
  const base = {
    date_start: toIso(day.value),
    // Конец диапазона — следующие сутки: иначе API обрезает dt_end титхи и
    // накшатры на 23:59:59 и подпись «до …» получилась бы неправдой.
    date_end: toIso(addDays(day.value, 1)),
    tz: pl.tz, lat: pl.lat, lon: pl.lon,
  }
  try {
    const [p, t] = await Promise.all([
      api.post<ApiPanchang>('/api/panchang', base),
      api.post<ApiNakTransit[]>('/api/calendar', base),
    ])
    panchang.value = p
    transits.value = Array.isArray(t) ? t : []
    loadedAt.value = new Date()
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    panchang.value = null
    transits.value = null
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  // Гороскоп нужен только ради джанма-накшатры для тара-балы; без профиля
  // вызов просто вернёт null и блок тары заменится приглашением.
  fetchHoroscope()
  Promise.all([loadPanchanga(), loadTithi()]).then(([pan, tit]) => {
    panContent.value = pan
    tithiContent.value = tit
  })
  load()
})

// Смена даты или места (профиль мог подтянуться позже) — перезапрос.
watch(
  () => [toIso(day.value), place.value.lat, place.value.lon, place.value.tz].join('|'),
  () => load(),
)

function shiftDay(n: number) {
  day.value = addDays(day.value, n)
}

// ─── Разбор ответа ──────────────────────────────────────────────────────────

const dayInfo = computed<ApiDay | null>(() => panchang.value?.days?.[0] ?? null)
const sunrise = computed(() => (dayInfo.value ? at(dayInfo.value.dt_sunrise) : null))
const sunset = computed(() => (dayInfo.value ? at(dayInfo.value.dt_sunset) : null))

/** Элемент, действующий на восходе, — так титхи/накшатру и относят к суткам. */
function activeAtSunrise<T extends { dt_start: string; dt_end: string }>(list: T[]): T | null {
  const sr = sunrise.value
  if (!list.length) return null
  if (sr) {
    const hit = list.find((x) => at(x.dt_start) <= sr && sr < at(x.dt_end))
    if (hit) return hit
  }
  return list[0]
}

const tithiNow = computed(() => activeAtSunrise(panchang.value?.tithis ?? []))
const nakNow = computed(() => activeAtSunrise(transits.value ?? []))

/** Описание титхи (1..15 внутри пакши) и её категории из content/tithi.json. */
const tithiDef = computed(() => {
  const t = tithiNow.value
  const c = tithiContent.value
  if (!t || !c?.tithis) return null
  return c.tithis[splitTithi(t.num).tithi - 1] ?? null
})
const tithiCat = computed(() => {
  const t = tithiNow.value
  const cats = tithiContent.value?.categories as any[] | undefined
  return (t && cats?.find((c) => c.name === t.type)) || null
})
/** «Подходит для:» — из поля do описания титхи, оно перечислением. */
const tithiList = computed<string[]>(() => {
  const raw = tithiDef.value?.do as string | undefined
  if (!raw) return []
  return raw.split(/,\s*/).map((s) => s.trim()).filter(Boolean).slice(0, 4)
})

const varaDef = computed(() => panContent.value?.vara?.days?.[day.value.getDay()] ?? null)
const varaPlanet = computed(() => (varaDef.value?.planet as string | undefined)?.split(' (')[0] ?? '')

// ─── Тара-бала ──────────────────────────────────────────────────────────────

const tara = computed(() => {
  const n = nakNow.value
  return n ? taraForDay(n.nk_num) : null
})
const taraVariant = computed<'good' | 'bad' | 'neutral'>(() => {
  const q = tara.value?.quality
  return q === 'good' ? 'good' : q === 'bad' ? 'bad' : 'neutral'
})
/** Рекомендации школы по таре (content/tara_school.json через calculators/tara). */
const taraSchoolGood = computed<string>(() => {
  const s = tara.value?.school as Record<string, string> | undefined
  return s?.good ?? ''
})
const TARA_STRENGTH_RU: Record<string, string> = {
  full: 'в полную силу (1-я группа, Джанмаркша)',
  partial: 'ослаблена (2-я группа, Кармаркша)',
  mild: 'почти нейтральна (3-я группа, Адханаркша)',
}

// ─── Стоп-факторы дня ───────────────────────────────────────────────────────

const kalams = computed<KalamPeriod[]>(() =>
  sunrise.value && sunset.value ? dayKalams(sunrise.value, sunset.value) : [])

/** Названия периодов в content/panchanga.json → ключи расчёта. */
const STOP_CONTENT_NAME: Record<KalamKey, string> = {
  rahu: 'Раху-калам',
  yamaganda: 'Ямаганда-калам',
  gulika: 'Гулика / Мандикалам',
}
const KALAM_ICON: Record<KalamKey, 'alert' | 'warn' | 'info'> = {
  rahu: 'alert', gulika: 'warn', yamaganda: 'info',
}
const KALAM_TONE: Record<KalamKey, 'bad' | 'gold' | 'neutral'> = {
  rahu: 'bad', gulika: 'gold', yamaganda: 'neutral',
}

const now = ref(new Date())
let ticker: ReturnType<typeof setInterval> | null = null
onMounted(() => { ticker = setInterval(() => { now.value = new Date() }, 60_000) })
onBeforeUnmount(() => { if (ticker) clearInterval(ticker) })

const kalamItems = computed(() => {
  const daily = (panContent.value?.stop_factors?.daily ?? []) as any[]
  return kalams.value.map((k) => {
    const def = daily.find((d) => d.name === STOP_CONTENT_NAME[k.key])
    const active = isToday.value && isKalamActive(k, now.value)
    return {
      name: active ? `${k.name} · идёт сейчас` : k.name,
      time: `${fmtTime(k.start)} – ${fmtTime(k.end)}`,
      note: def?.note || 'Избегают начала важных дел.',
      icon: KALAM_ICON[k.key],
      tone: KALAM_TONE[k.key],
    }
  })
})
const activeKalam = computed(() =>
  isToday.value ? kalams.value.find((k) => isKalamActive(k, now.value)) ?? null : null)

// ─── Хоры (лента «Ваш день по часам») ───────────────────────────────────────
// Только факт: чья хора и с какого по какое время. Никаких оценок
// «благоприятно / неблагоприятно» — модели для них нет.

const dayHoras = computed(() => {
  const rows = dayInfo.value?.horas ?? []
  return rows.filter((h) => h.day_night === 'день').map((h) => ({
    num: h.num,
    planet: h.planet,
    from: fmtTime(at(h.dt_start)),
    to: fmtTime(at(h.dt_end)),
    current: isToday.value
      && now.value >= at(h.dt_start) && now.value < at(h.dt_end),
  }))
})

// ─── «Астрологическая причина дня» — только проверяемые факты ───────────────

const reasons = computed(() => {
  const out: Array<{ tone: 'good' | 'warn' | 'info' | 'bad'; text: string }> = []
  const t = tithiNow.value
  if (t) {
    out.push({
      tone: qualityVariant(t.quality) === 'bad' ? 'warn' : 'good',
      text: `Титхи на восходе — ${t.paksha} ${t.name} (${t.num} из 30), категория ${t.type}: ${t.quality.toLowerCase()}.`
        + (tithiCat.value ? ` ${tithiCat.value.desc}` : ''),
    })
  }
  const n = nakNow.value
  if (n) {
    out.push({
      tone: 'info',
      text: `Луна идёт по накшатре ${n.ru} (${n.nk_num} из 27), управитель — ${n.lord}`
        + (GANA_RU[n.gana] ? `, ${GANA_RU[n.gana]}` : '') + '.',
    })
  }
  if (varaDef.value) {
    out.push({
      tone: 'info',
      text: `Вара — ${varaDef.value.day}, день планеты ${varaPlanet.value}. ${varaDef.value.good}`,
    })
  }
  const ta = tara.value
  if (ta && janmaNakshatraName.value) {
    out.push({
      tone: ta.quality === 'bad' ? 'warn' : ta.quality === 'good' ? 'good' : 'info',
      text: `От вашей джанма-накшатры (${janmaNakshatraName.value}) накшатра дня — ${ta.pos}-я,`
        + ` это тара «${ta.name}»: ${ta.short}. Это один из показателей дня, а не приговор.`,
    })
  }
  const ak = activeKalam.value
  if (ak) {
    out.push({
      tone: 'warn',
      text: `Прямо сейчас идёт ${ak.name} (${fmtTime(ak.start)} – ${fmtTime(ak.end)}) —`
        + ' традиция советует не начинать в этот отрезок важных дел.',
    })
  }
  out.push({
    tone: 'info',
    text: 'Йога и карана в расчёт не входят: сервис их пока не считает,'
      + ' поэтому картина дня по панчанге здесь неполная.',
  })
  return out
})

// ─── Пять карточек панчанги ────────────────────────────────────────────────

const NOT_CALCULATED = 'не рассчитывается'

const cards = computed(() => {
  const base = day.value
  const t = tithiNow.value
  const n = nakNow.value
  const v = varaDef.value
  const list: any[] = []

  list.push({
    no: 1,
    label: 'Титхи',
    glyph: '☾︎',
    value: t ? `${t.paksha} ${t.name}` : '—',
    until: t ? untilLabel(t.dt_end, base) : undefined,
    chip: t?.quality,
    chipVariant: qualityVariant(t?.quality),
    text: tithiCat.value ? `Категория ${t?.type}: ${tithiCat.value.desc}` : tithiDef.value?.good,
    listTitle: tithiList.value.length ? 'Подходит для:' : undefined,
    list: tithiList.value,
  })

  list.push({
    no: 2,
    label: 'Вара (день недели)',
    glyph: VARA_GLYPH[base.getDay()],
    value: v?.day ?? WEEKDAY_GEN[base.getDay()],
    until: varaPlanet.value
      ? `день ${PLANET_GEN[varaPlanet.value] ?? varaPlanet.value}`
      : undefined,
    text: v?.good,
  })

  list.push({
    no: 3,
    label: 'Накшатра',
    glyph: '✧',
    value: n?.ru ?? '—',
    until: n ? untilLabel(n.dt_end, base) : undefined,
    chip: n ? `управитель — ${n.lord}` : undefined,
    chipVariant: 'neutral' as const,
    text: n
      ? `Накшатра ${n.nk_num} из 27${GANA_RU[n.gana] ? `, ${GANA_RU[n.gana]}` : ''}.`
        + ' Именно по ней считается ваша тара-бала ниже.'
      : undefined,
    highlight: true,
  })

  list.push({
    no: 4,
    label: 'Йога',
    glyph: '❖',
    value: NOT_CALCULATED,
    text: 'Нитья-йогу (27 сочетаний суммы долгот Солнца и Луны) сервис пока'
      + ' не считает — значение не показываем, чтобы не выдумывать.',
    muted: true,
  })

  list.push({
    no: 5,
    label: 'Карана',
    glyph: '☽︎',
    value: NOT_CALCULATED,
    text: 'Карану (половину титхи, 11 видов) сервис пока не считает. Из-за этого'
      + ' не виден и стоп-фактор Бхадра (Вишти-карана).',
    muted: true,
  })

  return list
})

// ─── Шапка кабинета ─────────────────────────────────────────────────────────

watchEffect(() => {
  const label = isToday.value
    ? `Сегодня, ${fmtDate(day.value)}`
    : `${WEEKDAY_GEN[day.value.getDay()][0].toUpperCase()}${WEEKDAY_GEN[day.value.getDay()].slice(1)}, ${fmtDate(day.value)}`
  setPageHeader({
    title: 'Моя панчанга',
    subtitle: 'день и ваша тара-бала',
    back: '/me',
    dateNav: {
      label,
      onPrev: () => shiftDay(-1),
      onNext: () => shiftDay(1),
      // Календарь-пикер появится вместе с экраном «Подобрать дату»; пока
      // кнопка возвращает на сегодня — это единственное, что она может делать
      // честно, не выдумывая недостающий UI.
      onPick: () => { day.value = today },
    },
    // Восход/закат в шапку не помещаем — они длиннее, чем выдерживает
    // .topbar__id, и съедают заголовок. Они видны в карточке панчанги.
    place: { city: place.value.city, time: fmtDate(day.value) },
  })
})

const updatedLabel = computed(() =>
  loadedAt.value ? `${fmtDate(loadedAt.value)}, ${fmtTime(loadedAt.value)}` : '')
</script>

<template>
  <section class="panel" aria-label="Панчанга дня">
    <UiCard v-if="error">
      <p class="today-msg">
        Не удалось получить расчёт: {{ error }}
      </p>
      <UiButton @click="load()">Повторить</UiButton>
    </UiCard>

    <UiCard v-else-if="loading && !dayInfo">
      <p class="today-msg">Считаем панчангу на {{ fmtDate(day) }}…</p>
    </UiCard>

    <template v-else-if="dayInfo">
      <!-- Доменное правило (HANDOFF §5.1): стоп-факторы стоят рядом с общей
           картиной дня, а не прячутся в конце страницы. -->
      <div class="grid-53">
        <UiCard title="Панчанга дня" note="пять элементов">
          <UiKv
            k="Титхи"
            :v="tithiNow ? `${tithiNow.paksha} ${tithiNow.name} (${tithiNow.num}) · ${tithiNow.quality.toLowerCase()}` : '—'"
            :tone="qualityVariant(tithiNow?.quality) === 'bad' ? 'bad' : qualityVariant(tithiNow?.quality) === 'good' ? 'good' : undefined"
          />
          <UiKv
            k="Вара"
            :v="varaDef ? `${varaDef.day} · ${varaPlanet}` : WEEKDAY_GEN[day.getDay()]"
          />
          <UiKv
            k="Накшатра"
            :v="nakNow ? `${nakNow.ru} (${nakNow.nk_num}) · ${nakNow.lord}` : '—'"
          />
          <UiKv k="Йога">
            <span class="today-na">{{ NOT_CALCULATED }}</span>
          </UiKv>
          <UiKv k="Карана">
            <span class="today-na">{{ NOT_CALCULATED }}</span>
          </UiKv>
          <UiKv
            k="Восход · закат"
            :v="sunrise && sunset ? `${fmtTime(sunrise)} · ${fmtTime(sunset)}` : '—'"
          />

          <UiDisclaimer>
            Панчангу оценивают целиком, пятью элементами сразу. Йогу и карану
            сервис пока не считает — учитывайте, что картина дня здесь неполная.
          </UiDisclaimer>
        </UiCard>

        <UiCard title="Важно знать сегодня" subtitle="ежедневные стоп-факторы">
          <UiWarnList :items="kalamItems" />
          <UiDisclaimer>
            Время считаем распространённым методом: светлое время суток
            (восход {{ sunrise ? fmtTime(sunrise) : '—' }} — закат
            {{ sunset ? fmtTime(sunset) : '—' }}) делится на 8 равных частей,
            номер части задаёт день недели. Школы расходятся в точке отсчёта
            восхода и в схеме для Гулики — это ориентир, а не запрет.
          </UiDisclaimer>
        </UiCard>
      </div>

      <UiSectionHead title="Пять элементов подробно" />
      <div class="grid-5">
        <UiStatCard
          v-for="item in cards"
          :key="item.no"
          :no="item.no"
          :label="item.label"
          :glyph="item.glyph"
          :value="item.value"
          :until="item.until"
          :chip="item.chip"
          :chip-variant="item.chipVariant"
          :text="item.text"
          :list-title="item.listTitle"
          :list="item.list"
          :highlight="item.highlight"
          :class="{ 'today-card--na': item.muted }"
        />
      </div>

      <UiSectionHead title="Тара-бала для вас" />
      <UiCard v-if="!hasProfile">
        <p class="today-msg">
          Тара-бала считается от вашей джанма-накшатры — накшатры Луны в момент
          рождения. Добавьте дату, время и место рождения, и этот блок появится.
        </p>
        <UiButton to="/me">Заполнить данные рождения</UiButton>
      </UiCard>

      <UiCard v-else-if="!janmaNakshatra">
        <p class="today-msg">
          Данные рождения есть, но гороскоп ещё не посчитан — без него
          джанма-накшатра неизвестна. Откройте «Обо мне», чтобы обновить расчёт.
        </p>
        <UiButton to="/me">Обо мне</UiButton>
      </UiCard>

      <UiCard v-else-if="tara && nakNow">
        <div class="tara">
          <div class="tara__pair">
            <div class="tara__nak">
              <div class="tara__cap">Ваша джанма-накшатра</div>
              <div class="tara__name">{{ janmaNakshatraName }}</div>
              <div class="hint">№ {{ janmaNakshatra }} из 27</div>
            </div>
            <div class="tara__arrow" aria-hidden="true">→</div>
            <div class="tara__nak">
              <div class="tara__cap">Накшатра дня</div>
              <div class="tara__name">{{ nakNow.ru }}</div>
              <div class="hint">№ {{ nakNow.nk_num }} из 27</div>
            </div>
          </div>

          <div class="tara__body">
            <div class="tara__head">
              <span class="tara__title">Тара «{{ tara.name }}»</span>
              <UiChip :variant="taraVariant">{{ tara.short }}</UiChip>
            </div>
            <p class="tara__pos">
              Тара <b>{{ tara.n }} из 9</b> · позиция <b>{{ tara.pos }}</b> из 27 от Джанмы ·
              {{ TARA_STRENGTH_RU[tara.strength] }}
            </p>
            <p class="tara__full">{{ tara.full }}</p>
            <p v-if="taraSchoolGood" class="tara__extra">
              <b>По школе подходит:</b> {{ taraSchoolGood }}
            </p>
            <UiDisclaimer v-if="tara.schoolAvoid" tone="warn">
              Сегодня 27-я накшатра от Джанмы — часть школ советует такой день
              обходить для важных начинаний. Другие школы называют 22-ю или 23-ю:
              это метод школы, а не канон.
            </UiDisclaimer>
          </div>
        </div>

        <UiDisclaimer>
          Тара-бала — <b>один из показателей дня</b>, а не вердикт. Её читают
          вместе с панчангой, стоп-факторами и вашей картой, а не вместо них.
        </UiDisclaimer>
      </UiCard>

      <template v-if="dayHoras.length">
        <UiSectionHead title="Ваш день по часам" />
        <UiCard title="Хоры дня" note="планетарные часы от восхода до заката">
          <div class="horas">
            <div
              v-for="h in dayHoras"
              :key="h.num"
              class="horas__row"
              :class="{ 'horas__row--now': h.current }"
            >
              <span class="horas__time">{{ h.from }} – {{ h.to }}</span>
              <span class="horas__planet">{{ h.planet }}</span>
              <span v-if="h.current" class="horas__now">сейчас</span>
            </div>
          </div>
          <UiDisclaimer>
            Показан только управитель каждой хоры — так их отдаёт расчёт.
            Оценок «благоприятно / неблагоприятно» здесь нет: такой модели
            у сервиса пока нет.
          </UiDisclaimer>
        </UiCard>
      </template>

      <UiSectionHead title="Астрологическая причина дня" />
      <UiCard>
        <UiReasonList :items="reasons" />
      </UiCard>

      <UiNoteBar :updated="updatedLabel">
        Экран построен на расчёте панчанги и транзитов Луны на
        {{ fmtDate(day) }} для места «{{ place.city }}»<template v-if="!usesProfilePlace">
          (место по умолчанию — профиль рождения не заполнен)</template><template v-else>
          (по месту рождения из профиля)</template>, описаниях из справочника
        панчанги и титх<template v-if="tara"> и расчёте тара-балы от вашей
          джанма-накшатры</template>. Йога и карана в расчёт не входят.
      </UiNoteBar>

      <UiDisclaimer>
        Панчанга — ориентир, а не запрет. «Неблагоприятные» отрезки и тары
        традиция считает поводом для внимательности, а не поводом отменять день;
        точный расчёт под конкретное событие делает астролог.
      </UiDisclaimer>
    </template>
  </section>
</template>

<style scoped>
.today-msg {
  margin: 0 0 12px;
  font-size: 14px;
  color: var(--body);
  line-height: 1.6;
}

.today-na {
  color: var(--muted);
  font-style: italic;
}

/* Карточка элемента, которого расчёт не даёт: приглушена, чтобы её не читали
   как полноценное значение. */
.today-card--na :deep(.statcard__value) {
  color: var(--muted);
  font-style: italic;
  font-size: 16px;
}

/* ── Тара-бала ── */
.tara {
  display: grid;
  grid-template-columns: minmax(220px, 300px) 1fr;
  gap: 22px;
  align-items: start;
}

.tara__pair {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: var(--surface-2);
}

.tara__nak {
  flex: 1;
  text-align: center;
  min-width: 0;
}

.tara__cap {
  font-size: 11.5px;
  color: var(--muted);
  line-height: 1.35;
}

.tara__name {
  font-family: var(--serif);
  font-size: 17px;
  color: var(--ink);
  margin-top: 4px;
  line-height: 1.2;
}

.tara__arrow {
  flex: none;
  color: var(--accent);
  font-size: 18px;
}

.tara__head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.tara__title {
  font-family: var(--serif);
  font-size: 20px;
  color: var(--ink);
}

.tara__pos {
  margin: 9px 0 0;
  font-size: 13px;
  color: var(--muted);
}

.tara__pos b {
  color: var(--ink);
  font-weight: 600;
}

.tara__full,
.tara__extra {
  margin: 11px 0 0;
  font-size: 14px;
  line-height: 1.6;
  color: var(--body);
}

.tara__extra b {
  color: var(--ink);
  font-weight: 500;
}

/* ── Хоры ── */
.horas {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 8px;
}

.horas__row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 9px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  font-size: 13px;
}

.horas__row--now {
  border-color: var(--accent-line);
  background: var(--accent-soft);
}

.horas__time {
  color: var(--muted);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.horas__planet {
  color: var(--ink);
  font-weight: 500;
}

.horas__now {
  margin-left: auto;
  font-size: 11.5px;
  color: var(--accent-ink);
}

@media (max-width: 980px) {
  .tara {
    grid-template-columns: 1fr;
  }
}
</style>
