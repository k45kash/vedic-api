<script setup lang="ts">
import type { PositionMode } from '~/composables/useBirthForm'
import reference from '~content/panchanga.json'
import tithis from '~content/tithi.json'

useHead({ title: 'Панчанга на день · Vedic' })
const api = useApi()
type Interval = {
  dt_start: string; dt_end: string; name?: string; planet?: string; num?: number
  type?: string; quality?: string; lord?: string; paksha?: string; sunset?: string
  is_bhadra?: boolean; is_stop?: boolean; day_night?: string
}
type Timeline = { rows: Record<string, Interval[]>; warnings: string[] }
const place = reactive({ city: 'Ставрополь', lat: 45.0428, lon: 41.9734, tz: 3 })
const mode = ref<PositionMode>('apparent')
const settings = ref(false)
const monthOpen = ref(false)
const localNow = () => new Date(Date.now() + place.tz * 3600000).toISOString()
const requested = useRoute().query
const requestedDate = String(requested.date ?? '')
const requestedTime = String(requested.time ?? '')
const parsedDate = new Date(requestedDate + 'T00:00:00Z')
const day = ref(Number.isFinite(parsedDate.getTime()) && parsedDate.toISOString().slice(0,10) === requestedDate
  ? requestedDate : localNow().slice(0,10))
const clock = ref(/^([01]\d|2[0-3]):[0-5]\d$/.test(requestedTime) ? requestedTime : localNow().slice(11,16))
const month = ref(day.value.slice(0, 7))
const timeline = ref<Timeline | null>(null)
const chart = ref<any>(null)
const dayError = ref(''), chartError = ref('')
const query = computed(() => ({ day: day.value, lat: place.lat, lon: place.lon, tz: place.tz, position_mode: mode.value }))
watch(query, async (q, _, cleanup) => {
  let live = true
  cleanup(() => { live = false })
  timeline.value = null
  dayError.value = ''
  try {
    const data = await api.post<Timeline>('/api/panchang/day', q)
    if (live) timeline.value = data
  } catch (e) { if (live) dayError.value = String(e) }
}, { immediate: true })
watch([query, clock], async ([q, time], _, cleanup) => {
  let live = true
  cleanup(() => { live = false })
  chart.value = null
  chartError.value = ''
  if (!time) return
  const [year, month, d] = q.day.split('-').map(Number)
  const [hour, minute] = time.split(':').map(Number)
  try {
    const result = await api.post('/api/horoscope', { ...q, year, month, day: d, hour, minute })
    if (live) chart.value = result
  } catch (e) { if (live) chartError.value = String(e) }
}, { immediate: true })

