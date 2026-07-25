<script setup lang="ts">
// Страница «Карта» — раши-чакра (D1) пользователя на живых данных.
//
// Источники:
//   POST /api/horoscope        → лагна, планеты (знак, градус, накшатра, пада,
//                                retro, is_stationary, speed)
//   calculators/chart.ts       → analyzeChart / signForHouse (достоинство и
//                                трактовки приходят готовыми в строках разбора)
//   content/chart_geometry.json→ полигоны северной карты и сетка южной
//   content/houses.json        → группы, пурушартха, каракаки, диг-бала, описания
//   content/signs.json         → управитель, стихия, качество знака
//   content/placements.json    → трактовки «планета в доме» и «планета в знаке»
//   content/retrograde.json    → трактовки вакри
//   content/disclaimers.json   → готовые оговорки, свои не сочиняем
//
// ЧЕГО ЗДЕСЬ НЕТ: числовых оценок карты, «силы планет в баллах», шад-балы,
// аспектов и йог. Ни модели, ни данных под ними нет (docs/ASTROLOGER-REVIEW.md
// Б6) — пустое место честнее правдоподобной выдумки.
//
// Режим «по Луне» (время рождения неизвестно): лагна и дома НЕДОСТОВЕРНЫ.
// Карта домов от Лагны в этом режиме не показывается вовсе; вместо неё —
// чандра-лагна с явной пометкой, а если под вопросом и знак Луны, карта
// блокируется с объяснением. Так же, как это сделано на /me.
import {
  useJyotish, analyzeChart, signForHouse,
  loadChartGeometry, loadHouses, loadSigns, loadPlacements,
  loadRetrograde,
} from '~/composables/useJyotish'
import type { PlanetRu } from '~/composables/useJyotish'
import type { HoroPlanet } from '~/composables/useBirthProfile'
import type { PositionRow, WheelHouse } from '~/components/chart/types'

definePageMeta({ layout: 'app', middleware: 'auth' })
useHead({ title: 'Карта — Jyotish' })

// Проф-глубина включается классом .is-pro на корне раскладки (UiProOnly),
// поэтому useAudience здесь не нужен: переключение режима не должно
// перестраивать таблицу и раскрывающиеся блоки.
const { setPageHeader } = usePageHeader()
const {
  profile, horoscope, loading, error, hasProfile,
  lagnaReliable, fetchHoroscope,
} = useBirthProfile()
const { lagnaSign } = useJyotish()

// ─── Справочники символов ───────────────────────────────────────────────────
// Те же таблицы, что на /me и в исходнике коллеги (CF_PL_SHORT, sign_short.json).
// Держим их константами страницы: тянуть отдельным чанком 200 байт незачем.

const PLANET_GLYPH: Record<string, string> = {
  'Солнце': '☉︎', 'Луна': '☾︎', 'Марс': '♂︎', 'Меркурий': '☿︎', 'Юпитер': '♃︎',
  'Венера': '♀︎', 'Сатурн': '♄︎', 'Раху': '☊︎', 'Кету': '☋︎',
}
const PLANET_SHORT: Record<string, string> = {
  'Солнце': 'Су', 'Луна': 'Лу', 'Марс': 'Ма', 'Меркурий': 'Ме', 'Юпитер': 'Юп',
  'Венера': 'Ве', 'Сатурн': 'Са', 'Раху': 'Ра', 'Кету': 'Ке',
}
/** content/sign_short.json — 12 сокращений знаков. */
const SIGN_SHORT = [
  'Овен', 'Телец', 'Близн', 'Рак', 'Лев', 'Дева',
  'Весы', 'Скорп', 'Стрел', 'Козер', 'Водол', 'Рыбы',
]
const SIGN_GLYPH = ['♈︎', '♉︎', '♊︎', '♋︎', '♌︎', '♍︎', '♎︎', '♏︎', '♐︎', '♑︎', '♒︎', '♓︎']
const MONTHS_RU = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
]
const DIGNITY_RU = { exalted: 'экзальтация', own: 'свой знак', debilitated: 'падение' } as const

