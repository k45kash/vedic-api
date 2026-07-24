<script setup lang="ts">
useHead({ title: 'Панчанг — Vedic' })

const api = useApi()

const form = reactive({
  date: new Date().toISOString().slice(0, 10),
  lat: 45.0428,
  lon: 41.9734,
  tz: 3,
  city: 'Ставрополь',
})

const result = ref<any>(null)
const error = ref('')
const loading = ref(false)

// ── Цветовые палитры ──────────────────────────────────────────
const PLANET_COLORS: Record<string, [string, string]> = {
  'Солнце':   ['#FFD060', '#1d1d1f'],
  'Луна':     ['#87CEEB', '#1d1d1f'],
  'Марс':     ['#FF7F7F', '#fff'],
  'Меркурий': ['#90C97A', '#1d1d1f'],
  'Юпитер':   ['#C8A8E0', '#1d1d1f'],
  'Венера':   ['#FFB6C1', '#1d1d1f'],
  'Сатурн':   ['#9B9BC4', '#fff'],
  'Раху':     ['#B0B0B0', '#fff'],
  'Кету':     ['#C8A882', '#1d1d1f'],
}

// Порядок важен: сначала более специфичные ("очень …")
const QUALITY_COLORS: [string, string, string][] = [
  ['очень неблагоприятная', '#FF6B00', '#fff'],
  ['очень благоприятная',   '#34C759', '#fff'],
  ['неблагоприятная',       '#FF9500', '#fff'],
  ['благоприятная',         '#A8E6B4', '#1d1d1f'],
  ['переменная',            '#FFD54F', '#1d1d1f'],
]

const TITHI_COLORS: Record<string, [string, string]> = {
  'очень благоприятная': ['#A5D6A7', '#1d1d1f'],
  'благоприятная':       ['#C8E6C9', '#1d1d1f'],
  'переменная':          ['#FFF9C4', '#1d1d1f'],
  'неблагоприятная':     ['#FFCDD2', '#1d1d1f'],
}

function qualityColor(q: string): [string, string] {
  const key = q?.toLowerCase() ?? ''
  for (const [k, bg, fg] of QUALITY_COLORS) if (key.includes(k)) return [bg, fg]
  return ['#e0e0e0', '#1d1d1f']
}
function tithiColor(q: string): [string, string] {
  const key = q?.toLowerCase() ?? ''
  for (const [k, v] of Object.entries(TITHI_COLORS)) if (key.includes(k)) return v
  return ['#E1F5FE', '#1d1d1f']
}

// ── Утилиты времени ──────────────────────────────────────────
function toMin(dt: string): number {
  if (!dt) return 0
  const t = dt.includes('T') ? dt.split('T')[1] : dt.split(' ')[1]
  if (!t) return 0
  const [h, m] = t.split(':').map(Number)
  return h * 60 + m
}

function duration(dtStart: string, dtEnd: string): string {
  const parse = (dt: string) => {
    const sep = dt.includes('T') ? 'T' : ' '
    const [d, t] = dt.split(sep)
    const [yr, mo, dy] = d.split('-').map(Number)
    const [h, m, s] = t.split(':').map(Number)
    return Date.UTC(yr, mo - 1, dy, h, m, s || 0) / 1000
  }
  const diff = Math.abs(parse(dtEnd) - parse(dtStart))
  const totalMin = Math.floor(diff / 60)
  const s = diff % 60
  if (totalMin >= 60) {
    const h = Math.floor(totalMin / 60)
    const m = totalMin % 60
    return m === 0 ? `${h}ч` : `${h}ч ${m}мин`
  }
  return s > 0 ? `${totalMin}мин ${s}сек` : `${totalMin}мин`
}

function hhmm(dt?: string): string {
  return dt ? dt.slice(11, 16) : '—'
}

// ── Модель одного блока на треке ─────────────────────────────
interface Block {
  left: number      // %
  width: number     // %
  label: string
  bg: string
  fg: string
  tip?: string
}

// Один блок (обрезка по 0..1440 мин)
function mkBlock(startMin: number, endMin: number, label: string, bg: string, fg: string, tip = ''): Block | null {
  const s = Math.max(0, startMin)
  const e = Math.min(1440, endMin)
  if (e <= s) return null
  return { left: s / 1440 * 100, width: (e - s) / 1440 * 100, label, bg, fg, tip }
}

