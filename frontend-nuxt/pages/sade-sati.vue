<script setup lang="ts">
useHead({ title: 'Сади Сати — Vedic' })

const form = useBirthForm()
const api = useApi()
const { fmtDate, fmtYears } = useFormatters()

const result = ref<any>(null)
const error = ref('')
const loading = ref(false)

const PHASE_RU: Record<string, string> = {
  Aarohini: 'Aarohini', Madhya: 'Madhya (пик)', Avarohini: 'Avarohini',
}
const PHASE_CLASS: Record<string, string> = {
  Aarohini: 'aarohini', Madhya: 'madhya', Avarohini: 'avarohini',
}
const PHASE_COLOR: Record<string, string> = {
  aarohini: '#f5a623', madhya: '#d0454c', avarohini: '#6cbf6c',
}

function segWidth(ep: any, total: number): number {
  if (!total) return 0
  const a = new Date(ep.dt_start).getTime()
  const b = new Date(ep.dt_end).getTime()
  return ((b - a) / total) * 100
}
function cycleTotal(c: any): number {
  const t0 = new Date(c.episodes[0].dt_start).getTime()
  const t1 = new Date(c.episodes[c.episodes.length - 1].dt_end).getTime()
  return t1 - t0
}

async function submit() {
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await api.post('/api/sade-sati', birthToPayload(form))
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h1>Сади Сати</h1>
    <p class="subtitle">
      Транзит Сатурна через три знака вокруг натальной Луны (~7,5 лет).
      Параллельно — Аштама и Кантака Шани.
    </p>

    <BirthForm :form="form" :submitting="loading" @submit="submit" />

    <div class="result">
      <p v-if="loading" class="loading">Считаем 120 лет транзитов Сатурна…</p>
      <p v-if="error" class="error">Ошибка: {{ error }}</p>

      <template v-if="result">
        <!-- Натальная Луна -->
        <section>
          <h2>Натальная Луна</h2>
          <div class="card">
            <div class="ss-stats">
              <div class="ss-stat">
                <div class="ss-stat-lbl">Знак (раши)</div>
                <div class="ss-stat-val">{{ result.natal_moon.sign_ru }} ({{ result.natal_moon.sign }})</div>
              </div>
              <div class="ss-stat">
                <div class="ss-stat-lbl">Градус в знаке</div>
                <div class="ss-stat-val">{{ result.natal_moon.deg_in_sign_dms }}</div>
              </div>
              <div class="ss-stat">
                <div class="ss-stat-lbl">Накшатра</div>
                <div class="ss-stat-val">{{ result.natal_moon.nakshatra_ru }} · пада {{ result.natal_moon.pada }}</div>
              </div>
              <div class="ss-stat">
                <div class="ss-stat-lbl">Управитель</div>
                <div class="ss-stat-val">{{ result.natal_moon.nk_lord }}</div>
              </div>
              <div class="ss-stat">
                <div class="ss-stat-lbl">Фрейм</div>
                <div class="ss-stat-val">{{ result.natal_moon.frame === 'topocentric' ? 'топоцентрический' : 'геоцентрический' }}</div>
              </div>
            </div>
            <div v-if="result.natal_moon.boundary?.topo_applied" class="ss-warn">
              Луна в {{ result.natal_moon.boundary.dist_to_boundary_deg }}° от границы знака — применён топоцентрический расчёт
              (поправка {{ result.natal_moon.boundary.delta_arcsec }}″).
              <b v-if="result.natal_moon.boundary.sign_changed_by_topo">Знак изменился относительно геоцентрического!</b>
              <span v-else>Знак не изменился.</span>
            </div>
            <div v-else-if="result.natal_moon.boundary?.near_boundary" class="ss-warn">
              Луна в {{ result.natal_moon.boundary.dist_to_boundary_deg }}° от границы знака.
            </div>
          </div>
        </section>

        <!-- Сейчас -->
        <section>
          <h2>Сейчас</h2>
          <div class="card">
            <template v-if="!result.current.sade_sati && !result.current.ashtama_shani && !result.current.kantaka_shani">
              <div style="color: #6e6e73">Сейчас ни один период не активен.</div>
            </template>

            <template v-else>
              <div
                v-if="result.current.sade_sati"
                class="ss-now"
                :style="{ borderColor: PHASE_COLOR[PHASE_CLASS[result.current.sade_sati.phase] || 'madhya'] }"
              >
                <span
                  class="ss-phase-tag"
                  :style="{
                    background: PHASE_COLOR[PHASE_CLASS[result.current.sade_sati.phase] || 'madhya'],
                    color: PHASE_CLASS[result.current.sade_sati.phase] === 'madhya' ? '#fff' : '#1a1310',
                  }"
                >
                  САДИ САТИ · {{ PHASE_RU[result.current.sade_sati.phase] }}
                  <span v-if="result.current.sade_sati.is_retrograde_return" class="ss-retro" title="Ретроградный возврат">↺</span>
                </span>
                <div style="margin-top: 10px; font-size: 16px">
                  Сатурн в знаке <b>{{ result.current.sade_sati.sign_ru }}</b>
                  <span v-if="result.current.sade_sati.is_retrograde_return" style="color: #6e6e73; font-size: 13px">
                    (возврат после ретроградности)
                  </span>
                </div>
                <div class="ss-now-meta">
                  {{ fmtDate(result.current.sade_sati.dt_start) }} → {{ fmtDate(result.current.sade_sati.dt_end) }}
                  · осталось {{ fmtYears(result.current.sade_sati.days_remaining) }}
                </div>
                <div class="ss-progress">
                  <div
                    class="ss-progress-fill"
                    :style="{
                      width: (result.current.sade_sati.progress * 100) + '%',
                      background: PHASE_COLOR[PHASE_CLASS[result.current.sade_sati.phase] || 'madhya'],
                    }"
                  />
                </div>
              </div>

              <div v-if="result.current.ashtama_shani" class="ss-now" style="border-color: #7d6cbf">
                <span class="ss-phase-tag" style="background: #7d6cbf; color: #fff">АШТАМА ШАНИ</span>
                <div style="margin-top: 8px">
                  Сатурн в {{ result.current.ashtama_shani.sign_ru }} · осталось {{ fmtYears(result.current.ashtama_shani.days_remaining) }}
                </div>
              </div>

              <div v-if="result.current.kantaka_shani" class="ss-now" style="border-color: #4a90e2">
                <span class="ss-phase-tag" style="background: #4a90e2; color: #fff">КАНТАКА ШАНИ</span>
                <div style="margin-top: 8px">
                  Сатурн в {{ result.current.kantaka_shani.sign_ru }} · осталось {{ fmtYears(result.current.kantaka_shani.days_remaining) }}
                </div>
              </div>
            </template>
          </div>
        </section>

        <!-- Циклы -->
        <section v-if="result.sade_sati_cycles.length">
          <h2>Циклы Сади Сати</h2>
          <div class="card">
            <div v-for="(c, i) in result.sade_sati_cycles" :key="i" class="ss-cycle">
              <div class="ss-cycle-head">
                <div class="ss-cycle-title">Цикл #{{ i + 1 }}</div>
                <div class="ss-cycle-meta">
                  {{ fmtDate(c.dt_start) }} → {{ fmtDate(c.dt_end) }} · {{ c.duration_years }} лет
                  <template v-if="c.truncated_start"> · начало до даты рождения</template>
                  <template v-if="c.truncated_end"> · конец вне окна поиска</template>
                </div>
              </div>
              <div class="ss-timeline">
                <div
                  v-for="(ep, j) in c.episodes"
                  :key="j"
                  class="ss-seg"
                  :class="`ss-seg-${PHASE_CLASS[ep.phase]}`"
                  :style="{ width: segWidth(ep, cycleTotal(c)) + '%' }"
                  :title="`${ep.phase} · ${ep.sign_ru} · ${fmtDate(ep.dt_start)} → ${fmtDate(ep.dt_end)}`"
                >
                  <template v-if="segWidth(ep, cycleTotal(c)) > 8">{{ ep.phase }}</template>
                </div>
              </div>
              <div class="ss-eps">
                <div v-for="(ep, j) in c.episodes" :key="j" class="ss-ep-row">
                  <span class="ss-ep-tag" :class="`ss-tag-${PHASE_CLASS[ep.phase]}`">
                    {{ ep.phase }}
                    <span v-if="ep.is_retrograde_return" class="ss-retro" title="Ретроградный возврат">↺</span>
                  </span>
                  <span>{{ ep.sign_ru }} · {{ fmtDate(ep.dt_start) }} → {{ fmtDate(ep.dt_end) }}</span>
                  <span>{{ Math.round(ep.duration_days) }} дн</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Аштама/Кантака -->
        <section v-if="result.ashtama_shani_periods.length">
          <h2>Аштама Шани · знак {{ result.ashtama_sign.sign_ru }}</h2>
          <div class="card">
            <div class="ss-shani">
              <div
                v-for="(ep, i) in result.ashtama_shani_periods"
                :key="i"
                class="ss-shani-row"
                :class="{ current: result.current.ashtama_shani && ep.dt_start === result.current.ashtama_shani.dt_start }"
              >
                <div>
                  {{ fmtDate(ep.dt_start) }} → {{ fmtDate(ep.dt_end) }}
                  <span v-if="result.current.ashtama_shani && ep.dt_start === result.current.ashtama_shani.dt_start" class="ss-badge">сейчас</span>
                </div>
                <div class="when">{{ Math.round(ep.duration_days) }} дн</div>
              </div>
            </div>
          </div>
        </section>

        <section v-if="result.kantaka_shani_periods.length">
          <h2>Кантака Шани · знак {{ result.kantaka_sign.sign_ru }}</h2>
          <div class="card">
            <div class="ss-shani">
              <div
                v-for="(ep, i) in result.kantaka_shani_periods"
                :key="i"
                class="ss-shani-row"
                :class="{ current: result.current.kantaka_shani && ep.dt_start === result.current.kantaka_shani.dt_start }"
              >
                <div>
                  {{ fmtDate(ep.dt_start) }} → {{ fmtDate(ep.dt_end) }}
                  <span v-if="result.current.kantaka_shani && ep.dt_start === result.current.kantaka_shani.dt_start" class="ss-badge">сейчас</span>
                </div>
                <div class="when">{{ Math.round(ep.duration_days) }} дн</div>
              </div>
            </div>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>