/** Поля движения, которые API отдаёт по каждой планете. В HoroPlanet
 * (composables/useBirthProfile.ts) описан только необязательный retro: тип
 * писался, когда бэкенд ретроградность ещё не считал. Читаем аккуратно,
 * чужой файл не трогаем. */
interface PlanetMotion {
  retro?: boolean
  is_stationary?: boolean
  speed?: number
}

// ─── Шапка ──────────────────────────────────────────────────────────────────

const birthLine = computed(() => {
  const p = profile.value
  if (!p?.date) return 'данные рождения не заполнены'
  const [y, m, d] = p.date.split('-').map(Number)
  const date = Number.isFinite(y) ? `${d} ${MONTHS_RU[(m || 1) - 1]} ${y}` : p.date
  const time = p.timeUnknown ? 'время неизвестно' : p.time
  return [[date, time].filter(Boolean).join(', '), p.city].filter(Boolean).join(' · ')
})

watchEffect(() => {
  setPageHeader({
    title: 'Карта рождения',
    subtitle: hasProfile.value ? birthLine.value : 'заполните данные рождения',
    subtitleLink: hasProfile.value ? { text: 'изменить', to: '/me' } : null,
  })
})

onMounted(() => { if (hasProfile.value) fetchHoroscope() })

// ─── Ленивые справочники ────────────────────────────────────────────────────
// Всё через useJyotish: страница не импортирует ~content напрямую.

const geometry = ref<Record<string, any> | null>(null)
const housesRef = ref<any | null>(null)
const signsRef = ref<any | null>(null)
const placementsMeta = ref<any | null>(null)
const retroRef = ref<any | null>(null)

/** Дисклеймеры достоверности — из content/disclaimers.json по ключу секции
 * (задача 2.8): своих формулировок на странице нет. */
const { disclaimer } = useDisclaimers()

onMounted(async () => {
  const [g, h, s, pl, r] = await Promise.allSettled([
    loadChartGeometry(), loadHouses(), loadSigns(),
    loadPlacements(), loadRetrograde(),
  ])
  if (g.status === 'fulfilled') geometry.value = g.value
  if (h.status === 'fulfilled') housesRef.value = h.value
  if (s.status === 'fulfilled') signsRef.value = s.value
  if (pl.status === 'fulfilled') placementsMeta.value = pl.value
  if (r.status === 'fulfilled') retroRef.value = r.value
})

/** Справка по дому 1..12 из houses.json. */
function houseDef(n: number): any | null {
  return (housesRef.value?.houses ?? []).find((x: any) => x.n === n) ?? null
}
/** Справка по знаку 1..12 из signs.json. */
function signDef(n: number): any | null {
  return signsRef.value?.signs?.[n - 1] ?? null
}
/** Трактовка вакри для планеты из retrograde.json. */
function retroDef(name: string): any | null {
  return (retroRef.value?.planets ?? []).find((x: any) => x.name === name) ?? null
}

// ─── Планеты из ответа API ──────────────────────────────────────────────────

const apiPlanets = computed<HoroPlanet[]>(
  () => (horoscope.value?.planets ?? []).filter((p) => p.available),
)
const apiByName = computed(() => new Map(apiPlanets.value.map((p) => [p.name, p])))

const moon = computed(() => apiByName.value.get('Луна') ?? null)

/** При неизвестном времени Луна проходит до ~15,4° за сутки: стоит она ближе
 * половины этого окна к границе знака — знак Луны тоже под вопросом.
 * Логика повторяет /me: одна карта, одна честность. */
const moonSignUncertain = computed(() => {
  const m = moon.value
  if (!m || lagnaReliable.value) return false
  return m.deg_in_sign < 7.7 || m.deg_in_sign > 30 - 7.7
})

// ─── Точка отсчёта карты ────────────────────────────────────────────────────
// 'lagna' — классическая раши-чакра от асцендента;
// 'moon'  — чандра-лагна: первым домом считается знак Луны.

type Basis = 'lagna' | 'moon'

