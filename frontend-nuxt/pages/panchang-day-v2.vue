<script setup lang="ts">
import type { PositionMode } from '~/composables/useBirthForm'
import reference from '~content/panchanga.json'
import tithis from '~content/tithi.json'

import { ApiError } from '~/composables/useApi'

definePageMeta({ layout: 'app', middleware: 'auth' })
useHead({ title: 'Панчанга на день · Vedic' })
usePageHeader().setPageHeader({ title: 'Панчанга на день' })
const api = useApi()
type Interval = {
  dt_start: string; dt_end: string; name?: string; planet?: string; num?: number
  type?: string; quality?: string; lord?: string; paksha?: string; sunset?: string
  is_bhadra?: boolean; is_stop?: boolean; day_night?: string
}
type Timeline = { start?: string; end?: string; timezone?: string; rows: Record<string, Interval[]>; warnings: string[] }
const route = useRoute()
const requested = route.query
const auth = useAuth()

function redirectExpiredSession(error: unknown) {
  if (!(error instanceof ApiError) || error.status !== 401) return false
  auth.logout()
  void navigateTo({ path: '/login', query: { redirect: route.fullPath } }, { replace: true })
  return true
}
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
const manualTz = ref(requested.auto !== '1' && typeof requested.tz === 'string')
const clockHint = ref('')
const selectedEpoch = ref(typeof requested.utc === 'string' ? Date.parse(requested.utc) : NaN)
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
  lon: String(place.lon), tz: String(selected.value?.offset ?? place.tz), mode: mode.value,
  ...(!manualTz.value ? { auto: '1', utc: timeline.value?.timezone && selected.value ? new Date(selected.value.epoch).toISOString() : '' } : {}),
}))
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
watch([monthOpen, month, () => place.lat, () => place.lon, () => place.tz, mode, manualTz],
  async ([open, selected, lat, lon, tz, position_mode, manual], _, cleanup) => {
    let live = true
    cleanup(() => { live = false })
    monthData.value = {}
    monthStatus.value = ''
    if (!open || !selected) return
    monthStatus.value = 'Рассчитываем месяц…'
    try {
      const days = await api.post<Array<(typeof monthData.value)[string]>>('/api/panchang/month',
        { day: selected + '-01', lat, lon, tz, position_mode, use_local_timezone: !manual })
      if (live) {
        monthData.value = Object.fromEntries(days.map(item => [item.date, item]))
        monthStatus.value = ''
      }
    } catch (error) {
      if (live && !redirectExpiredSession(error)) monthStatus.value = 'Не удалось рассчитать месяц.'
    }
  })