// Блок с переносом через полночь → возможно два блока
function mkBlockWrap(startMin: number, endMin: number, label: string, bg: string, fg: string, tip = ''): Block[] {
  const out: Block[] = []
  if (endMin > 1440) {
    const a = mkBlock(startMin, 1440, label, bg, fg, tip)
    const b = mkBlock(0, endMin - 1440, label, bg, fg, tip)
    if (a) out.push(a)
    if (b) out.push(b)
  } else {
    const a = mkBlock(startMin, endMin, label, bg, fg, tip)
    if (a) out.push(a)
  }
  return out
}

const HOURS = Array.from({ length: 13 }, (_, i) => i * 2) // 0..24 шаг 2

// ── Собранные ряды таймлайна ─────────────────────────────────
interface Panchang {
  date: string
  sunrise: string
  sunset: string
  dayDur: number
  nowPct: number | null
  dayNight: Block[]
  tithi: Block[]
  muhurta: Block[]
  hora: Block[]
  legend: { planet: string; bg: string }[]
}

const panchang = computed<Panchang | null>(() => {
  if (!result.value) return null
  const day = result.value.days?.[1]
  if (!day) return null
  const date = form.date

  const sunriseMin = toMin(day.dt_sunrise)
  const sunsetMin = toMin(day.dt_sunset)

  // Линия текущего времени (только если запрошен сегодняшний день)
  let nowPct: number | null = null
  const today = new Date().toISOString().slice(0, 10)
  if (date === today) {
    const now = new Date()
    nowPct = (now.getHours() * 60 + now.getMinutes()) / 1440 * 100
  }

  // День/Ночь
  const dayNight: Block[] = []
  const nightBefore = mkBlock(0, sunriseMin, 'Ночь', '#d0d8f0', '#4a5080')
  const dayBlock = mkBlock(sunriseMin, sunsetMin, `Восход ${hhmm(day.dt_sunrise)} · Закат ${hhmm(day.dt_sunset)}`, '#FFF9E6', '#8a6500')
  const nightAfter = mkBlock(sunsetMin, 1440, 'Ночь', '#d0d8f0', '#4a5080')
  for (const b of [nightBefore, dayBlock, nightAfter]) if (b) dayNight.push(b)

  // Титхи — только перекрывающиеся с текущим днём
  const tithi: Block[] = []
  for (const t of result.value.tithis ?? []) {
    if (!(t.dt_start.slice(0, 10) <= date && t.dt_end.slice(0, 10) >= date)) continue
    const s = t.dt_start.slice(0, 10) < date ? 0 : toMin(t.dt_start)
    const eRaw = t.dt_end.slice(0, 10) > date ? 1440 : toMin(t.dt_end)
    const e = eRaw < s ? eRaw + 1440 : eRaw
    const [bg, fg] = tithiColor(t.quality)
    const fmt = (dt: string) => (dt ? dt.slice(0, 16).replace('T', ' ') : '—')
    const tip = `${fmt(t.dt_start)} – ${fmt(t.dt_end)}  (${duration(t.dt_start, t.dt_end)})\n${t.quality}`
    const b = mkBlock(s, e, t.name, bg, fg, tip)
    if (b) tithi.push(b)
  }

  // Мухурты
  const muhurta: Block[] = []
  ;(day.muhurtas ?? []).forEach((m: any, i: number) => {
    const s = toMin(m.dt_start)
    const eRaw = toMin(m.dt_end)
    const e = eRaw < s ? eRaw + 1440 : eRaw
    const [bg, fg] = qualityColor(m.quality)
    const tip = `${m.name}\n${hhmm(m.dt_start)} – ${hhmm(m.dt_end)}  (${duration(m.dt_start, m.dt_end)})\n${m.quality}`
    muhurta.push(...mkBlockWrap(s, e, String(m.num ?? i + 1), bg, fg, tip))
  })

  // Хоры
  const hora: Block[] = []
  for (const h of day.horas ?? []) {
    const [bg, fg] = PLANET_COLORS[h.planet] ?? ['#e0e0e0', '#1d1d1f']
    const s = toMin(h.dt_start)
    const eRaw = toMin(h.dt_end)
    const e = eRaw < s ? eRaw + 1440 : eRaw
    const tip = `${h.planet}\n${hhmm(h.dt_start)} – ${hhmm(h.dt_end)}\n${h.day_night}`
    hora.push(...mkBlockWrap(s, e, h.planet.slice(0, 2), bg, fg, tip))
  }

  // Легенда планет
  const planetsUsed = [...new Set((day.horas ?? []).map((h: any) => h.planet))] as string[]
  const legend = planetsUsed.map(p => ({ planet: p, bg: (PLANET_COLORS[p] ?? ['#e0e0e0'])[0] }))

  return {
    date,
    sunrise: hhmm(day.dt_sunrise),
    sunset: hhmm(day.dt_sunset),
    dayDur: day.day_dur_h,
    nowPct,
    dayNight,
    tithi,
    muhurta,
    hora,
    legend,
  }
})