const basisPref = ref<Basis>('lagna')

/** Реально применённая точка отсчёта. При недостоверной лагне выбора нет. */
const basis = computed<Basis>(() => (lagnaReliable.value ? basisPref.value : 'moon'))

const originSign = computed<number | null>(() => (
  basis.value === 'moon' ? (moon.value?.sign_num ?? null) : lagnaSign.value
))

/** Можно ли вообще рисовать дома.
 * От Лагны — только при известном времени. От Луны — при известном знаке Луны:
 * если время неизвестно и Луна у границы знака, чандра-лагна тоже произвольна,
 * и рисовать её было бы такой же выдумкой, как лагну. */
const housesMeaningful = computed(() => {
  if (!originSign.value) return false
  return basis.value === 'lagna' ? lagnaReliable.value : !moonSignUncertain.value
})

/** Трактовки домов (placements.houses, houses.json) допустимы только для
 * настоящих бхав от Лагны: тексты написаны про них, а не про дома от Луны. */
const houseTextsAllowed = computed(() => basis.value === 'lagna' && lagnaReliable.value)

const originLabel = computed(() => (basis.value === 'moon' ? 'дома от Луны' : 'дома от Лагны'))
const houseColumnLabel = computed(() => (basis.value === 'moon' ? 'Дом от Луны' : 'Дом'))
const housesCardTitle = computed(() => {
  if (!housesMeaningful.value) return 'Знаки планет'
  return basis.value === 'moon' ? 'Дома от Луны и знаки' : 'Дома и знаки'
})

// ─── Переключатели вида ─────────────────────────────────────────────────────

const variant = ref<'north' | 'south'>('north')
const showGroups = ref(false)

// ─── Разбор карты ───────────────────────────────────────────────────────────

/** Планеты в форме, которую понимает analyzeChart. */
const planetInput = computed(() => apiPlanets.value.map((p) => ({
  name: p.name as PlanetRu,
  sign: p.sign_num,
  retro: !!(p as HoroPlanet & PlanetMotion).retro,
})))

/** Строки разбора относительно выбранной точки отсчёта.
 * Порядок — традиционный (Солнце → Кету), его задаёт сам analyzeChart. */
const rows = computed(() => {
  const origin = originSign.value
  if (!origin || !planetInput.value.length) return []
  return analyzeChart(origin, planetInput.value)
})

/** Клетки карты: 12 домов, знак в каждом, планеты. */
const wheelHouses = computed<WheelHouse[]>(() => {
  const origin = originSign.value
  if (!origin) return []
  const out: WheelHouse[] = []
  for (let h = 1; h <= 12; h++) {
    const sign = signForHouse(origin, h)
    out.push({
      house: h,
      sign,
      signShort: SIGN_SHORT[sign - 1] ?? '',
      group: houseDef(h)?.groups?.[0] ?? null,
      planets: rows.value
        .filter((r) => r.sign === sign)
        .map((r) => {
          const api = apiByName.value.get(r.planet) as (HoroPlanet & PlanetMotion) | undefined
          return {
            name: r.planet,
            short: PLANET_SHORT[r.planet] ?? r.planet.slice(0, 2),
            retro: !!api?.retro,
            stationary: !!api?.is_stationary,
            dignity: r.dignity,
          }
        }),
    })
  }
  return out
})

const wheelAria = computed(() => {
  const s = originSign.value
  if (!s) return 'Карта рождения'
  const style = variant.value === 'north' ? 'северное начертание' : 'южное начертание'
  const from = basis.value === 'moon' ? 'от Луны' : 'от Лагны'
  return `Раши-чакра, ${style}, дома ${from} в знаке ${signDef(s)?.name ?? SIGN_SHORT[s - 1]}`
})

// ─── Таблица положений ──────────────────────────────────────────────────────