const query = computed(() => ({ day: day.value, lat: place.lat, lon: place.lon, tz: place.tz, position_mode: mode.value, use_local_timezone: !manualTz.value }))
watch(query, async (q, _, cleanup) => {
  let live = true
  cleanup(() => { live = false })
  timeline.value = null
  dayError.value = ''
  try {
    const data = await api.post<Timeline>('/api/panchang/day', q)
    if (live) timeline.value = data
  } catch (error) {
    if (live && !redirectExpiredSession(error)) dayError.value = String(error)
  }
}, { immediate: true })
const dateMs = computed(() => Date.parse(day.value + 'T00:00Z'))
const windowStart = computed(() => timeline.value?.start ? Date.parse(timeline.value.start) : dateMs.value)
const dayMinutes = computed(() => timeline.value?.end ? Math.round((Date.parse(timeline.value.end) - windowStart.value) / 60000) : 1440)
const zonedFormat = computed(() => timeline.value?.timezone ? new Intl.DateTimeFormat('sv-SE', {
  timeZone: timeline.value.timezone, year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
}) : null)
function localStamp(epoch: number) {
  return zonedFormat.value?.format(epoch).replace(' ', 'T') ?? new Date(epoch).toISOString()
}
const minutes = computed(() => Array.from({ length: dayMinutes.value }, (_, index) => {
  const epoch = windowStart.value + index * 60000
  const stamp = localStamp(epoch)
  const local = stamp.slice(11,16)
  const offset = zonedFormat.value ? (Date.parse(stamp.slice(0,16) + 'Z') - epoch) / 3600000 : place.tz
  return { epoch, local, offset, index }
}))
const clockOptions = computed(() => minutes.value.filter(slot => slot.local === clock.value))
const selected = computed(() => clockOptions.value.find(slot => slot.epoch === selectedEpoch.value) ?? clockOptions.value[0])
const minute = computed(() => selected.value?.index ?? 0)
const instant = computed(() => selected.value?.epoch ?? NaN)
const hourTicks = computed(() => minutes.value.filter(slot => slot.local.endsWith(':00')))
const ms = (stamp: string) => Date.parse(/[+-]\d{2}:\d{2}$|Z$/.test(stamp) ? stamp : stamp + 'Z')
const hhmm = (stamp: string) => stamp.slice(11, 16)
const full = (stamp: string) => stamp.slice(8,10) + '.' + stamp.slice(5,7) + ' ' + hhmm(stamp)
const offsetLabel = (offset: number) => {
  const total = Math.round(Math.abs(offset) * 60)
  return 'UTC' + (offset < 0 ? '−' : '+') + Math.floor(total / 60)
    + (total % 60 ? ':' + String(total % 60).padStart(2, '0') : '')
}
watch(shareQuery, () => { shareUrl.value = ''; sharedStatus.value = '' })
function selectMinute(n: number) {
  const slot = minutes.value[Math.max(0, Math.min(dayMinutes.value - 1, Math.floor(n)))]
  if (!slot) return
  clockHint.value = ''
  clock.value = slot.local
  selectedEpoch.value = slot.epoch
}
function changeTimezoneMode(event: Event) {
  const manual = (event.target as HTMLInputElement).checked
  if (manual && selected.value) place.tz = selected.value.offset
  manualTz.value = manual
}
function changeClock(event: Event) {
  const input = event.target as HTMLInputElement
  const match = minutes.value.find(slot => slot.local === input.value)
  if (match) selectMinute(match.index)
  else {
    clockHint.value = input.value ? 'Этой минуты нет в местных сутках из-за перевода часов.' : ''
    input.value = clock.value
  }
}
watch(timeline, data => {
  if (!data || selected.value || !minutes.value.length) return
  const slot = minutes.value.find(item => item.local >= clock.value) ?? minutes.value[0]
  selectMinute(slot.index)
  clockHint.value = 'Выбранное время пропущено при переводе часов. Показана ближайшая доступная минута.'
})
function pick(e: MouseEvent) {
  const box = (e.currentTarget as HTMLElement).getBoundingClientRect()
  selectMinute((e.clientX - box.left) / box.width * dayMinutes.value)
}
function shift(n: number) {
  clockHint.value = ''
  day.value = new Date(dateMs.value + n * 86400000).toISOString().slice(0,10)
}
function today() {
  const now = zonedFormat.value ? localStamp(Date.now()) : localNow()
  clockHint.value = ''
  day.value = now.slice(0,10)
  clock.value = now.slice(11,16)
  selectedEpoch.value = Math.floor(Date.now() / 60000) * 60000
}