const dateMs = computed(() => Date.parse(day.value + 'T00:00Z'))
const minute = computed(() => Number(clock.value.slice(0, 2)) * 60 + Number(clock.value.slice(3, 5)))
const instant = computed(() => dateMs.value + minute.value * 60000)
// API возвращает местные метки. UTC здесь служит числовой шкалой без зоны браузера.
const ms = (stamp: string) => Date.parse(stamp + 'Z')
const hhmm = (stamp: string) => stamp.slice(11, 16)
const full = (stamp: string) => stamp.slice(8,10) + '.' + stamp.slice(5,7) + ' ' + hhmm(stamp)
function selectMinute(n: number) {
  n = Math.max(0, Math.min(1439, Math.floor(n)))
  clock.value = [Math.floor(n / 60), n % 60].map(v => String(v).padStart(2,'0')).join(':')
}
function pick(e: MouseEvent) {
  const box = (e.currentTarget as HTMLElement).getBoundingClientRect()
  selectMinute((e.clientX - box.left) / box.width * 1440)
}
function shift(n: number) { day.value = new Date(dateMs.value + n * 86400000).toISOString().slice(0,10) }
function today() { const now = localNow(); day.value = now.slice(0,10); clock.value = now.slice(11,16) }
function openMonth() { month.value = day.value.slice(0,7); monthOpen.value = !monthOpen.value }
const monthDays = computed(() => {
  if (!month.value) return []
  const first = new Date(month.value + '-01T00:00Z')
  const last = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth()+1, 0)).getUTCDate()
  return [...Array((first.getUTCDay()+6)%7).fill(''), ...Array.from({length:last}, (_,i) => month.value+'-'+String(i+1).padStart(2,'0'))]
})
const tracks = [
  ['light','День и ночь'],['rahu','Раху-кала'],['abhijit','Абхиджит'],['vara','Вара'],
  ['tithi','Титхи'],['lagna','Восходящий знак'],['moon','Знак Луны'],['nakshatra','Накшатра'],
  ['karana','Карана'],['yoga','Йога'],['muhurta','Мухурты'],['yama','Ямы'],['hora','Хоры'],
]
const palette = ['#d6e7e1','#ffe3ab','#d6e3f4','#eadbf1','#f6ceca','#c9e6ea','#e6dcbe']
function label(row: Interval) { return row.name || row.planet || '' }
function block(row: Interval, key: string, i: number) {
  const lo = Math.max(0, (ms(row.dt_start)-dateMs.value)/86400000)
  const hi = Math.min(1, (ms(row.dt_end)-dateMs.value)/86400000)
  const background = key === 'light' ? (row.name === 'Ночь' ? '#ced3e3' : '#fff0ca')
    : key === 'rahu' ? '#f4c7bb' : key === 'abhijit' ? '#b6dfc5' : palette[(row.num ?? i) % palette.length]
  return { left: lo*100+'%', width: (hi-lo)*100+'%', background }
}
function shortLabel(key: string, r: Interval) {
  if (key === 'hora') return r.planet?.slice(0,2)
  if (key === 'muhurta') return ((r.num! - 1) % 15) + 1
  if (key === 'yama' || key === 'lagna') return r.num
  return label(r)
}
const current = computed(() => Object.fromEntries(Object.entries(timeline.value?.rows ?? {}).map(([key,rows]) =>
  [key, rows.find(r => ms(r.dt_start) <= instant.value && instant.value < ms(r.dt_end))])))
const { data: nakshatras } = useLazyAsyncData('day-nakshatra-reference', () =>
  import('~content/nakshatras.json').then(m => m.default))
