<script setup lang="ts">
useHead({ title: 'Календарь — Vedic' })

const api = useApi()

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

const result = ref<any>(null)
const error = ref('')
const loading = ref(false)

async function submit() {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await api.post('/api/calendar', {
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

const transits = computed(() => result.value?.transits ?? result.value?.events ?? [])
</script>

<template>
  <div>
    <h1>Календарь накшатр</h1>
    <p class="subtitle">
      Транзиты Луны по накшатрам за выбранный период.
      <em>(базовая версия — детальный UI появится в следующем апдейте)</em>
    </p>

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
        <section v-if="transits.length">
          <h2>Транзиты ({{ transits.length }})</h2>
          <div class="card">
            <table class="planets-table">
              <thead>
                <tr><th>Время</th><th>Накшатра</th><th>Подробности</th></tr>
              </thead>
              <tbody>
                <tr v-for="(t, i) in transits" :key="i">
                  <td>{{ t.dt ?? t.date ?? t.time ?? '—' }}</td>
                  <td>{{ t.nakshatra_ru ?? t.nakshatra ?? '—' }}</td>
                  <td>{{ t.note ?? t.description ?? '' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
        <section v-else>
          <h2>Ответ API</h2>
          <div class="card">
            <pre class="raw">{{ JSON.stringify(result, null, 2) }}</pre>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<style scoped>
.raw {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 12px;
  color: #444;
  background: #f5f5f7;
  padding: 12px;
  border-radius: 10px;
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-word;
}
.planets-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.planets-table th { text-align: left; font-size: 11px; font-weight: 500; color: #a1a1a6; text-transform: uppercase; padding: 0 16px 12px 0; }
.planets-table td { padding: 11px 16px 11px 0; border-top: 1px solid #f5f5f7; }
</style>