const positionRows = computed<PositionRow[]>(() => rows.value.map((r) => {
  const api = apiByName.value.get(r.planet) as (HoroPlanet & PlanetMotion) | undefined
  return {
    planet: r.planet,
    glyph: PLANET_GLYPH[r.planet] ?? api?.abbr ?? '',
    signRu: r.signData.name,
    signShort: SIGN_SHORT[r.sign - 1] ?? '',
    house: housesMeaningful.value ? r.house : null,
    nakshatra: api?.nakshatra_ru ?? '—',
    pada: api?.pada ?? 0,
    nakLord: api?.nk_lord ?? '—',
    dignity: r.dignity,
    retro: !!api?.retro,
    stationary: !!api?.is_stationary,
    degDms: api?.deg_in_sign_dms ?? '',
    speed: typeof api?.speed === 'number' ? api.speed : null,
  }
}))

const retroPlanets = computed(() => positionRows.value.filter((r) => r.retro))
const stationaryPlanets = computed(() => positionRows.value.filter((r) => r.stationary))

// ─── Плитки ─────────────────────────────────────────────────────────────────

/** Где стоит управитель Лагны (лагнеша). Механическая выкладка из карты,
 * не трактовка: знак лагны → его управитель → дом, в котором тот стоит. */
const lagnesha = computed(() => {
  const s = lagnaSign.value
  if (!s || !lagnaReliable.value) return null
  const ruler = signDef(s)?.ruler ?? horoscope.value?.lagna.lord ?? null
  if (!ruler) return null
  const row = rows.value.find((r) => r.planet === ruler)
  return { name: ruler as string, house: row?.house ?? null, sign: row?.signData.name ?? null }
})

const tiles = computed(() => {
  const h = horoscope.value
  if (!h) return []
  const out: Array<{ key: string; label: string; value: string; meta: string; glyph: string }> = []

  out.push(lagnaReliable.value
    ? {
        key: 'lagna',
        label: 'Лагна (асцендент)',
        value: h.lagna.sign_ru,
        meta: `${h.lagna.deg_in_sign_dms} · управитель ${h.lagna.lord}`,
        glyph: SIGN_GLYPH[h.lagna.sign_num - 1] ?? '',
      }
    : {
        key: 'lagna',
        label: 'Лагна (асцендент)',
        value: '—',
        meta: 'нужно точное время рождения',
        glyph: '',
      })

  const lg = lagnesha.value
  out.push(lg
    ? {
        key: 'lagnesha',
        label: 'Управитель лагны',
        value: lg.name,
        meta: lg.house ? `${lg.house}-й дом · ${lg.sign}` : 'положение не определено',
        glyph: PLANET_GLYPH[lg.name] ?? '',
      }
    : {
        key: 'lagnesha',
        label: 'Управитель лагны',
        value: '—',
        meta: 'зависит от лагны',
        glyph: '',
      })

  const m = moon.value
  out.push({
    key: 'moon',
    label: 'Чандра-лагна (знак Луны)',
    value: m?.sign_ru ?? '—',
    // Знак Луны при неизвестном времени тоже может оказаться другим — молчать
    // об этом нельзя, иначе плитка выглядит достовернее, чем она есть.
    meta: !m
      ? ''
      : moonSignUncertain.value
        ? 'знак под вопросом: Луна у границы, время рождения неизвестно'
        : `${h.nk.ru}, ${h.nk.pada} пада`,
    glyph: '☾︎',
  })

  // Ретроградность — реальный флаг из ответа API, а не догма из описаний.
  out.push({
    key: 'retro',
    label: 'Ретроградные планеты',
    value: retroPlanets.value.length
      ? retroPlanets.value.map((r) => r.planet).join(', ')
      : 'нет',
    meta: retroPlanets.value.length
      ? 'вакри — движение по долготе отрицательное'
      : 'все планеты идут прямо',
    glyph: '℞',
  })

  return out
})

// ─── Трактовки «планета в доме и знаке» ─────────────────────────────────────