watch([query, selected, timeline, mobile, showChart], ([q, slot, data], _, cleanup) => {
  let live = true
  chart.value = null
  chartError.value = ''
  chartLoading.value = Boolean(data && slot && (!mobile.value || showChart.value))
  if (!chartLoading.value || !slot) return
  const timer = setTimeout(async () => {
    const [year, month, d] = q.day.split('-').map(Number)
    const [hour, minute] = slot.local.split(':').map(Number)
    try {
      const result = await api.post('/api/horoscope', { ...q, tz: slot.offset, year, month, day: d, hour, minute })
      if (live) chart.value = result
    } catch (e) {
      if (live) chartError.value = String(e)
    } finally {
      if (live) chartLoading.value = false
    }
  }, 150)
  cleanup(() => { live = false; clearTimeout(timer) })
}, { immediate: true })

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
  const lo = Math.max(0, (ms(row.dt_start)-windowStart.value)/(dayMinutes.value * 60000))
  const hi = Math.min(1, (ms(row.dt_end)-windowStart.value)/(dayMinutes.value * 60000))
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
// Группируем по абсолютному времени: повторяющийся час может иметь одинаковую
// подпись на шкале, хотя события относятся к разным моментам.
const dayEvents = computed(() => {
  const rows = timeline.value?.rows
  if (!rows) return []
  const start = windowStart.value
  const end = start + dayMinutes.value * 60000
  const groups = new Map<number, { stamp: string; epoch: number; labels: string[] }>()
  function add(stamp: string, description: string) {
    const epoch = ms(stamp)
    if (!Number.isFinite(epoch) || epoch < start || epoch >= end) return
    const group = groups.get(epoch)
    if (group) group.labels.push(description)
    else groups.set(epoch, { stamp, epoch, labels: [description] })
  }

  for (const [key, title] of details) {
    for (const interval of rows[key] ?? []) {
      const prefix = key === 'vara' ? 'Восход · ' : ''
      add(interval.dt_start, prefix + title + ' → ' + label(interval))
      if (interval.sunset) add(interval.sunset, 'Закат')
    }
  }
  for (const key of ['rahu', 'abhijit']) {
    for (const interval of rows[key] ?? []) {
      add(interval.dt_start, label(interval) + ' начинается')
      add(interval.dt_end, label(interval) + ' заканчивается')
    }
  }
  return [...groups.values()].sort((a, b) => a.epoch - b.epoch)
})
const nextDayEvent = computed(() => dayEvents.value.find(event => event.epoch > instant.value))
function eventTime(stamp: string) {
  const time = stamp.slice(11, 19)
  const offset = stamp.match(/[+-]\d{2}:\d{2}$/)?.[0]
  return dayMinutes.value !== 1440 && offset ? time + ' · UTC' + offset : time
}
const abhijitComparison = computed(() => {
  const rahu = timeline.value?.rows.rahu ?? []
  return (timeline.value?.rows.abhijit ?? []).map(abhijit => {
    const overlaps = rahu.flatMap(window => {
      const dt_start = ms(abhijit.dt_start) >= ms(window.dt_start) ? abhijit.dt_start : window.dt_start
      const dt_end = ms(abhijit.dt_end) <= ms(window.dt_end) ? abhijit.dt_end : window.dt_end
      return ms(dt_start) < ms(dt_end) ? [{ dt_start, dt_end }] : []
    }).sort((a, b) => ms(a.dt_start) - ms(b.dt_start))
    const outsideRahu = []
    let cursor = abhijit.dt_start
    for (const overlap of overlaps) {
      if (ms(cursor) < ms(overlap.dt_start)) {
        outsideRahu.push({ dt_start: cursor, dt_end: overlap.dt_start })
      }
      if (ms(cursor) < ms(overlap.dt_end)) cursor = overlap.dt_end
    }
    if (ms(cursor) < ms(abhijit.dt_end)) outsideRahu.push({ dt_start: cursor, dt_end: abhijit.dt_end })
    return { abhijit, overlaps, outsideRahu }
  })
})
const overlaps = computed(() => abhijitComparison.value.flatMap(item => item.overlaps))
function intervalTimes(interval: Pick<Interval, 'dt_start' | 'dt_end'>) {
  return hhmm(interval.dt_start) + '–' + hhmm(interval.dt_end)
}
function goToChange(at: string) {
  const epoch = Math.ceil(ms(at) / 60000) * 60000
  const target = localStamp(epoch)
  selectedEpoch.value = epoch
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
    <header class="heading"><div><p>{{ place.city }} · {{ offsetLabel(selected?.offset ?? place.tz) }} · {{ mode === 'apparent' ? 'Видимые положения' : 'Геометрические положения' }}</p></div>
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
      <label><input :checked="manualTz" @change="changeTimezoneMode" type="checkbox"> Смещение вручную</label>
      <small>{{ manualTz ? 'Одно смещение на все сутки' : (timeline?.timezone ?? 'Зона определяется по координатам') }}</small>
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
      <label>Местное время <input aria-label="Местное время" type="time" :value="clock" @change="changeClock"></label>
    </div>
    <label v-if="clockOptions.length > 1" class="clock-choice">Повтор часа
      <select :value="minute" @change="selectMinute(Number(($event.target as HTMLSelectElement).value))">
        <option v-for="(slot,index) in clockOptions" :key="slot.epoch" :value="slot.index">{{ index + 1 }}-е вхождение · {{ offsetLabel(slot.offset) }}</option>
      </select>
    </label>
    <p v-if="clockHint" role="status">{{ clockHint }}</p>
    <p v-if="dayError" role="alert">{{ dayError }}</p><p v-else-if="!timeline" role="status">Рассчитываем сутки…</p>
    <p v-for="warning in timeline?.warnings" :key="warning">{{ warning }}</p>
    <template v-if="timeline && dayMinutes > 0">
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
      <details v-if="dayEvents.length" class="panel day-events">
        <summary>Переходы дня</summary>
        <ol>
          <li v-for="event in dayEvents" :key="event.epoch" :class="{ upcoming: nextDayEvent === event }">
            <button type="button" :aria-label="'К событию в ' + eventTime(event.stamp)" @click="goToChange(event.stamp)">
              {{ eventTime(event.stamp) }}
            </button>
            <div>
              <small v-if="nextDayEvent === event">Следующее событие</small>
              <span v-for="description in event.labels" :key="description">{{ description }}</span>
            </div>
          </li>
        </ol>
      </details>
      <button v-if="mobile" class="track-toggle" :aria-expanded="extraTracks" @click="extraTracks = !extraTracks">{{ extraTracks ? 'Свернуть дополнительные ряды' : 'Показать дополнительные ряды' }}</button>
      <label class="minute-slider">Минута на шкале <input type="range" min="0" :max="dayMinutes - 1" :value="minute" :aria-valuetext="clockOptions.length > 1 && selected ? clock + ' · ' + offsetLabel(selected.offset) : clock" @input="selectMinute(Number(($event.target as HTMLInputElement).value))"></label>
      <div class="scroll panel"><div class="scale">
        <div class="marker-layer" aria-hidden="true"><div class="marker" :class="{ 'near-end': minute > dayMinutes - 120 }" :style="{ left: minute / dayMinutes * 100 + '%' }"><span>{{ clock }}</span></div></div>
        <div class="track"><b>Часы</b><div class="axis"><span v-for="slot in hourTicks" :key="slot.epoch" :title="offsetLabel(slot.offset)" :style="{ left: slot.index / dayMinutes * 100 + '%' }">{{ Number(slot.local.slice(0,2)) }}</span></div></div>
        <div v-for="[key,title] in visibleTracks" :key="key" class="track">
          <b>{{ title }}</b><div class="rail" @click="pick"><span v-for="(r,i) in timeline.rows[key]" :key="r.dt_start" class="bar" :class="{ stop: r.is_bhadra || r.is_stop, active: r === current[key] }" :style="block(r,key,i)" :title="fullLabel(key,r)+' · '+full(r.dt_start)+' — '+full(r.dt_end)">{{ shortLabel(key,r) }}<small v-if="['vara','tithi','nakshatra','karana','yoga','moon'].includes(key)">{{ hhmm(r.dt_start) }}–{{ hhmm(r.dt_end) }}</small></span><span v-if="key === 'abhijit'" v-for="part in overlaps" :key="part.dt_start" class="overlap" :style="block(part,key,0)" title="Пересечение с Раху-калой"></span></div>
        </div>
      </div></div>
      <div class="windows"><span v-for="k in ['rahu','abhijit']" :key="k"><template v-for="r in timeline.rows[k]" :key="r.dt_start"><strong>{{ r.name }}</strong> {{ hhmm(r.dt_start) }}–{{ hhmm(r.dt_end) }} </template></span></div>
      <details v-if="overlaps.length" class="panel calculation-note">
        <summary>Как пересекаются Абхиджит и Раху-кала</summary>
        <dl v-for="{ abhijit, overlaps: intersection, outsideRahu } in abhijitComparison" :key="abhijit.dt_start">
          <dt>Полный Абхиджит</dt><dd>{{ intervalTimes(abhijit) }}</dd>
          <dt>Пересечение с Раху-калой</dt>
          <dd>{{ intersection.map(intervalTimes).join(', ') || 'Нет пересечения' }}</dd>
          <dt>Абхиджит вне Раху-калы</dt>
          <dd>{{ outsideRahu.map(intervalTimes).join(', ') || 'Нет такого интервала' }}</dd>
        </dl>
        <p>Время вне Раху-калы показано для сверки. Оценка мухурты зависит от остальных факторов панчанги.</p>
      </details>
      <p class="moment">В {{ clock }} · {{ current.lagna?.name || '—' }} на восходе · Мухурта {{ current.muhurta?.name || '—' }} · Хора {{ current.hora?.planet || '—' }}</p>
      <h2>Панчанга в {{ clock }}</h2><div class="cards">
        <section v-for="[key,title] in details" :key="key" class="panel detail"><small>{{ title }}</small>
          <template v-if="current[key]"><h3>{{ current[key]?.num }} · {{ current[key]?.name }}</h3>
            <p>{{ full(current[key]!.dt_start) }} — {{ full(current[key]!.dt_end) }}</p>
            <p v-if="current[key]?.sunset">Закат {{ hhmm(current[key]!.sunset!) }}</p>
            <p>{{ [current[key]?.paksha,current[key]?.type,current[key]?.quality].filter(Boolean).join(' · ') }}</p>
            <p>{{ description(key,current[key]!) }}</p>
            <details v-if="key === 'tithi' && (current[key]?.num === 3 || current[key]?.num === 18)" class="tithi-note">
              <summary>Как оценена Тритья</summary>
              <p>В нашем справочнике Тритья растущей Луны (Шукла, № 3) благоприятная. Тритья убывающей Луны (Кришна, № 18) переменная. При сверке сравнивайте номер титхи, пакшу и правило оценки.</p>
            </details>
          </template><p v-else>Интервал не определён</p>
        </section>
      </div>
    </template>
    <button v-if="mobile" class="track-toggle" :aria-expanded="showChart" @click="showChart = !showChart">{{ showChart ? 'Свернуть карту D1' : 'Показать карту D1' }}</button>
    <section v-if="(!mobile || showChart) && dayMinutes > 0">
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
.pd{color:var(--ink);font:15px/1.45 system-ui,sans-serif}.heading,.buttons,.toolbar,.windows,.prefs{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.heading{justify-content:space-between}.heading h1{font-size:clamp(28px,4vw,43px);letter-spacing:-.045em}.heading p,.detail small{color:var(--muted)}.heading p,.detail p{margin:.35rem 0}.pd button,.pd input,.pd select{color:inherit;font:inherit}.pd button,.pd input{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:7px 11px}.pd button{cursor:pointer}.pd button:hover,.pd button.chosen{background:var(--accent-soft)}.buttons button:first-child{background:#166047;color:white}.toolbar{margin:22px 0 12px}.toolbar label{margin-left:auto}.panel{background:var(--surface);border:1px solid var(--line);border-radius:12px}.prefs,.month{padding:15px;margin-top:12px}.prefs input{max-width:130px}.month{max-width:340px}.monthgrid{display:grid;grid-template-columns:repeat(7,1fr);gap:3px;margin-top:10px;text-align:center}.monthgrid button{padding:5px}.scroll{overflow:auto}.scale{min-width:770px;padding:14px 16px}.track{display:grid;grid-template-columns:112px 1fr;align-items:stretch}.track>b{font-size:12px;align-self:center}.axis{display:flex;justify-content:space-between;color:#61767a;font-size:11px}.axis span{width:4.1667%}.rail{height:33px;position:relative;background:repeating-linear-gradient(90deg,#dce4e2 0 1px,transparent 1px 4.16667%);cursor:crosshair}.bar{box-sizing:border-box;position:absolute;top:2px;bottom:2px;border:1px solid white;border-radius:6px;padding:3px;overflow:hidden;white-space:nowrap;color:#263e48;font-size:13px;text-align:center}.bar.stop{border-bottom:3px solid #bd5554}.track:has(.bar small) .rail{height:49px}.bar small{display:block;font-size:10px}.moment{color:var(--muted)}.rail i{position:absolute;top:0;bottom:0;width:2px;background:#13694e;pointer-events:none}.windows{margin:11px 0;color:var(--muted);gap:22px}.pd h2{margin:26px 0 10px;font-size:21px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px}.detail{padding:13px}.detail h3{margin:4px 0;font-size:18px}.detail p{font-size:13px}.positions{display:grid;grid-template-columns:minmax(230px,1fr) 2fr;gap:14px}.positions table{width:100%;min-width:520px;border-collapse:collapse}.positions td,.positions th{padding:7px;text-align:left;border-bottom:1px solid #e0e6e6}.pd [role=alert]{color:#993f32}@media(max-width:720px){.positions{grid-template-columns:1fr}.toolbar label{margin-left:0}.heading{align-items:flex-start}.cards{grid-template-columns:repeat(auto-fit,minmax(145px,1fr))}}

.share { display: grid; gap: 4px; margin-top: 12px; }
.overview { padding: 14px; margin-bottom: 14px; background: var(--surface-2); }
.overview h2 { margin: 0 0 10px; }
.overview dl { display: grid; grid-template-columns: repeat(auto-fit, minmax(125px, 1fr)); gap: 10px; margin: 0; }
.overview dt { font-size: 12px; color: var(--muted); }
.overview dd { margin: 0; }
.overview dd:first-of-type { font-weight: 700; }
.overview dd + dd { font-size: 12px; }
.next { display: flex; align-items: center; flex-wrap: wrap; gap: 8px 12px; margin-top: 13px; padding-top: 10px; border-top: 1px solid var(--line); }
.next p { margin: 0; }
.minute-slider { display: flex; align-items: center; gap: 10px; margin: 8px 0; }
.pd input[type="range"] { accent-color: #166047; width: min(100%, 320px); padding: 0; }
.scale { position: relative; --track-label-width: 112px; }
.track { grid-template-columns: var(--track-label-width) 1fr; }
.track > b { position: sticky; left: 0; z-index: 4; background: var(--surface); padding: 4px; align-self: stretch; display: grid; align-items: center; }
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

.axis { position: relative; min-height: 17px; }
.axis span { position: absolute; }
.rail { background-size: calc(100% * 60 / v-bind(dayMinutes)) 100%; background-image: linear-gradient(to right,#dce4e2 1px,transparent 1px); }
.calculation-note { padding: 12px; margin: 10px 0; }
.calculation-note summary, .tithi-note summary { color: var(--accent-ink); cursor: pointer; }
.calculation-note dl { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 6px 12px; max-width: 480px; }
.calculation-note dd { margin: 0; font-variant-numeric: tabular-nums; }
.calculation-note p { margin-bottom: 0; }
.tithi-note { margin-top: 8px; font-size: 13px; }
.day-events { margin-bottom: 14px; }
.day-events summary { cursor: pointer; color: #166047; padding: 12px 14px; }
.day-events ol { list-style: none; margin: 0; padding: 0 10px 10px; }
.day-events li { display: flex; align-items: flex-start; gap: 12px; border-top: 1px solid var(--line); padding: 8px 4px; }
.day-events li.upcoming { background: var(--accent-soft); }
.day-events li button { flex: 0 0 auto; font-variant-numeric: tabular-nums; }
.day-events li span, .day-events li small { display: block; }
.day-events li small { color: var(--accent-ink); }
.clock-choice { display: block; margin-bottom: 8px; }
</style>
