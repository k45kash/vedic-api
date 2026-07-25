<script setup lang="ts">
// Страница «Обо мне» — натальная карта пользователя на реальных данных.
//
// Источники: профиль рождения (composables/useBirthProfile) + ответ
// POST /api/horoscope + калькуляторы (analyzeChart/dignity) + справочник
// накшатр (content/nakshatras.json, грузится лениво — 279 КБ).
//
// Чего здесь НЕТ и быть не может, пока бэкенд не отдаёт:
//   • даши (Виншоттари) — API их не считает вообще;
//   • ретроградность планет — поля retro в ответе нет;
//   • персональных оценок «N/10» — считать не из чего.
// Лучше пустое место, чем правдоподобная выдумка (docs/SERVICE-IA.md §9).
import {
  useJyotish, dignity, isGandantaNakshatra,
  loadNakshatras, loadDisclaimers,
} from '~/composables/useJyotish'
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
const { chart, janmaNakshatra } = useJyotish()

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
// Четвёртой плиткой раньше была «текущая маха-даша» — убрана: даши не считаются
// ни на бэкенде, ни здесь. Вместо неё — управитель накшатры (реальное поле nk.lord).

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
// Ретро-флага в ответе API нет, поэтому «вакри» не показываем ни в каком виде.

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
      dignity: r.dignity ? DIGNITY_SHORT[r.dignity] : null,
      houseText: lagnaReliable.value ? r.inHouseText : '',
      signText: r.inSignText,
      pro: i >= SIMPLE_PLANETS,
    }
  })
})

const hiddenPlanets = computed(() => Math.max(0, planetRows.value.length - SIMPLE_PLANETS))

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

// ─── Готовые дисклеймеры (content/disclaimers.json, ленивая загрузка) ───────

const disc = ref<Record<string, string>>({})
onMounted(async () => {
  try {
    const d = await loadDisclaimers()
    const map: Record<string, string> = {}
    for (const s of d.sections ?? []) if (!map[s.section]) map[s.section] = s.text
    disc.value = map
  } catch {
    disc.value = {}
  }
})
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
        <UiSectionHead title="Планеты по домам и знакам" />
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
            {{ row.houseText || row.signText }}
            <UiProOnly v-if="row.houseText && row.signText">
              <p class="hint" style="margin:8px 0 0">{{ row.signText }}</p>
            </UiProOnly>
          </UiProRow>

          <UiProOnly>
            <p class="hint" style="margin:14px 0 0">
              <template v-if="lagnaReliable">Дома — Whole Sign от Лагны. </template>
              Достоинство определяется по знаку, без точного градуса экзальтации.
              Ретро-статус (вакри) не показан: API его не отдаёт, а рисовать его
              «по памяти» нельзя.
            </p>
          </UiProOnly>
          <p v-if="hiddenPlanets" class="hint hint--simple" style="margin:14px 0 0">
            Ещё {{ hiddenPlanets }} планет и карта домов — в режиме «Астролог».
          </p>
        </UiCard>
        <UiDisclaimer v-if="disc.placements">{{ disc.placements }}</UiDisclaimer>

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
          <UiDisclaimer v-if="disc['chart-full']">{{ disc['chart-full'] }}</UiDisclaimer>
        </UiProOnly>

        <UiDisclaimer v-if="disc['chart-analysis']">{{ disc['chart-analysis'] }}</UiDisclaimer>
      </template>
    </template>
  </section>
</template>

<style scoped>
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