function prevDay(date: string): string {
  const d = new Date(date); d.setDate(d.getDate() - 1); return d.toISOString().slice(0, 10)
}
function nextDay(date: string): string {
  const d = new Date(date); d.setDate(d.getDate() + 1); return d.toISOString().slice(0, 10)
}

async function submit() {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    // Запрашиваем вчера/сегодня/завтра — day[1] это выбранный день,
    // соседние нужны для титхи/хор, переходящих через полночь.
    result.value = await api.post('/api/panchang', {
      date_start: prevDay(form.date),
      date_end:   nextDay(form.date),
      tz:         form.tz,
      lat:        form.lat,
      lon:        form.lon,
    })
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1>Панчанг</h1>
    <p class="subtitle">Панчанга на день — хоры, мухурты и титхи</p>

    <form class="birth" @submit.prevent="submit">
      <div class="row">
        <div class="field">
          <label>Дата</label>
          <input type="date" v-model="form.date" required />
        </div>
      </div>
      <div class="row">
        <CityField
          v-model:city="form.city"
          v-model:lat="form.lat"
          v-model:lon="form.lon"
          v-model:tz="form.tz"
          :date="form.date"
        />
      </div>
      <div class="row">
        <div class="field">
          <label>Широта</label>
          <input type="number" v-model.number="form.lat" step="0.0001" required />
        </div>
        <div class="field">
          <label>Долгота</label>
          <input type="number" v-model.number="form.lon" step="0.0001" required />
        </div>
        <div class="field">
          <label>UTC ±, ч</label>
          <input type="number" v-model.number="form.tz" step="0.5" required />
        </div>
      </div>
      <button type="submit" class="primary" :disabled="loading">Рассчитать</button>
    </form>

    <div class="result">
      <p v-if="loading" class="loading">Выполняется расчёт…</p>
      <p v-if="error" class="error">Ошибка: {{ error }}</p>

      <div v-if="panchang" class="panchang-card">
        <div class="panchang-header">
          <span class="panchang-title">{{ panchang.date }}</span>
        </div>
        <div class="panchang-meta">
          Восход {{ panchang.sunrise }} · Закат {{ panchang.sunset }} · Длина дня {{ panchang.dayDur?.toFixed(1) }} ч
        </div>

        <div class="tl-wrap">
          <div class="tl-inner">
            <!-- Шкала часов -->
            <div class="tl-axis">
              <span
                v-for="h in HOURS"
                :key="h"
                class="tl-hour"
                :style="{ left: (h / 24 * 100) + '%' }"
              >{{ h }}</span>
            </div>

            <!-- День/Ночь -->
            <div class="tl-row">
              <span class="tl-row-label">День/Ночь</span>
              <div class="tl-track">
                <div
                  v-for="(b, i) in panchang.dayNight"
                  :key="i"
                  class="tl-block"
                  :style="{ left: b.left + '%', width: b.width + '%', background: b.bg }"
                  :data-tip="b.tip || undefined"
                >
                  <span class="tl-block-text" :style="{ color: b.fg }">{{ b.label }}</span>
                </div>
                <div v-if="panchang.nowPct != null" class="tl-now" :style="{ left: panchang.nowPct + '%' }" />
              </div>
            </div>

            <div class="tl-section-gap" />

            <!-- Титхи -->
            <div class="tl-row">
              <span class="tl-row-label">Титхи</span>
              <div class="tl-track">
                <div
                  v-for="(b, i) in panchang.tithi"
                  :key="i"
                  class="tl-block"
                  :style="{ left: b.left + '%', width: b.width + '%', background: b.bg }"
                  :data-tip="b.tip || undefined"
                >
                  <span class="tl-block-text" :style="{ color: b.fg }">{{ b.label }}</span>
                </div>
              </div>
            </div>

            <div class="tl-section-gap" />

            <!-- Мухурты -->
            <div class="tl-row">
              <span class="tl-row-label">Мухурты</span>
              <div class="tl-track">
                <div
                  v-for="(b, i) in panchang.muhurta"
                  :key="i"
                  class="tl-block"
                  :style="{ left: b.left + '%', width: b.width + '%', background: b.bg }"
                  :data-tip="b.tip || undefined"
                >
                  <span class="tl-block-text" :style="{ color: b.fg }">{{ b.label }}</span>
                </div>
              </div>
            </div>

            <div class="tl-section-gap" />

            <!-- Хоры -->
            <div class="tl-row">
              <span class="tl-row-label">Хоры</span>
              <div class="tl-track">
                <div
                  v-for="(b, i) in panchang.hora"
                  :key="i"
                  class="tl-block"
                  :style="{ left: b.left + '%', width: b.width + '%', background: b.bg }"
                  :data-tip="b.tip || undefined"
                >
                  <span class="tl-block-text" :style="{ color: b.fg }">{{ b.label }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="tl-legend">
          <div v-for="l in panchang.legend" :key="l.planet" class="tl-legend-item">
            <div class="tl-legend-dot" :style="{ background: l.bg }" />{{ l.planet }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.panchang-card {
  background: #fff;
  border-radius: 18px;
  padding: 24px 24px 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  margin-bottom: 16px;
}
.panchang-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px; }
.panchang-title { font-size: 17px; font-weight: 600; color: #1d1d1f; }
.panchang-meta { font-size: 13px; color: #6e6e73; margin-bottom: 20px; }

.tl-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.tl-inner { min-width: 700px; }

.tl-axis { display: flex; margin-left: 80px; margin-bottom: 4px; position: relative; height: 16px; }
.tl-hour { position: absolute; font-size: 10px; color: #a1a1a6; transform: translateX(-50%); }

.tl-row { display: flex; align-items: stretch; margin-bottom: 3px; height: 32px; }
.tl-row-label {
  width: 80px; min-width: 80px;
  font-size: 11px; font-weight: 500; color: #6e6e73;
  display: flex; align-items: center; padding-right: 8px;
}
.tl-track { flex: 1; position: relative; background: #f5f5f7; border-radius: 6px; overflow: visible; }

.tl-block {
  position: absolute; top: 0; height: 100%;
  border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  padding: 0 4px; overflow: hidden; cursor: default;
  transition: filter 0.1s; box-sizing: border-box;
}
.tl-block:hover { filter: brightness(0.93); }
.tl-block-text {
  font-size: 11px; font-weight: 600;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  pointer-events: none;
}

.tl-block[data-tip] { overflow: visible; }
.tl-block[data-tip]:hover::after {
  content: attr(data-tip);
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%);
  background: #1d1d1f; color: #fff;
  font-size: 12px; font-weight: 400; line-height: 1.5;
  white-space: pre;
  padding: 8px 12px; border-radius: 10px;
  pointer-events: none; z-index: 200;
  box-shadow: 0 4px 16px rgba(0,0,0,0.2);
}

.tl-now { position: absolute; top: 0; width: 2px; height: 100%; background: #0071e3; z-index: 10; pointer-events: none; }
.tl-section-gap { height: 8px; }

.tl-legend { display: flex; flex-wrap: wrap; gap: 8px 16px; margin-top: 16px; padding-top: 16px; border-top: 1px solid #f5f5f7; }
.tl-legend-item { display: flex; align-items: center; gap: 5px; font-size: 11px; color: #6e6e73; }
.tl-legend-dot { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }
</style>
