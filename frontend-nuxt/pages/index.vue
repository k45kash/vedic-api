<script setup lang="ts">
import { toDMS } from '~/utils/format'

useHead({ title: 'Накшатра — Vedic' })

const form = useBirthForm()
const api = useApi()

const result = ref<any>(null)
const error = ref('')
const loading = ref(false)

const planetsByHouse = computed(() => {
  if (!result.value) return {} as Record<number, string[]>
  const m: Record<number, string[]> = {}
  result.value.planets
    .filter((p: any) => p.available)
    .forEach((p: any) => {
      if (!m[p.house]) m[p.house] = []
      m[p.house].push(`${p.abbr} ${p.name}`)
    })
  return m
})

const boundaryMsg = computed(() => {
  if (!result.value?.boundary) return ''
  const b = result.value.boundary
  if (b.is_boundary) return `⚠️ Луна на границе накшатры (${b.dist_arcsec?.toFixed(0)}")`
  if (b.dist_deg != null) {
    const pct = ((b.dist_deg / (360 / 27)) * 100).toFixed(1)
    return `Луна устойчиво в накшатре (${b.dist_deg.toFixed(3)}° = ${pct}% до границы)`
  }
  return ''
})

async function submit() {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await api.post('/api/horoscope', birthToPayload(form))
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1>Накшатра</h1>
    <p class="subtitle">Накшатра, лагна и положение планет по дате рождения</p>

    <BirthForm :form="form" :submitting="loading" @submit="submit" />

    <div class="result">
      <p v-if="loading" class="loading">Выполняется расчёт…</p>
      <p v-if="error" class="error">Ошибка: {{ error }}</p>

      <template v-if="result">
        <section>
          <div class="card">
            <h2>Луна</h2>
            <div class="grid">
              <div class="stat"><span class="stat-label">Julian Day</span><span class="stat-value">{{ result.jd?.toFixed(5) }}</span></div>
              <div class="stat"><span class="stat-label">Аянамша Лахири</span><span class="stat-value">{{ result.aya?.toFixed(4) }}°</span></div>
              <div class="stat"><span class="stat-label">Луна тропическая</span><span class="stat-value">{{ result.moon_trop != null ? result.moon_trop.toFixed(4) + '°' : '—' }}</span></div>
              <div class="stat"><span class="stat-label">Луна сидерическая</span><span class="stat-value">{{ result.moon_dms }}</span></div>
              <div class="stat"><span class="stat-label">Метод</span><span class="stat-value">{{ result.method ?? '—' }}</span></div>
            </div>
          </div>
        </section>

        <section>
          <div class="card">
            <h2>Накшатра Луны</h2>
            <div class="grid">
              <div class="stat"><span class="stat-label">Накшатра</span><span class="stat-value">#{{ result.nk.num }} {{ result.nk.name }} ({{ result.nk.ru }})</span></div>
              <div class="stat"><span class="stat-label">Пада</span><span class="stat-value">{{ result.nk.pada }} / 4</span></div>
              <div class="stat"><span class="stat-label">Владелец</span><span class="stat-value">{{ result.nk.lord }}</span></div>
              <div class="stat"><span class="stat-label">Символ</span><span class="stat-value">{{ result.nk.symbol ?? '—' }}</span></div>
              <div class="stat"><span class="stat-label">Гана</span><span class="stat-value">{{ result.nk.gana }}</span></div>
              <div class="stat"><span class="stat-label">Внутри накшатры</span><span class="stat-value">{{ result.nk.degrees_in_nakshatra != null ? toDMS(result.nk.degrees_in_nakshatra) : '—' }}</span></div>
            </div>
            <p v-if="boundaryMsg" class="boundary-msg">{{ boundaryMsg }}</p>
          </div>
        </section>

        <section>
          <div class="card">
            <h2>Лагна (Асцендент)</h2>
            <div class="grid">
              <div class="stat"><span class="stat-label">Лагна сидерическая</span><span class="stat-value">{{ result.lagna.asc_dms }}</span></div>
              <div class="stat"><span class="stat-label">Знак Лагны</span><span class="stat-value">#{{ result.lagna.sign_num }} {{ result.lagna.sign }} ({{ result.lagna.sign_ru }})</span></div>
              <div class="stat"><span class="stat-label">Владелец</span><span class="stat-value">{{ result.lagna.lord }}</span></div>
              <div class="stat"><span class="stat-label">Стихия</span><span class="stat-value">{{ result.lagna.element }}</span></div>
              <div class="stat"><span class="stat-label">Градусов в знаке</span><span class="stat-value">{{ result.lagna.deg_in_sign_dms ?? '—' }}</span></div>
            </div>
          </div>
        </section>

        <section>
          <div class="card">
            <h2>Планеты</h2>
            <table class="planets-table">
              <thead>
                <tr>
                  <th>Планета</th><th>Знак</th><th>°</th><th>Дом</th>
                  <th>Накшатра</th><th>Пада</th><th>Владелец накш.</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(p, i) in result.planets.filter((x: any) => x.available)" :key="i">
                  <td class="planet-name">{{ p.abbr ?? '' }} {{ p.name }}</td>
                  <td>{{ p.sign_ru }}</td>
                  <td>{{ p.deg_in_sign != null ? toDMS(p.deg_in_sign) : '—' }}</td>
                  <td>{{ p.house }}</td>
                  <td>{{ p.nakshatra_ru }}</td>
                  <td>{{ p.pada }}</td>
                  <td>{{ p.nk_lord ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <LagnaChart :horoscope="result" />

        <section>
          <div class="card">
            <h2>12 Домов (Whole Sign)</h2>
            <table class="planets-table">
              <thead>
                <tr><th>Дом</th><th>Знак</th><th>Владелец</th><th>Планеты</th><th>Значение</th></tr>
              </thead>
              <tbody>
                <tr v-for="h in result.lagna.houses ?? []" :key="h.house">
                  <td>{{ h.house }}</td>
                  <td>{{ h.sign_ru }}</td>
                  <td>{{ h.lord }}</td>
                  <td>{{ (planetsByHouse[h.house] ?? []).join(', ') || '—' }}</td>
                  <td class="house-meaning">{{ h.meaning ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<style>
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 20px; }
.stat { display: flex; flex-direction: column; gap: 4px; }
.stat-label { font-size: 11px; font-weight: 500; color: #a1a1a6; text-transform: uppercase; letter-spacing: 0.5px; }
.stat-value { font-size: 17px; font-weight: 500; color: #1d1d1f; }

.planets-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.planets-table th {
  text-align: left;
  font-size: 11px; font-weight: 500;
  color: #a1a1a6; text-transform: uppercase; letter-spacing: 0.5px;
  padding: 0 16px 12px 0;
}
.planets-table td { padding: 11px 16px 11px 0; border-top: 1px solid #f5f5f7; color: #1d1d1f; }
.planets-table tr:last-child td { border-bottom: 1px solid #f5f5f7; }
.planet-name { font-weight: 500; }

.boundary-msg {
  margin-top: 16px; font-size: 13px; color: #6e6e73;
  padding: 10px 14px; background: #f5f5f7; border-radius: 10px;
}
.house-meaning { color: #6e6e73; font-size: 13px; }
</style>