const currentNak = computed(() => nakshatras.value?.find(n => n.no === current.value.nakshatra?.num))
const details = [['vara','Вара'],['tithi','Титхи'],['nakshatra','Накшатра'],['karana','Карана'],['yoga','Йога']]
function description(key: string, r: Interval) {
  if (key === 'vara') return reference.vara.days.find(d => d.day === r.name)?.planet
  if (key === 'yoga') return reference.yoga.list.find(y => y.n === r.num)?.mean
  if (key === 'tithi') return tithis.tithis.find(t => t.n === ((r.num!-1)%15)+1)?.do
  if (key === 'karana') return [...reference.karana.movable,...reference.karana.fixed].find(k => r.name?.startsWith(k.name.split(' ')[0]))?.good
  return [r.lord && 'Управитель · '+r.lord, currentNak.value?.nature, currentNak.value?.devata].filter(Boolean).join('. ')
}
function fullLabel(key: string, r: Interval) {
  if (key === 'lagna') return r.num + ' · ' + r.name
  if (key === 'muhurta' || key === 'hora') return shortLabel(key,r) + ' · ' + label(r)
  return label(r)
}
const karakas = computed(() => {
  const list = (chart.value?.planets ?? []).filter((p:any) => p.available && p.idx < 7)
  const names = ['АК','АмК','БК','МК','ПК','ГК','ДК']
  return Object.fromEntries(list.sort((a:any,b:any) => b.deg_in_sign-a.deg_in_sign).map((p:any,i:number) => [p.idx,names[i]]))
})
</script>
<template>
  <article class="pd">
    <header class="heading"><div><h1>Панчанга на день</h1><p>{{ place.city }} · UTC{{ place.tz >= 0 ? '+' : '' }}{{ place.tz }} · {{ mode === 'apparent' ? 'Видимые положения' : 'Геометрические положения' }}</p></div>
      <div class="buttons"><button @click="today">Сегодня</button><button @click="openMonth">На месяц</button><button @click="settings = !settings">Место и расчёт</button></div>
    </header>
    <section v-if="settings" class="panel prefs">
      <CityField v-model:city="place.city" v-model:lat="place.lat" v-model:lon="place.lon" v-model:tz="place.tz" :date="day" :time="clock" />
      <label>Широта<input v-model.number="place.lat" type="number" min="-90" max="90" step="0.0001"></label>
      <label>Долгота<input v-model.number="place.lon" type="number" min="-180" max="180" step="0.0001"></label>
      <label>UTC, ч<input v-model.number="place.tz" type="number" min="-14" max="14" step="0.25"></label>
      <PositionModeField v-model="mode" />
    </section>
    <section v-if="monthOpen" class="panel month"><label>Месяц <input type="month" v-model="month"></label>
      <div class="monthgrid"><b v-for="w in ['Пн','Вт','Ср','Чт','Пт','Сб','Вс']" :key="w">{{ w }}</b>
        <template v-for="(d,i) in monthDays" :key="i"><button v-if="d" :class="{ chosen: d===day }" @click="day=d; monthOpen=false">{{ Number(d.slice(-2)) }}</button><span v-else /></template>
      </div>
    </section>
    <div class="toolbar"><button aria-label="Предыдущий день" @click="shift(-1)">‹</button><input aria-label="Дата" type="date" :value="day" @change="day=($event.target as HTMLInputElement).value || day"><button aria-label="Следующий день" @click="shift(1)">›</button>
      <label>Местное время <input aria-label="Местное время" type="time" :value="clock" @change="clock=($event.target as HTMLInputElement).value || clock"></label>
    </div>
    <p v-if="dayError" role="alert">{{ dayError }}</p><p v-else-if="!timeline" role="status">Рассчитываем сутки…</p>
    <template v-if="timeline">
      <p v-for="w in timeline.warnings" :key="w">{{ w }}</p>
      <div class="scroll panel"><div class="scale">
        <div class="track"><b>Часы</b><div class="axis"><span v-for="h in 24" :key="h">{{ h-1 }}</span></div></div>
        <div v-for="[key,title] in tracks" :key="key" class="track">
          <b>{{ title }}</b><div class="rail" @click="pick"><span v-for="(r,i) in timeline.rows[key]" :key="r.dt_start" class="bar" :class="{ stop: r.is_bhadra || r.is_stop }" :style="block(r,key,i)" :title="fullLabel(key,r)+' · '+full(r.dt_start)+' — '+full(r.dt_end)">{{ shortLabel(key,r) }}<small v-if="['vara','tithi','nakshatra','karana','yoga','moon'].includes(key)">{{ hhmm(r.dt_start) }}–{{ hhmm(r.dt_end) }}</small></span><i :style="{ left:minute/14.4+'%' }"/></div>
        </div>
      </div></div>
      <div class="windows"><span v-for="k in ['rahu','abhijit']" :key="k"><template v-for="r in timeline.rows[k]" :key="r.dt_start"><strong>{{ r.name }}</strong> {{ hhmm(r.dt_start) }}–{{ hhmm(r.dt_end) }} </template></span></div>
      <p class="moment">В {{ clock }} · {{ current.lagna?.name || '—' }} на восходе · Мухурта {{ current.muhurta?.name || '—' }} · Хора {{ current.hora?.planet || '—' }}</p>
      <h2>Панчанга в {{ clock }}</h2><div class="cards">
        <section v-for="[key,title] in details" :key="key" class="panel detail"><small>{{ title }}</small>
          <template v-if="current[key]"><h3>{{ current[key]?.num }} · {{ current[key]?.name }}</h3>
            <p>{{ full(current[key]!.dt_start) }} — {{ full(current[key]!.dt_end) }}</p>
            <p v-if="current[key]?.sunset">Закат {{ hhmm(current[key]!.sunset!) }}</p>
            <p>{{ [current[key]?.paksha,current[key]?.type,current[key]?.quality].filter(Boolean).join(' · ') }}</p>
            <p>{{ description(key,current[key]!) }}</p>
          </template><p v-else>Интервал не определён</p>
        </section>
      </div>
    </template>
    <h2>Раши D1 · {{ clock }}</h2>
    <p v-if="chartError" role="alert">{{ chartError }}</p><p v-else-if="!chart">Рассчитываем карту…</p>
    <div v-else class="positions"><LagnaChart :horoscope="chart" /><div class="scroll panel"><table><thead><tr><th>Граха</th><th>Карака</th><th>Знак</th><th>Градус</th><th>Накшатра</th><th>Пада</th></tr></thead>
      <tbody><tr><td>Лагна</td><td>—</td><td>{{ chart.lagna.sign_ru }}</td><td>{{ chart.lagna.deg_in_sign_dms }}</td><td>{{ chart.lagna.nakshatra_ru }}</td><td>{{ chart.lagna.pada }}</td></tr>
        <tr v-for="p in chart.planets" :key="p.idx"><td>{{ p.name }}{{ p.retro ? ' ℞' : '' }}</td><td>{{ karakas[p.idx] || '—' }}</td><td>{{ p.sign_ru }}</td><td>{{ p.deg_in_sign_dms }}</td><td>{{ p.nakshatra_ru }}</td><td>{{ p.pada }}</td></tr></tbody>
    </table></div></div>
  </article>
