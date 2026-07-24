<script setup lang="ts">
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
  <div>
    <h1>Календарь накшатр</h1>
    <p class="subtitle">Транзиты Луны по накшатрам за выбранный период</p>

    <form class="birth" @submit.prevent="submit">
      <div class="row">
        <div class="field">
          <label>Дата начала</label>
          <input type="date" v-model="form.date_start" required />
        </div>
        <div class="field">
          <label>Дата конца</label>
          <input type="date" v-model="form.date_end" required />
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
      <p v-if="loading" class="loading">Считаем транзиты Луны…</p>
      <p v-if="error" class="error">Ошибка: {{ error }}</p>

      <template v-if="result">
        <p v-if="!result.length" class="error">Нет данных</p>

        <div v-else class="nk-list">
          <template v-for="(nk, i) in result" :key="i">
            <div class="nk-row" @click="toggleRow(i)">
              <div>
                <div class="nk-name">#{{ nk.nk_num }} {{ nk.ru }}</div>
                <div class="nk-name-en">{{ nk.name }}</div>
              </div>
              <div class="nk-meta"><strong>{{ nk.lord }}</strong><br />Гана: {{ nk.gana }}</div>
              <div class="nk-meta">{{ fmt(nk.dt_start) }}</div>
              <div class="nk-meta">{{ fmt(nk.dt_end) }}</div>
              <div class="nk-duration">{{ nk.duration_h?.toFixed(1) }} ч</div>
            </div>
            <div
              v-if="nk.padas && nk.padas.length"
              class="nk-padas"
              :class="{ open: openRows.has(i) }"
            >
              <div v-for="(p, j) in nk.padas" :key="j" class="pada-row">
                <span class="pada-num">{{ p.pada }}</span>
                <span>{{ fmt(p.dt_start) }}</span>
                <span>{{ fmt(p.dt_end) }}</span>
                <span>{{ p.duration_h?.toFixed(1) }} ч</span>
              </div>
            </div>
          </template>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.nk-list { display: flex; flex-direction: column; gap: 2px; }

.nk-row {
  background: #fff;
  border-radius: 14px;
  padding: 16px 20px;
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr 1fr;
  align-items: center;
  gap: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  cursor: pointer;
  transition: box-shadow 0.15s;
}

.nk-row:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }

.nk-name { font-weight: 600; font-size: 15px; color: #1d1d1f; }
.nk-name-en { font-size: 12px; color: #a1a1a6; margin-top: 1px; }

.nk-meta { font-size: 13px; color: #6e6e73; }
.nk-meta strong { color: #1d1d1f; font-weight: 500; }

.nk-duration {
  font-size: 13px;
  color: #6e6e73;
  text-align: right;
}

.nk-padas {
  display: none;
  background: #f5f5f7;
  border-radius: 0 0 14px 14px;
  overflow: hidden;
  margin-top: -12px;
  padding: 4px 20px 12px;
}

.nk-padas.open { display: block; }

.pada-row {
  display: grid;
  grid-template-columns: 40px 1fr 1fr 1fr;
  font-size: 13px;
  padding: 8px 0;
  border-top: 1px solid #e8e8ed;
  color: #1d1d1f;
}
.pada-row:first-child { border-top: none; }
.pada-num { color: #a1a1a6; font-weight: 600; }
</style>
