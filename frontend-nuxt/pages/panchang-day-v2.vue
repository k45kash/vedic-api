<script setup lang="ts">
import type { PositionMode } from '~/composables/useBirthForm'
import reference from '~content/panchanga.json'
import tithis from '~content/tithi.json'

useHead({ title: 'Панчанга v2 · Vedic' })
const api = useApi()
type Interval = {
  dt_start: string; dt_end: string; name?: string; planet?: string; num?: number
  type?: string; quality?: string; lord?: string; paksha?: string; sunset?: string
  is_bhadra?: boolean; is_stop?: boolean; day_night?: string
}
type Timeline = { rows: Record<string, Interval[]>; warnings: string[] }
const requested = useRoute().query
function coordinate(key: string, fallback: number, limit: number) {
  const input = requested[key]
  const value = typeof input === 'string' && input.trim() ? Number(input) : NaN
  return Number.isFinite(value) && Math.abs(value) <= limit ? value : fallback
}
const place = reactive({
  city: typeof requested.city === 'string' ? requested.city.slice(0, 120) : 'Ставрополь',
  lat: coordinate('lat', 45.0428, 90),
  lon: coordinate('lon', 41.9734, 180),
  tz: coordinate('tz', 3, 14),
})
const mode = ref<PositionMode>(requested.mode === 'geometric' ? 'geometric' : 'apparent')
const extraTracks = ref(false)
const showChart = ref(false)
const sharedStatus = ref('')
const shareUrl = ref('')
const manualTz = ref(typeof requested.tz === 'string')
const tzNote = ref('')
const mobile = ref(false)
let media: MediaQueryList | undefined
function updateViewport() { mobile.value = media?.matches ?? false }
onMounted(() => {
  media = window.matchMedia('(max-width: 720px)')
  updateViewport()
  media.addEventListener('change', updateViewport)
})
onBeforeUnmount(() => media?.removeEventListener('change', updateViewport))
const settings = ref(false)
const monthOpen = ref(false)
const localNow = () => new Date(Date.now() + place.tz * 3600000).toISOString()
const requestedDate = String(requested.date ?? '')
const requestedTime = String(requested.time ?? '')
const parsedDate = new Date(requestedDate + 'T00:00:00Z')
const day = ref(Number.isFinite(parsedDate.getTime()) && parsedDate.toISOString().slice(0,10) === requestedDate
  ? requestedDate : localNow().slice(0,10))