<style>
.ss-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; }
.ss-stat  { background: #f5f5f7; padding: 12px 14px; border-radius: 12px; }
.ss-stat-lbl { font-size: 11px; color: #6e6e73; text-transform: uppercase; letter-spacing: 0.05em; }
.ss-stat-val { font-size: 15px; margin-top: 4px; color: #1d1d1f; font-weight: 500; }

.ss-warn {
  margin-top: 12px;
  padding: 10px 14px;
  background: rgba(255, 184, 0, 0.1);
  border: 1px solid rgba(255, 184, 0, 0.3);
  border-radius: 10px;
  font-size: 13px;
  color: #715200;
}

.ss-now { padding: 16px 20px; border-radius: 14px; border-left: 4px solid #d0454c; background: #f5f5f7; }
.ss-now + .ss-now { margin-top: 12px; }
.ss-phase-tag {
  display: inline-block;
  padding: 3px 10px;
  border-radius: 20px;
  font-size: 11px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.05em;
}
.ss-now-meta { font-size: 13px; color: #6e6e73; margin-top: 4px; }
.ss-progress { margin-top: 10px; height: 6px; background: rgba(0,0,0,0.06); border-radius: 3px; overflow: hidden; }
.ss-progress-fill { height: 100%; }

.ss-cycle { margin-bottom: 24px; }
.ss-cycle:last-child { margin-bottom: 0; }
.ss-cycle-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; flex-wrap: wrap; gap: 6px; }
.ss-cycle-title { font-weight: 600; font-size: 15px; }
.ss-cycle-meta  { color: #6e6e73; font-size: 13px; }

.ss-timeline { display: flex; height: 38px; border-radius: 10px; overflow: hidden; }
.ss-seg { display: flex; align-items: center; justify-content: center; font-size: 11px; color: rgba(0,0,0,0.75); font-weight: 600; overflow: hidden; white-space: nowrap; }
.ss-seg-aarohini  { background: #f5a623; }
.ss-seg-madhya    { background: #d0454c; color: #fff; }
.ss-seg-avarohini { background: #6cbf6c; }

.ss-eps { margin-top: 10px; font-size: 13px; color: #6e6e73; }
.ss-ep-row { display: grid; grid-template-columns: 120px 1fr auto; gap: 12px; padding: 6px 0; align-items: center; }
.ss-ep-tag { display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: 11px; font-weight: 600; color: #1a1310; }
.ss-tag-aarohini  { background: #f5a623; }
.ss-tag-madhya    { background: #d0454c; color: #fff; }
.ss-tag-avarohini { background: #6cbf6c; }
.ss-retro { display: inline-block; margin-left: 3px; font-weight: 700; cursor: help; opacity: 0.85; }

.ss-shani { display: grid; gap: 8px; }
.ss-shani-row { display: grid; grid-template-columns: 1fr auto; padding: 10px 14px; background: #f5f5f7; border-radius: 10px; font-size: 13px; }
.ss-shani-row.current { border-left: 3px solid #0071e3; background: rgba(0, 113, 227, 0.06); }
.ss-shani-row .when { color: #6e6e73; }
.ss-badge { display: inline-block; padding: 2px 8px; background: #0071e3; color: #fff; border-radius: 20px; font-size: 11px; font-weight: 600; margin-left: 8px; }
</style>
