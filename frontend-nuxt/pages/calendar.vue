<script setup lang="ts">
import type { PositionMode } from '~/composables/useBirthForm'
definePageMeta({ layout: 'app', middleware: 'auth' })
usePageHeader().setPageHeader({
  title: 'Календарь накшатр',
  subtitle: 'Транзиты Луны и пады за выбранный период',
})
useHead({ title: 'Календарь — Vedic' })

const api = useApi()

interface Pada {
  pada: number
  dt_start: string
  dt_end: string
  duration_h: number
}
interface Nakshatra {
  nk_num: number
  ru: string
  name: string
  lord: string
  gana: string
  dt_start: string
  dt_end: string
  duration_h: number
  padas?: Pada[]
}

const today = new Date()
const inTwoMonths = new Date(today.getTime() + 60 * 86400 * 1000)

const form = reactive({
  position_mode: 'apparent' as PositionMode,
  date_start: today.toISOString().slice(0, 10),
  date_end:   inTwoMonths.toISOString().slice(0, 10),
  lat: 45.0428,
  lon: 41.9734,
  tz: 3,
  city: 'Ставрополь',
})

const result = ref<Nakshatra[] | null>(null)
const error = ref('')
const loading = ref(false)

// Открытые строки (по индексу) — реактивно, без DOM-манипуляций.
const openRows = reactive(new Set<number>())

function toggleRow(i: number) {
  if (openRows.has(i)) openRows.delete(i)
  else openRows.add(i)
}

function fmt(dt: string): string {
  return dt ? dt.replace('T', ' ').slice(0, 16) : '—'
}

async function submit() {
  loading.value = true
  error.value = ''
  result.value = null
  openRows.clear()
  try {
    result.value = await api.post<Nakshatra[]>('/api/calendar', {
      position_mode: form.position_mode,
      date_start: form.date_start,
      date_end:   form.date_end,
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
  <div class="astro-tool">
    <UiCard title="Параметры расчёта">
      <form class="birth" @submit.prevent="submit">
        <div class="row">
          <div class="field">
            <label for="calendar-start">Дата начала</label>
            <input id="calendar-start" type="date" v-model="form.date_start" required />
          </div>
          <div class="field">
            <label for="calendar-end">Дата конца</label>
            <input id="calendar-end" type="date" v-model="form.date_end" required />
          </div>
        </div>
        <div class="row">
          <CityField
            v-model:city="form.city"
            v-model:lat="form.lat"
            v-model:lon="form.lon"
            v-model:tz="form.tz"
            :date="form.date_start"
          />
        </div>
        <div class="row">
          <div class="field">
            <label for="calendar-lat">Широта</label>
            <input id="calendar-lat" type="number" v-model.number="form.lat" step="0.0001" required />
          </div>
          <div class="field">
            <label for="calendar-lon">Долгота</label>
            <input id="calendar-lon" type="number" v-model.number="form.lon" step="0.0001" required />
          </div>
          <div class="field">
            <label for="calendar-tz">UTC ±, ч</label>
            <input id="calendar-tz" type="number" v-model.number="form.tz" step="any" required />
          </div>
        </div>
        <PositionModeField v-model="form.position_mode" :disabled="loading" />
        <button type="submit" class="primary" :disabled="loading">Рассчитать</button>
      </form>
    </UiCard>

    <div class="astro-result">
      <p v-if="loading" role="status">Считаем транзиты Луны…</p>
      <p v-if="error" class="astro-error" role="alert">{{ error }}</p>

      <template v-if="result">
        <p v-if="!result.length">Нет данных</p>

        <UiCard v-else title="Транзиты Луны" subtitle="Выберите накшатру, чтобы раскрыть её пады">
          <div class="nk-list">
            <template v-for="(nk, i) in result" :key="i">
              <button
                type="button"
                class="nk-row"
                :disabled="!nk.padas?.length"
                :aria-expanded="nk.padas?.length ? openRows.has(i) : undefined"
                @click="toggleRow(i)"
              >
                <span>
                  <strong class="nk-name">#{{ nk.nk_num }} {{ nk.ru }}</strong>
                  <span class="nk-name-en">{{ nk.name }}</span>
                </span>
                <span><strong>{{ nk.lord }}</strong><br />Гана · {{ nk.gana }}</span>
                <span><span class="nk-caption">Начало</span>{{ fmt(nk.dt_start) }}</span>
                <span><span class="nk-caption">Конец</span>{{ fmt(nk.dt_end) }}</span>
                <span>{{ nk.duration_h?.toFixed(1) }} ч <span v-if="nk.padas?.length" aria-hidden="true">{{ openRows.has(i) ? '▴' : '▾' }}</span></span>
              </button>
              <div
                v-if="nk.padas?.length && openRows.has(i)"
                class="nk-padas"
              >
                <div v-for="(p, j) in nk.padas" :key="j" class="pada-row">
                  <span class="pada-num">Пада {{ p.pada }}</span>
                  <span>{{ fmt(p.dt_start) }}</span>
                  <span>{{ fmt(p.dt_end) }}</span>
                  <span>{{ p.duration_h?.toFixed(1) }} ч</span>
                </div>
              </div>
            </template>
          </div>
        </UiCard>
      </template>
    </div>
  </div>
</template>

<style scoped>
.nk-list { display: grid; gap: 8px; }
.nk-row {
  display: grid;
  grid-template-columns: 1.35fr 1fr 1fr 1fr auto;
  gap: 8px 12px;
  align-items: center;
  width: 100%;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--surface-2);
  color: var(--body);
  text-align: left;
}
.astro-tool .nk-row { font-size: 13px; }
.nk-row:not(:disabled) { cursor: pointer; }
.nk-row:not(:disabled):hover { border-color: var(--accent); }
.nk-row[aria-expanded="true"] { background: var(--accent-soft); }
.nk-name { color: var(--ink); font-size: 15px; }
.nk-name-en, .nk-caption { display: block; font-size: 12px; }
.nk-padas { padding: 0 14px 8px; }
.pada-row {
  display: grid;
  grid-template-columns: .65fr 1fr 1fr auto;
  gap: 6px 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--line);
  color: var(--body);
  font-size: 13px;
}
.pada-num { color: var(--ink); font-weight: 600; }
@media (max-width: 720px) {
  .nk-row, .pada-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .nk-row > :last-child { grid-column: 1 / -1; }
  .pada-num { grid-column: 1 / -1; }
}
</style>
