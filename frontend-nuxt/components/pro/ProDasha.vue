<script setup lang="ts">
/**
 * Текущий период Вимшоттари: маха-даша и антар-даша.
 *
 * Границы периодов считает бэкенд (`vimshottari.py`, приходит в
 * `/api/horoscope` полем `dasha_current`) — здесь ни одной даты не
 * вычисляется. Трактовки берутся из `content/yogakarma.json`
 * (`dashas` + `antardashas`) через `calculators/drishti.ts`.
 *
 * Полоса — доля прошедшего времени периода, то есть факт календаря,
 * а не оценка «насколько период хорош»: числовых оценок у сервиса нет
 * (пометка Б6).
 *
 * Длина года в расчёте — 365,25 суток; это развилка школ, поэтому рядом
 * стоит пометка А3.
 */
import type { DashaReading } from '~/composables/useJyotish'

/** Один период из `dasha_current` (ровно те поля, что отдаёт API).
 * Тип локальный: `<script setup>` не умеет экспортировать, а странице
 * достаточно структурной совместимости. */
interface DashaPeriod {
  lord: string
  lord_id: string
  dt_start: string
  dt_end: string
  duration_years: number
  progress: number
  years_remaining: number
  days_remaining: number
}

const props = defineProps<{
  maha: DashaPeriod | null
  antar: DashaPeriod | null
  reading: DashaReading | null
  /** Момент, на который бэкенд определил текущий период. */
  asOf?: string
  /** Трактовки недостоверны, если недостоверна накшатра Луны. */
  moonUncertain?: boolean
}>()

const MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']

/** «2010-06-09T11:27:52» → «9 июня 2010». Время периода не показываем:
 * минуты здесь мнимая точность — они зависят от времени рождения. */
function fmtDate(iso: string): string {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`
}

/** «1 г 10 мес» — остаток периода словами. */
function remaining(p: DashaPeriod): string {
  const days = Math.max(0, Math.round(p.days_remaining))
  if (days < 60) return `${days} дн.`
  const years = Math.floor(days / 365.25)
  const months = Math.round((days - years * 365.25) / 30.44)
  const parts: string[] = []
  if (years) parts.push(`${years} г.`)
  if (months) parts.push(`${months} мес.`)
  return parts.join(' ') || `${days} дн.`
}

const pct = (p: DashaPeriod) => Math.round(Math.min(1, Math.max(0, p.progress)) * 100)

const label = computed(() =>
  [props.maha?.lord, props.antar?.lord].filter(Boolean).join(' / '))
</script>

<template>
  <div v-if="maha" class="dsh">
    <div class="dsh__head">
      <span class="dsh__label">{{ label }}</span>
      <span class="dsh__cap">маха-даша / антар-даша сейчас</span>
    </div>

    <div class="dsh__p">
      <div class="dsh__prow">
        <span class="dsh__pname">Маха-даша {{ maha.lord }}</span>
        <span class="dsh__pdates">
          {{ fmtDate(maha.dt_start) }} — {{ fmtDate(maha.dt_end) }} ·
          {{ maha.duration_years }} лет
        </span>
      </div>
      <div class="dsh__bar"><span class="dsh__fill" :style="{ width: pct(maha) + '%' }" /></div>
      <div class="dsh__prog">пройдено {{ pct(maha) }}% · осталось {{ remaining(maha) }}</div>
      <p v-if="reading?.maha" class="dsh__text">{{ reading.maha.desc }}</p>
    </div>

    <div v-if="antar" class="dsh__p">
      <div class="dsh__prow">
        <span class="dsh__pname">Антар-даша {{ antar.lord }}</span>
        <span class="dsh__pdates">
          {{ fmtDate(antar.dt_start) }} — {{ fmtDate(antar.dt_end) }}
        </span>
      </div>
      <div class="dsh__bar"><span class="dsh__fill dsh__fill--sub" :style="{ width: pct(antar) + '%' }" /></div>
      <div class="dsh__prog">пройдено {{ pct(antar) }}% · осталось {{ remaining(antar) }}</div>
      <p v-if="reading?.antar" class="dsh__text">{{ reading.antar.text }}</p>
      <p v-if="reading?.antar?.relLabel" class="dsh__rel">
        Связь планет периода и подпериода: {{ reading.antar.relLabel }}.
      </p>
    </div>

    <p v-if="moonUncertain" class="dsh__note">
      Даши отсчитываются от накшатры Луны при рождении, а она здесь под
      вопросом (см. предупреждение выше) — вместе с ней смещаются и границы
      всех периодов.
    </p>
    <p v-if="asOf" class="dsh__note">
      Период определён на {{ fmtDate(asOf) }} — при следующем расчёте он
      обновится сам.
    </p>
  </div>
</template>

<style scoped>
.dsh__head {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 10px;
}

.dsh__label {
  font-family: var(--serif);
  font-size: 21px;
  color: var(--ink);
}

.dsh__cap {
  font-size: 12.5px;
  color: var(--muted);
}

.dsh__p {
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}

.dsh__prow {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 10px;
}

.dsh__pname {
  font-size: 14.5px;
  color: var(--ink);
  font-weight: 500;
}

.dsh__pdates {
  font-size: 12.5px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.dsh__bar {
  margin-top: 9px;
  height: 5px;
  border-radius: var(--r-pill);
  background: var(--surface-3);
  overflow: hidden;
}

.dsh__fill {
  display: block;
  height: 100%;
  border-radius: var(--r-pill);
  background: var(--accent);
}
.dsh__fill--sub { background: var(--gold); }

.dsh__prog {
  margin-top: 5px;
  font-size: 12px;
  color: var(--muted);
}

.dsh__text {
  margin: 11px 0 0;
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--body);
}

.dsh__rel {
  margin: 7px 0 0;
  font-size: 12.5px;
  color: var(--muted);
}

.dsh__note {
  margin: 12px 0 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--muted);
}
</style>
