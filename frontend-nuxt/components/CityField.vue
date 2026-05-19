<script setup lang="ts">
// Поле города с автодополнением через Nominatim.
// Двусторонне связано с lat/lon/tz/city в родительском state через v-model:lat / :lon / :tz / :city.
// При выборе города или изменении props.date дёргает /api/tz и подставляет
// исторически корректный offset с поправкой на DST/декретное время.
const props = defineProps<{
  lat: number
  lon: number
  tz: number
  city: string
  /** YYYY-MM-DD; нужна, чтобы /api/tz отдал offset для исторической даты */
  date: string
  /** HH:mm; влияет на ambiguous-time около переводов часов */
  time?: string
}>()

const emit = defineEmits<{
  'update:lat':  [v: number]
  'update:lon':  [v: number]
  'update:tz':   [v: number]
  'update:city': [v: string]
}>()

const { base: apiBase } = useApi()

const dropdown = ref<Array<{ lat: string; lon: string; name: string; sub: string }>>([])
const open = ref(false)
const tzHint = ref('')
const tzWarn = ref(false)

let searchTimer: ReturnType<typeof setTimeout> | undefined

async function onInput(e: Event) {
  const q = (e.target as HTMLInputElement).value
  emit('update:city', q)
  if (searchTimer) clearTimeout(searchTimer)
  if (q.trim().length < 2) { open.value = false; return }
  searchTimer = setTimeout(() => searchCity(q.trim()), 400)
}

async function searchCity(q: string) {
  try {
    const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=json&limit=5&addressdetails=1`
    const data = await (await fetch(url, { headers: { 'Accept-Language': 'ru' } })).json() as any[]
    dropdown.value = data.map(it => ({
      lat:  it.lat,
      lon:  it.lon,
      name: it.name || (it.display_name as string).split(',')[0],
      sub:  (it.display_name as string).split(',').slice(1, 3).join(',').trim(),
    }))
    open.value = dropdown.value.length > 0
  } catch {
    open.value = false
  }
}

function pickCity(item: { lat: string; lon: string; name: string }) {
  emit('update:lat',  parseFloat(parseFloat(item.lat).toFixed(4)))
  emit('update:lon',  parseFloat(parseFloat(item.lon).toFixed(4)))
  emit('update:city', item.name)
  open.value = false
  // refreshTz сработает через watch на lat/lon/date
}

async function refreshTz() {
  if (!props.lat || !props.lon || !props.date) return
  const [y, m, d] = props.date.split('-').map(Number)
  const [hh, mm]  = (props.time || '12:00').split(':').map(Number)
  tzWarn.value = false
  tzHint.value = 'Определяем часовой пояс…'
  try {
    const url = `${apiBase}/api/tz?lat=${props.lat}&lon=${props.lon}&year=${y}&month=${m}&day=${d}&hour=${hh}&minute=${mm}`
    const r = await fetch(url)
    if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`)
    const dto = await r.json()
    emit('update:tz', dto.offset_hours)
    const dst = dto.is_dst ? ' · летнее время' : ''
    tzHint.value = `${dto.tz_name} → ${dto.offset_str}${dst}`
  } catch (e: any) {
    tzWarn.value = true
    tzHint.value = 'Не удалось определить TZ: ' + e.message
  }
}

// Любое изменение координат или даты → пересчёт tz.
watch(() => [props.lat, props.lon, props.date, props.time], refreshTz, { immediate: true })

function closeDropdown(e: Event) {
  if (!(e.target as HTMLElement).closest('.city-wrap')) open.value = false
}
onMounted(() => document.addEventListener('click', closeDropdown))
onBeforeUnmount(() => document.removeEventListener('click', closeDropdown))
</script>

<template>
  <div class="field field--city">
    <label>Город</label>
    <div class="city-wrap">
      <input
        type="text"
        class="city-input"
        autocomplete="off"
        placeholder="Москва, Мумбаи, Нью-Йорк…"
        :value="city"
        @input="onInput"
        @keydown.escape="open = false"
      />
      <ul class="city-dropdown" :class="{ open }">
        <li v-for="(it, i) in dropdown" :key="i" @click="pickCity(it)">
          <div class="city-name">{{ it.name }}</div>
          <div class="city-sub">{{ it.sub }}</div>
        </li>
      </ul>
      <div class="tz-hint" :class="{ warn: tzWarn }">{{ tzHint }}</div>
    </div>
  </div>
</template>

<style scoped>
.field--city { flex: 1 1 100%; max-width: 100%; width: 100%; }
.city-wrap { position: relative; width: 100%; }

.city-input {
  width: 100%;
  padding: 10px 14px;
  border-radius: 10px;
  border: none;
  background: #f5f5f7;
  font-size: 15px;
  font-family: inherit;
  color: #1d1d1f;
  outline: none;
  transition: box-shadow 0.15s;
}
.city-input:focus { box-shadow: 0 0 0 3px rgba(0,113,227,0.25); }

.city-dropdown {
  display: none;
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
  list-style: none;
  overflow: hidden;
  z-index: 50;
}
.city-dropdown.open { display: block; }
.city-dropdown li {
  padding: 11px 14px;
  font-size: 14px;
  cursor: pointer;
  color: #1d1d1f;
}
.city-dropdown li + li { border-top: 1px solid #e8e8ed; }
.city-dropdown li:hover { background: #f5f5f7; }
.city-dropdown li .city-name { font-weight: 500; }
.city-dropdown li .city-sub { color: #6e6e73; font-size: 12px; margin-top: 2px; }

.tz-hint {
  font-size: 12px;
  color: #6e6e73;
  margin-top: 6px;
  min-height: 1em;
}
.tz-hint.warn { color: #c08a30; }

label { font-size: 13px; font-weight: 500; color: #6e6e73; display: block; margin-bottom: 6px; }
</style>