const placementRows = computed(() => rows.value.map((r) => {
  const api = apiByName.value.get(r.planet) as (HoroPlanet & PlanetMotion) | undefined
  const pos: string[] = []
  if (housesMeaningful.value) pos.push(`${r.house}-й дом`)
  pos.push(r.signData.name)
  return {
    key: r.planet,
    name: r.planet,
    glyph: PLANET_GLYPH[r.planet] ?? '',
    position: pos.join(' · '),
    dignity: r.dignity,
    dignityLabel: r.dignity ? DIGNITY_RU[r.dignity] : '',
    retro: !!api?.retro,
    houseText: houseTextsAllowed.value ? r.inHouseText : '',
    houseName: houseTextsAllowed.value ? r.houseData?.name ?? '' : '',
    signText: r.inSignText,
    signInfo: signDef(r.sign),
    retroInfo: api?.retro ? retroDef(r.planet) : null,
  }
}))

// ─── Дома ───────────────────────────────────────────────────────────────────

const houseRows = computed(() => {
  const origin = originSign.value
  if (!origin || !houseTextsAllowed.value) return []
  return Array.from({ length: 12 }, (_, i) => {
    const n = i + 1
    const sign = signForHouse(origin, n)
    const def = houseDef(n)
    const sd = signDef(sign)
    return {
      n,
      def,
      sign,
      signName: sd?.name ?? SIGN_SHORT[sign - 1],
      ruler: sd?.ruler ?? '',
      planets: rows.value.filter((r) => r.house === n).map((r) => r.planet),
      /** Где стоит управитель этого дома — механическая выкладка, не трактовка. */
      rulerAt: rows.value.find((r) => r.planet === sd?.ruler)?.house ?? null,
    }
  })
})

const GROUP_TONE: Record<string, 'good' | 'bad' | 'neutral'> = {
  'Трикона': 'good', 'Кендра': 'neutral', 'Духстана': 'bad', 'Упачая': 'neutral',
}
</script>