</template>
<style scoped>
.pd{color:#253948;font:15px/1.45 system-ui,sans-serif}.heading,.buttons,.toolbar,.windows,.prefs{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.heading{justify-content:space-between}.heading h1{font-size:clamp(28px,4vw,43px);letter-spacing:-.045em}.heading p,.detail small{color:#506c71}.heading p,.detail p{margin:.35rem 0}.pd button,.pd input,.pd select{color:inherit;font:inherit}.pd button,.pd input{background:white;border:1px solid #bdcfcf;border-radius:8px;padding:7px 11px}.pd button{cursor:pointer}.pd button:hover,.pd button.chosen{background:#e1f0e9}.buttons button:first-child{background:#166047;color:white}.toolbar{margin:22px 0 12px}.toolbar label{margin-left:auto}.panel{background:white;border:1px solid #d6e0df;border-radius:12px}.prefs,.month{padding:15px;margin-top:12px}.prefs input{max-width:130px}.month{max-width:340px}.monthgrid{display:grid;grid-template-columns:repeat(7,1fr);gap:3px;margin-top:10px;text-align:center}.monthgrid button{padding:5px}.scroll{overflow:auto}.scale{min-width:770px;padding:14px 16px}.track{display:grid;grid-template-columns:112px 1fr;align-items:stretch}.track>b{font-size:12px;align-self:center}.axis{display:flex;justify-content:space-between;color:#61767a;font-size:11px}.axis span{width:4.1667%}.rail{height:33px;position:relative;background:repeating-linear-gradient(90deg,#dce4e2 0 1px,transparent 1px 4.16667%);cursor:crosshair}.bar{box-sizing:border-box;position:absolute;top:2px;bottom:2px;border:1px solid white;border-radius:6px;padding:3px;overflow:hidden;white-space:nowrap;color:#263e48;font-size:13px;text-align:center}.bar.stop{border-bottom:3px solid #bd5554}.track:has(.bar small) .rail{height:49px}.bar small{display:block;font-size:10px}.moment{color:#405961}.rail i{position:absolute;top:0;bottom:0;width:2px;background:#13694e;pointer-events:none}.windows{margin:11px 0;color:#465e62;gap:22px}.pd h2{margin:26px 0 10px;font-size:21px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}.detail{padding:13px}.detail h3{margin:4px 0;font-size:18px}.detail p{font-size:13px}.positions{display:grid;grid-template-columns:minmax(230px,1fr) 2fr;gap:14px}.positions table{width:100%;min-width:520px;border-collapse:collapse}.positions td,.positions th{padding:7px;text-align:left;border-bottom:1px solid #e0e6e6}.pd [role=alert]{color:#993f32}@media(max-width:720px){.positions{grid-template-columns:1fr}.toolbar label{margin-left:0}.heading{align-items:flex-start}.cards{grid-template-columns:repeat(auto-fit,minmax(145px,1fr))}}
</style>