const clock = ref(/^([01]\d|2[0-3]):[0-5]\d$/.test(requestedTime) ? requestedTime : localNow().slice(11,16))
const month = ref(day.value.slice(0, 7))
const timeline = ref<Timeline | null>(null)
const chart = ref<any>(null)
const chartLoading = ref(false)
const dayError = ref(''), chartError = ref('')
const monthData = ref<Record<string, { date: string; tithi: string | null; nakshatra: string | null; bhadra: boolean }>>({})
const monthStatus = ref('')
const shareQuery = computed(() => ({
  date: day.value, time: clock.value, city: place.city, lat: String(place.lat),
  lon: String(place.lon), tz: String(place.tz), mode: mode.value,
}))
watch(shareQuery, () => { shareUrl.value = ''; sharedStatus.value = '' })
async function share() {
  const url = new URL('/panchang-day-v2', window.location.origin)
  url.search = new URLSearchParams(shareQuery.value).toString()
  shareUrl.value = url.href
  try {
    await navigator.clipboard.writeText(url.href)
    sharedStatus.value = 'Ссылка скопирована'
  } catch {
    sharedStatus.value = 'Ссылка готова для копирования'
  }
}
watch([day, () => place.lat, () => place.lon, manualTz], async ([date, lat, lon, manual], _, cleanup) => {
  let live = true
  cleanup(() => { live = false })
  tzNote.value = ''
  if (manual || typeof lat !== 'number' || typeof lon !== 'number') return
  const [year, month, d] = date.split('-')
  const params = new URLSearchParams({ lat: String(lat), lon: String(lon), year, month, day: d })
  try {
    const zone = await api.get<{ tz_name: string; offset_hours: number }>('/api/tz?' + params)
    if (!live) return
    place.tz = zone.offset_hours
    tzNote.value = zone.tz_name
  } catch {
    if (live) tzNote.value = 'Часовой пояс не определён. Укажите смещение вручную.'
  }
}, { immediate: true })
watch([monthOpen, month, () => place.lat, () => place.lon, () => place.tz, mode],
  async ([open, selected, lat, lon, tz, position_mode], _, cleanup) => {
    let live = true
    cleanup(() => { live = false })
    monthData.value = {}
    monthStatus.value = ''
    if (!open || !selected) return
    monthStatus.value = 'Рассчитываем месяц…'
    try {
      const days = await api.post<Array<(typeof monthData.value)[string]>>('/api/panchang/month',
        { day: selected + '-01', lat, lon, tz, position_mode })
      if (live) {
        monthData.value = Object.fromEntries(days.map(item => [item.date, item]))
        monthStatus.value = ''
      }
    } catch {
      if (live) monthStatus.value = 'Не удалось рассчитать месяц.'
    }
  })

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
watch([query, clock, mobile, showChart], ([q, time], _, cleanup) => {
  let live = true
  chart.value = null
  chartError.value = ''
  chartLoading.value = Boolean(time && (!mobile.value || showChart.value))
  if (!chartLoading.value) return
  const timer = setTimeout(async () => {
    const [year, month, d] = q.day.split('-').map(Number)
    const [hour, minute] = time.split(':').map(Number)
    try {
      const result = await api.post('/api/horoscope', { ...q, year, month, day: d, hour, minute })
      if (live) chart.value = result
    } catch (e) {
      if (live) chartError.value = String(e)
    } finally {
      if (live) chartLoading.value = false
    }
  }, 150)
  cleanup(() => { live = false; clearTimeout(timer) })
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
const advanced = new Set(['lagna','moon','muhurta','yama','hora'])
const visibleTracks = computed(() => tracks.filter(([key]) => extraTracks.value || !mobile.value || !advanced.has(key)))
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
const nextChange = computed(() => {
  const next = details.flatMap(([key, title]) => {
    const active = current.value[key]
    const following = timeline.value?.rows[key]?.find(row => row.dt_start === active?.dt_end)
    return active ? [{ key, title, at: active.dt_end, following }] : []
  }).sort((a,b) => ms(a.at) - ms(b.at))
  if (!next.length) return []
  return next.filter(item => item.at === next[0].at)
})
const overlaps = computed(() => (timeline.value?.rows.abhijit ?? []).flatMap(abhijit =>
  (timeline.value?.rows.rahu ?? []).flatMap(rahu => {
    const start = ms(abhijit.dt_start) >= ms(rahu.dt_start) ? abhijit.dt_start : rahu.dt_start
    const end = ms(abhijit.dt_end) <= ms(rahu.dt_end) ? abhijit.dt_end : rahu.dt_end
    return ms(start) < ms(end) ? [{ dt_start: start, dt_end: end }] : []
  })))
function goToChange(at: string) {
  const target = new Date(Math.ceil(ms(at) / 60000) * 60000).toISOString()
  day.value = target.slice(0, 10)
  clock.value = target.slice(11, 16)
}
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
    <header class="heading"><div><h1>Панчанга на день</h1><NuxtLink :to="{ path: '/panchang-day', query: { date: day, time: clock } }">Эталон для сверки</NuxtLink><p>{{ place.city }} · UTC{{ place.tz >= 0 ? '+' : '' }}{{ place.tz }} · {{ mode === 'apparent' ? 'Видимые положения' : 'Геометрические положения' }}</p></div>
      <div class="buttons"><button @click="today">Сегодня</button><button @click="openMonth">На месяц</button><button @click="settings = !settings" :aria-expanded="settings">Место и расчёт</button><button @click="share">Ссылка для сверки</button></div>
    </header>
    <div v-if="shareUrl" class="share">
      <span role="status">{{ sharedStatus }}</span>
      <input aria-label="Ссылка для сверки" :value="shareUrl" readonly @focus="($event.target as HTMLInputElement).select()">
    </div>
    <section v-if="settings" class="panel prefs">
      <CityField v-model:city="place.city" v-model:lat="place.lat" v-model:lon="place.lon" :tz="place.tz" :date="day" skip-timezone-lookup />
      <label>Широта<input v-model.number="place.lat" type="number" min="-90" max="90" step="0.0001"></label>
      <label>Долгота<input v-model.number="place.lon" type="number" min="-180" max="180" step="0.0001"></label>
      <label>UTC, ч<input v-model.number="place.tz" @input="manualTz = true" type="number" min="-14" max="14" step="0.25"></label>
      <label><input v-model="manualTz" type="checkbox"> Смещение вручную</label>
      <small>{{ tzNote }} Смещение применяется ко всем суткам.</small>
      <PositionModeField v-model="mode" />
    </section>
    <section v-if="monthOpen" class="panel month"><label>Месяц <input type="month" v-model="month"></label>
      <p v-if="monthStatus" role="status">{{ monthStatus }}</p>
      <div class="monthgrid"><b v-for="w in ['Пн','Вт','Ср','Чт','Пт','Сб','Вс']" :key="w">{{ w }}</b>
        <template v-for="(d,i) in monthDays" :key="i"><button v-if="d" :class="{ chosen: d===day }" @click="day=d; monthOpen=false"><strong>{{ Number(d.slice(-2)) }}</strong>
          <template v-if="monthData[d]">
            <small>{{ monthData[d].tithi ?? 'Восхода нет' }}</small>
            <small>{{ monthData[d].nakshatra }}</small>
            <small v-if="monthData[d].bhadra" class="bhadra">Бхадра</small>
          </template>
        </button><span v-else /></template>
      </div>
    </section>
    <div class="toolbar"><button aria-label="Предыдущий день" @click="shift(-1)">‹</button><input aria-label="Дата" type="date" :value="day" @change="day=($event.target as HTMLInputElement).value || day"><button aria-label="Следующий день" @click="shift(1)">›</button>
      <label>Местное время <input aria-label="Местное время" type="time" :value="clock" @change="clock=($event.target as HTMLInputElement).value || clock"></label>
    </div>
    <p v-if="dayError" role="alert">{{ dayError }}</p><p v-else-if="!timeline" role="status">Рассчитываем сутки…</p>
    <template v-if="timeline">
      <p v-for="w in timeline.warnings" :key="w">{{ w }}</p>
      <section class="panel overview">
        <h2>Действует в {{ clock }}</h2>
        <dl>
          <div v-for="[key,title] in details" :key="key">
            <dt>{{ title }}</dt><dd>{{ current[key]?.name || '—' }}</dd>
            <dd v-if="current[key]">до {{ full(current[key]!.dt_end) }}</dd>
          </div>
        </dl>
        <div v-if="nextChange.length" class="next">
          <span>Ближайший переход · {{ full(nextChange[0].at) }}:{{ nextChange[0].at.slice(17,19) }}</span>
          <p>{{ nextChange.map(item => item.title + (item.following ? ' → ' + label(item.following) : '')).join(' · ') }}</p>
          <button @click="goToChange(nextChange[0].at)">К переходу</button>
        </div>
      </section>
      <button v-if="mobile" class="track-toggle" :aria-expanded="extraTracks" @click="extraTracks = !extraTracks">{{ extraTracks ? 'Свернуть дополнительные ряды' : 'Показать дополнительные ряды' }}</button>
      <label class="minute-slider">Минута на шкале <input type="range" min="0" max="1439" :value="minute" :aria-valuetext="clock" @input="selectMinute(Number(($event.target as HTMLInputElement).value))"></label>
      <div class="scroll panel"><div class="scale">
        <div class="marker-layer" aria-hidden="true"><div class="marker" :class="{ 'near-end': minute > 1320 }" :style="{ left: minute / 14.4 + '%' }"><span>{{ clock }}</span></div></div>
        <div class="track"><b>Часы</b><div class="axis"><span v-for="h in 24" :key="h">{{ h-1 }}</span></div></div>
        <div v-for="[key,title] in visibleTracks" :key="key" class="track">
          <b>{{ title }}</b><div class="rail" @click="pick"><span v-for="(r,i) in timeline.rows[key]" :key="r.dt_start" class="bar" :class="{ stop: r.is_bhadra || r.is_stop, active: r === current[key] }" :style="block(r,key,i)" :title="fullLabel(key,r)+' · '+full(r.dt_start)+' — '+full(r.dt_end)">{{ shortLabel(key,r) }}<small v-if="['vara','tithi','nakshatra','karana','yoga','moon'].includes(key)">{{ hhmm(r.dt_start) }}–{{ hhmm(r.dt_end) }}</small></span><span v-if="key === 'abhijit'" v-for="part in overlaps" :key="part.dt_start" class="overlap" :style="block(part,key,0)" title="Пересечение с Раху-калой"></span></div>
        </div>
      </div></div>
      <div class="windows"><span v-for="k in ['rahu','abhijit']" :key="k"><template v-for="r in timeline.rows[k]" :key="r.dt_start"><strong>{{ r.name }}</strong> {{ hhmm(r.dt_start) }}–{{ hhmm(r.dt_end) }} </template></span></div>
      <p v-for="part in overlaps" :key="part.dt_start" class="bhadra">Абхиджит пересекается с Раху-калой · {{ hhmm(part.dt_start) }}–{{ hhmm(part.dt_end) }}</p>
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
    <button v-if="mobile" class="track-toggle" :aria-expanded="showChart" @click="showChart = !showChart">{{ showChart ? 'Свернуть карту D1' : 'Показать карту D1' }}</button>
    <section v-if="!mobile || showChart">
    <h2>Раши D1 · {{ clock }}</h2>
    <p v-if="chartError" role="alert">{{ chartError }}</p><p v-else-if="chartLoading" role="status">Рассчитываем карту…</p>
    <div v-else-if="chart" class="positions"><LagnaChart :horoscope="chart" /><div class="scroll panel"><table><thead><tr><th>Граха</th><th>Карака</th><th>Знак</th><th>Градус</th><th>Накшатра</th><th>Пада</th></tr></thead>
      <tbody><tr><td>Лагна</td><td>—</td><td>{{ chart.lagna.sign_ru }}</td><td>{{ chart.lagna.deg_in_sign_dms }}</td><td>{{ chart.lagna.nakshatra_ru }}</td><td>{{ chart.lagna.pada }}</td></tr>
        <tr v-for="p in chart.planets" :key="p.idx"><td>{{ p.name }}{{ p.retro ? ' ℞' : '' }}</td><td>{{ karakas[p.idx] || '—' }}</td><td>{{ p.sign_ru }}</td><td>{{ p.deg_in_sign_dms }}</td><td>{{ p.nakshatra_ru }}</td><td>{{ p.pada }}</td></tr></tbody>
    </table></div></div>
    </section>
  </article>
</template>
<style scoped>
.pd{color:#253948;font:15px/1.45 system-ui,sans-serif}.heading,.buttons,.toolbar,.windows,.prefs{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.heading{justify-content:space-between}.heading h1{font-size:clamp(28px,4vw,43px);letter-spacing:-.045em}.heading p,.detail small{color:#506c71}.heading p,.detail p{margin:.35rem 0}.pd button,.pd input,.pd select{color:inherit;font:inherit}.pd button,.pd input{background:white;border:1px solid #bdcfcf;border-radius:8px;padding:7px 11px}.pd button{cursor:pointer}.pd button:hover,.pd button.chosen{background:#e1f0e9}.buttons button:first-child{background:#166047;color:white}.toolbar{margin:22px 0 12px}.toolbar label{margin-left:auto}.panel{background:white;border:1px solid #d6e0df;border-radius:12px}.prefs,.month{padding:15px;margin-top:12px}.prefs input{max-width:130px}.month{max-width:340px}.monthgrid{display:grid;grid-template-columns:repeat(7,1fr);gap:3px;margin-top:10px;text-align:center}.monthgrid button{padding:5px}.scroll{overflow:auto}.scale{min-width:770px;padding:14px 16px}.track{display:grid;grid-template-columns:112px 1fr;align-items:stretch}.track>b{font-size:12px;align-self:center}.axis{display:flex;justify-content:space-between;color:#61767a;font-size:11px}.axis span{width:4.1667%}.rail{height:33px;position:relative;background:repeating-linear-gradient(90deg,#dce4e2 0 1px,transparent 1px 4.16667%);cursor:crosshair}.bar{box-sizing:border-box;position:absolute;top:2px;bottom:2px;border:1px solid white;border-radius:6px;padding:3px;overflow:hidden;white-space:nowrap;color:#263e48;font-size:13px;text-align:center}.bar.stop{border-bottom:3px solid #bd5554}.track:has(.bar small) .rail{height:49px}.bar small{display:block;font-size:10px}.moment{color:#405961}.rail i{position:absolute;top:0;bottom:0;width:2px;background:#13694e;pointer-events:none}.windows{margin:11px 0;color:#465e62;gap:22px}.pd h2{margin:26px 0 10px;font-size:21px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}.detail{padding:13px}.detail h3{margin:4px 0;font-size:18px}.detail p{font-size:13px}.positions{display:grid;grid-template-columns:minmax(230px,1fr) 2fr;gap:14px}.positions table{width:100%;min-width:520px;border-collapse:collapse}.positions td,.positions th{padding:7px;text-align:left;border-bottom:1px solid #e0e6e6}.pd [role=alert]{color:#993f32}@media(max-width:720px){.positions{grid-template-columns:1fr}.toolbar label{margin-left:0}.heading{align-items:flex-start}.cards{grid-template-columns:repeat(auto-fit,minmax(145px,1fr))}}

.share { display: grid; gap: 4px; margin-top: 12px; }
.overview { padding: 14px; margin-bottom: 14px; background: #f6fbf8; }
.overview h2 { margin: 0 0 10px; }
.overview dl { display: grid; grid-template-columns: repeat(auto-fit, minmax(125px, 1fr)); gap: 10px; margin: 0; }
.overview dt { font-size: 12px; color: #526c66; }
.overview dd { margin: 0; }
.overview dd:first-of-type { font-weight: 700; }
.overview dd + dd { font-size: 12px; }
.next { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 12px; margin-top: 13px; padding-top: 10px; border-top: 1px solid #d6e0df; }
.next p { margin: 0; }
.minute-slider { display: flex; align-items: center; gap: 10px; margin: 8px 0; }
.pd input[type="range"] { accent-color: #166047; width: min(100%, 320px); padding: 0; }
.scale { position: relative; --track-label-width: 112px; }
.track { grid-template-columns: var(--track-label-width) 1fr; }
.track > b { position: sticky; left: 0; z-index: 4; background: #fff; padding: 4px; align-self: stretch; display: grid; align-items: center; }
.marker-layer { position: absolute; inset: 0 16px 0 calc(var(--track-label-width) + 16px); pointer-events: none; z-index: 3; }
.marker { position: absolute; inset-block: 0; border-left: 2px solid #12674b; }
.marker span { display: block; padding: 2px 5px; border-radius: 4px; background: #12674b; color: #fff; font-size: 11px; }
.marker.near-end span { transform: translateX(-100%); }
.bar.active { box-shadow: inset 0 0 0 2px #166047; font-weight: 700; }
.overlap { position: absolute; inset-block: 2px; pointer-events: none; background: repeating-linear-gradient(135deg,#914d4966 0 3px, transparent 3px 7px) !important; }
.bhadra { color: #8c382e; }
.month { max-width: none; }
.monthgrid button { min-width: 0; text-align: left; }
.monthgrid small { display: block; overflow-wrap: anywhere; font-size: 11px; }
.track-toggle { margin: 10px 0; }
@media(max-width: 720px) {
  .pd { min-width: 0; }
  .overview dl { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .scale { --track-label-width: 95px; }
  .month { overflow: auto; }
  .monthgrid { min-width: 490px; }
}
</style>