<template>
  <section class="panel" aria-label="Карта рождения">
    <!-- ─── Профиля нет: не выдумываем форму, отправляем на «Обо мне» ────── -->
    <UiCard
      v-if="!hasProfile"
      title="Нужны данные рождения"
      subtitle="Карта строится по дате, времени и месту рождения."
    >
      <p style="margin:0 0 16px;font-size:14px">
        Заполните их один раз на странице «Обо мне» — карта и все остальные
        разделы подхватят их автоматически.
      </p>
      <UiButton to="/me">Заполнить данные рождения</UiButton>
    </UiCard>

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

        <!-- ─── Режим «по Луне»: лагна и дома недостоверны ───────────────── -->
        <UiDisclaimer v-if="!lagnaReliable" tone="warn">
          Время рождения не указано, поэтому <b>лагна и дома рождения не рассчитываются</b>:
          за сутки асцендент проходит все двенадцать знаков, и любая карта домов была бы
          выдумкой, а не расчётом.
          <template v-if="!moonSignUncertain">
            Ниже показана <b>чандра-лагна</b> — карта, где первым домом взят знак Луны.
            Это самостоятельный вспомогательный приём, а не замена карты рождения:
            трактовки домов к ней не прикладываются.
          </template>
          <template v-else>
            Знак Луны в этот день тоже под вопросом (она стоит близко к границе знака),
            поэтому и чандра-лагну построить не на чем.
          </template>
          <br>
          <NuxtLink to="/me">Указать время рождения</NuxtLink> — и карта построится полностью.
        </UiDisclaimer>

        <!-- ─── Карта ───────────────────────────────────────────────────── -->
        <UiSectionHead title="Раши-чакра (D1)" />

        <UiCard v-if="!housesMeaningful && !lagnaReliable && moonSignUncertain">
          <p style="margin:0;font-size:14px">
            Карту показать не на чем: без времени рождения нет ни лагны, ни надёжного
            знака Луны. Всё остальное на этой странице — знаки планет, накшатры, пады и
            достоинства — остаётся рабочим, потому что от времени почти не зависит.
          </p>
        </UiCard>

        <div v-else class="grid-53">
          <UiCard class="chart-card">
            <template #head>
              <div>
                <h2 class="card__title">
                  {{ variant === 'north' ? 'Северное начертание' : 'Южное начертание' }}
                </h2>
                <div class="card__sub">
                  {{ variant === 'north'
                    ? 'дома закреплены за ромбами, знаки едут'
                    : 'знаки закреплены за клетками, дома едут' }}
                </div>
              </div>
              <div class="seg chart-seg" role="group" aria-label="Начертание карты">
                <button
                  type="button"
                  :class="{ 'is-on': variant === 'north' }"
                  :aria-pressed="variant === 'north'"
                  @click="variant = 'north'"
                >
                  Северная
                </button>
                <button
                  type="button"
                  :class="{ 'is-on': variant === 'south' }"
                  :aria-pressed="variant === 'south'"
                  @click="variant = 'south'"
                >
                  Южная
                </button>
              </div>
            </template>

            <ChartWheel
              :geometry="geometry"
              :variant="variant"
              :houses="wheelHouses"
              :groups="showGroups && houseTextsAllowed"
              :show-houses="housesMeaningful"
              :origin-label="originLabel"
              :aria-label="wheelAria"
            />

            <div class="chart-legend">
              <span><b class="lg lg--ex">Ср</b> экзальтация</span>
              <span><b class="lg lg--deb">Ср</b> падение</span>
              <span><b class="lg">Ср℞</b> вакри (ретроградна)</span>
              <span><b class="lg">Ср·</b> станция (почти без движения)</span>
            </div>

            <!-- Южная карта: клетки закреплены за знаками, а не за домами (Б7). -->
            <div v-if="variant === 'south'" class="chart-note">
              <UiMethodNote id="Б7" />
            </div>

            <UiProOnly v-if="houseTextsAllowed">
              <div class="chart-tools">
                <label class="chart-check">
                  <input v-model="showGroups" type="checkbox">
                  подсветить группы домов
                </label>
                <div v-if="showGroups" class="chart-legend chart-legend--groups">
                  <span><i class="lg-sw lg-sw--tri" />трикона</span>
                  <span><i class="lg-sw lg-sw--ken" />кендра</span>
                  <span><i class="lg-sw lg-sw--duh" />духстана</span>
                  <span><i class="lg-sw lg-sw--upa" />упачая</span>
                </div>
                <p v-if="showGroups && housesRef?.groups_note" class="hint" style="margin:8px 0 0">
                  {{ housesRef.groups_note }}
                </p>
              </div>

              <div v-if="lagnaReliable" class="chart-tools">
                <div class="seg" role="group" aria-label="Точка отсчёта домов">
                  <button
                    type="button"
                    :class="{ 'is-on': basisPref === 'lagna' }"
                    :aria-pressed="basisPref === 'lagna'"
                    @click="basisPref = 'lagna'"
                  >
                    От Лагны
                  </button>
                  <button
                    type="button"
                    :class="{ 'is-on': basisPref === 'moon' }"
                    :aria-pressed="basisPref === 'moon'"
                    @click="basisPref = 'moon'"
                  >
                    От Луны
                  </button>
                </div>
                <p class="hint" style="margin:8px 0 0">
                  Чандра-лагна — вспомогательный взгляд на ту же карту: положения планет
                  не меняются, меняется только точка отсчёта домов. Трактовки домов
                  написаны про бхавы от Лагны, поэтому к карте от Луны не прикладываются.
                </p>
              </div>
            </UiProOnly>
          </UiCard>

          <UiCard :title="housesCardTitle" :heading-level="3">
            <template v-if="housesMeaningful">
              <UiKv v-for="c in wheelHouses" :key="c.house" :k="`${c.house}-й дом`">
                {{ signDef(c.sign)?.name ?? c.signShort }}<template v-if="signDef(c.sign)?.ruler">
                  · упр. {{ signDef(c.sign).ruler }}</template><template v-if="c.planets.length">
                  · {{ c.planets.map((p) => p.name).join(', ') }}</template>
              </UiKv>
              <p class="hint" style="margin:14px 0 0">
                Дома целознаковые (Whole Sign): весь знак = один дом. Так же считает и API.
                <template v-if="basis === 'moon'">
                  Отсчёт ведётся от знака Луны, а не от Лагны.
                </template>
              </p>
            </template>
            <template v-else>
              <UiKv v-for="r in positionRows" :key="r.planet" :k="r.planet">
                {{ r.signRu }} · {{ r.nakshatra }} {{ r.pada }}
              </UiKv>
              <p class="hint" style="margin:14px 0 0">
                Дома не показаны: без времени рождения их не из чего считать.
              </p>
            </template>
          </UiCard>
        </div>

        <!-- Оговорка про расстановку знаков по домам нужна только там, где
             дома действительно показаны. -->
        <UiDisclaimer v-if="housesMeaningful" :entry="disclaimer('chart-full')" />

        <!-- ─── Таблица положений ───────────────────────────────────────── -->
        <UiSectionHead title="Положения планет" />
        <UiCard>
          <ChartPositions
            :rows="positionRows"
            :show-house="housesMeaningful"
            :house-label="houseColumnLabel"
          />

          <p class="hint" style="margin:16px 0 0">
            Достоинство определяется по знаку, без проверки точного градуса экзальтации —
            так же, как в исходной версии расчёта.
            <template v-if="housesMeaningful">
              Дома — целознаковые (Whole Sign) от {{ basis === 'moon' ? 'Луны' : 'Лагны' }}.
            </template>
          </p>

          <UiProOnly>
            <p class="hint" style="margin:10px 0 0">
              Движение берётся из скорости по долготе, которую отдаёт эфемерида:
              отрицательная — вакри, близкая к нулю — станция. Это расчёт, а не
              справочное «планета Х всегда ретроградна».
            </p>
          </UiProOnly>
        </UiCard>

        <!-- Узлы: расчёт по истинному узлу расходится с описанием в content/ -->
        <div class="chart-note">
          <UiMethodNote id="А2" />
        </div>

        <UiCard v-if="retroPlanets.length || stationaryPlanets.length" title="Движение планет" :heading-level="3">
          <p v-if="retroPlanets.length" style="margin:0;font-size:14px">
            Ретроградны (вакри):
            <b>{{ retroPlanets.map((r) => r.planet).join(', ') }}</b>.
          </p>
          <p v-else style="margin:0;font-size:14px">Ретроградных планет в карте нет.</p>
          <p v-if="stationaryPlanets.length" style="margin:10px 0 0;font-size:14px">
            Почти без движения (станция):
            <b>{{ stationaryPlanets.map((r) => r.planet).join(', ') }}</b> — в такие дни
            планета меняет направление, её тема в карте подчёркнута.
          </p>
          <UiProOnly v-if="retroRef?.strength_note">
            <p class="hint" style="margin:12px 0 0">{{ retroRef.strength_note }}</p>
            <p v-if="retroRef.debil_note" class="hint" style="margin:8px 0 0">
              {{ retroRef.debil_note }}
            </p>
          </UiProOnly>
        </UiCard>
        <UiDisclaimer v-if="retroPlanets.length" :entry="disclaimer('retro')" />

        <!-- ─── Трактовки: планета в доме и знаке ───────────────────────── -->
        <UiSectionHead title="Планета в доме и знаке" />
        <UiCard>
          <p v-if="placementsMeta?.intro" class="hint" style="margin:0 0 16px">
            {{ placementsMeta.intro }}
          </p>
          <p v-if="!houseTextsAllowed" class="hint" style="margin:0 0 16px">
            Показаны только трактовки по знакам: трактовка «планета в доме» требует
            достоверных домов, а их сейчас нет.
          </p>

          <ChartDisclosure
            v-for="p in placementRows"
            :key="p.key"
            :title="p.name"
            :glyph="p.glyph"
            :meta="p.position"
            :tag="p.dignityLabel || (p.retro ? '℞ вакри' : '')"
            :tag-tone="p.dignity === 'exalted' ? 'good' : p.dignity === 'debilitated' ? 'bad' : 'neutral'"
          >
            <p v-if="p.houseText" style="margin:0 0 10px">
              <b v-if="p.houseName">{{ p.houseName }}. </b>{{ p.houseText }}
            </p>
            <p v-if="p.signText" style="margin:0">{{ p.signText }}</p>
            <p v-if="!p.houseText && !p.signText" class="hint" style="margin:0">
              Трактовки для этого положения в справочнике нет.
            </p>

            <UiProOnly>
              <div class="disc-item__pro">
                <UiKv v-if="p.signInfo" k="Знак">
                  {{ p.signInfo.name }} · {{ p.signInfo.element }} ·
                  {{ p.signInfo.quality }} · упр. {{ p.signInfo.ruler }}
                </UiKv>
                <p v-if="p.retroInfo?.retro && p.retroInfo.retro !== '—'" style="margin:10px 0 0;font-size:13.5px">
                  <b>Вакри.</b> {{ p.retroInfo.retro }}
                </p>
              </div>
            </UiProOnly>
          </ChartDisclosure>

          <p v-if="placementsMeta?.guru_note" class="hint" style="margin:16px 0 0">
            {{ placementsMeta.guru_note }}
          </p>
        </UiCard>
        <UiDisclaimer :entry="disclaimer('placements')" />
        <UiDisclaimer :entry="disclaimer('signs')" />

        <!-- ─── Дома ────────────────────────────────────────────────────── -->
        <template v-if="houseRows.length">
          <UiSectionHead title="Двенадцать домов" />
          <UiCard>
            <p v-if="housesRef?.intro" class="hint" style="margin:0 0 16px">
              {{ housesRef.intro }}
            </p>

            <ChartDisclosure
              v-for="h in houseRows"
              :key="h.n"
              :title="`${h.n}-й дом — ${h.def?.name ?? ''}`"
              :meta="`${h.signName} · упр. ${h.ruler}${h.planets.length ? ' · ' + h.planets.join(', ') : ''}`"
              :tag="h.def?.groups?.[0] || ''"
              :tag-tone="GROUP_TONE[h.def?.groups?.[0] || ''] || 'neutral'"
            >
              <p v-if="h.def?.desc" style="margin:0">{{ h.def.desc }}</p>

              <UiProOnly>
                <div class="disc-item__pro">
                  <UiKv k="Санскрит" :v="h.def?.skt" />
                  <UiKv k="Пурушартха" :v="h.def?.purushartha" />
                  <UiKv k="Группы" :v="(h.def?.groups || []).join(', ')" />
                  <UiKv k="Караки" :v="h.def?.karakas" />
                  <UiKv v-if="h.def?.digbala && h.def.digbala !== '—'" k="Диг-бала" :v="h.def.digbala" />
                  <UiKv k="Управитель дома">
                    {{ h.ruler }}<template v-if="h.rulerAt"> — стоит в {{ h.rulerAt }}-м доме</template>
                  </UiKv>
                  <p v-if="h.def?.desc_full" style="margin:12px 0 0;font-size:13.5px">
                    {{ h.def.desc_full }}
                  </p>
                  <p v-if="h.def?.watch" class="hint" style="margin:10px 0 0">{{ h.def.watch }}</p>
                </div>
              </UiProOnly>
            </ChartDisclosure>

            <UiProOnly v-if="housesRef?.digbala_summary">
              <p class="hint" style="margin:16px 0 0">{{ housesRef.digbala_summary }}</p>
            </UiProOnly>
            <p v-if="housesRef?.detail_note" class="hint" style="margin:10px 0 0">
              {{ housesRef.detail_note }}
            </p>
          </UiCard>
          <UiDisclaimer :entry="disclaimer('house-chart')" />
        </template>

        <UiDisclaimer :entry="disclaimer('chart-analysis')" />
      </template>
    </template>
  </section>
</template>

<style scoped>
/* Всё остальное оформление страницы — в assets/css/tokens.css рядом с
   остальными правилами кабинета (там же адаптив). */
.chart-note { margin-top: 12px; }
</style>
