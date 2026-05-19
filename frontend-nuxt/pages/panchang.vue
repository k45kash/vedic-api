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

async function submit() {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await api.post('/api/panchang', {
      date_start: form.date,
      date_end:   form.date,
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
    <p class="subtitle">
      Панчанга на день — хоры, мухурты и титхи.
      <em>(базовая версия — детальный UI с цветовыми качествами появится в следующем апдейте)</em>
    </p>

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
      <p v-if="loading" class="loading">Считаем панчанг…</p>
      <p v-if="error" class="error">Ошибка: {{ error }}</p>

      <template v-if="result">
        <section v-for="(day, di) in (result.days ?? [result])" :key="di">
          <h2>{{ day.date ?? form.date }}</h2>
          <div class="card">
            <pre class="raw">{{ JSON.stringify(day, null, 2) }}</pre>
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
</style>
