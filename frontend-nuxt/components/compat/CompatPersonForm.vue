<script setup lang="ts">
/**
 * Ввод второго человека на экране «Совместимость».
 *
 * Два режима, потому что ашта-куте нужно разное:
 *   • «Данные рождения» — дата, время и место → POST /api/horoscope → накшатра
 *     Луны + раши + градус. Это единственный путь к полным 36 баллам.
 *   • «Известна только накшатра» — раши Луны нет, поэтому доступен лишь
 *     частичный расчёт на 21 балл (Гана, Йони, Тара, Нади). Так же вёл себя
 *     исходный калькулятор коллеги, и это честнее, чем угадывать знак.
 *
 * Компонент НЕ трогает постоянный профиль пользователя: партнёр нигде не
 * сохраняется, `useBirthProfile` здесь не используется вовсе. Поля рождения
 * повторяют BirthProfileForm.vue (тот жёстко связан с профилем и правкам
 * не подлежит), город/координаты/пояс — переиспользованный CityField.vue.
 */
import { nakLabel } from '~/composables/useJyotish'
import type { HoroscopeResult } from '~/composables/useBirthProfile'
import type { CompatPerson } from './types'

const props = withDefaults(defineProps<{
  /** Заголовок карточки: «Партнёр», «Вы». */
  title: string
  subtitle?: string
  /** Каким режимом открыться. */
  defaultMode?: 'birth' | 'nakshatra'
}>(), { defaultMode: 'birth' })

const emit = defineEmits<{ 'update:person': [p: CompatPerson | null] }>()

const api = useApi()

const mode = ref<'birth' | 'nakshatra'>(props.defaultMode)

// ─── Форма рождения ─────────────────────────────────────────────────────────

const form = reactive({
  date: '',
  time: '',
  timeUnknown: false,
  city: '',
  lat: 0,
  lon: 0,
  tz: 0,
})

/** Для /api/tz при неизвестном времени берём полдень — как в BirthProfileForm. */
const effectiveTime = computed(() => (form.timeUnknown ? '12:00' : form.time))

const nakNo = ref<number>(1)

const loading = ref(false)
const error = ref('')

/** Любая правка обнуляет результат: иначе на экране остался бы разбор,
 *  посчитанный по прежним данным. */
function invalidate() {
  emit('update:person', null)
  error.value = ''
}
watch(() => [mode.value, form.date, form.time, form.timeUnknown, form.lat, form.lon, form.tz, nakNo.value], invalidate)

const canSubmit = computed(() => {
  if (mode.value === 'nakshatra') return nakNo.value >= 1 && nakNo.value <= 27
  if (!form.date) return false
  if (!form.timeUnknown && !form.time) return false
  return Number.isFinite(form.lat) && Number.isFinite(form.lon) && Number.isFinite(form.tz)
})

const NAK_NUMBERS = Array.from({ length: 27 }, (_, i) => i + 1)

const MONTHS_RU = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
]

function birthLine(): string {
  const [y, m, d] = form.date.split('-').map(Number)
  const date = Number.isFinite(y) ? `${d} ${MONTHS_RU[(m || 1) - 1]} ${y}` : form.date
  const time = form.timeUnknown ? 'время неизвестно' : form.time
  return [[date, time].filter(Boolean).join(', '), form.city].filter(Boolean).join(' · ')
}

/** Ширина накшатры и максимальная суточная скорость Луны — те же значения,
 *  что в useBirthProfile.ts: одна карта, одна честность. */
const NAK_SIZE = 360 / 27
const MOON_MAX_DEG_PER_DAY = 15.4

async function submit() {
  if (mode.value === 'nakshatra') {
    emit('update:person', {
      nakNo: nakNo.value,
      moonSign: null,
      moonDeg: null,
      source: 'nakshatra',
      birthLine: '',
      timeUnknown: false,
      moonSignUncertain: false,
      nakUncertain: false,
    })
    return
  }

  loading.value = true
  error.value = ''
  try {
    const [y, m, d] = form.date.split('-').map(Number)
    const [hh, mm] = (form.timeUnknown ? '12:00' : form.time).split(':').map(Number)
    const res = await api.post<HoroscopeResult>('/api/horoscope', {
      year: y, month: m, day: d, hour: hh, minute: mm,
      tz: form.tz, lat: form.lat, lon: form.lon,
    })
    const moon = (res.planets ?? []).find((p) => p.name === 'Луна')

    // При неизвестном времени Луна за сутки проходит до 15,4°: окно ±7,7°
    // вокруг полудня почти всегда перекрывает границу накшатры (её ширина
    // 13°20′), а знак — только если Луна близко к его краю.
    const half = MOON_MAX_DEG_PER_DAY / 2
    const nakUncertain = form.timeUnknown
      ? Math.floor((res.moon_sid - half) / NAK_SIZE) !== Math.floor((res.moon_sid + half) / NAK_SIZE)
      : !!res.boundary?.is_boundary
        || res.boundary?.topo?.changes === true
        || res.boundary?.ayas_agree === false
    const moonSignUncertain = form.timeUnknown && !!moon
      && (moon.deg_in_sign < half || moon.deg_in_sign > 30 - half)

    emit('update:person', {
      nakNo: res.nk.num,
      moonSign: moon?.sign_num ?? null,
      moonDeg: moon?.deg_in_sign ?? null,
      source: 'birth',
      birthLine: birthLine(),
      timeUnknown: form.timeUnknown,
      moonSignUncertain,
      nakUncertain,
    })
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
    emit('update:person', null)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <UiCard :title="props.title" :subtitle="props.subtitle" :heading-level="3">
    <div class="seg cf-seg" role="group" aria-label="Что известно о человеке">
      <button
        type="button"
        :class="{ 'is-on': mode === 'birth' }"
        :aria-pressed="mode === 'birth'"
        @click="mode = 'birth'"
      >
        Данные рождения
      </button>
      <button
        type="button"
        :class="{ 'is-on': mode === 'nakshatra' }"
        :aria-pressed="mode === 'nakshatra'"
        @click="mode = 'nakshatra'"
      >
        Только накшатра
      </button>
    </div>

    <form class="cf-form" @submit.prevent="submit">
      <!-- ─── Полные данные рождения → 36 баллов ───────────────────────── -->
      <template v-if="mode === 'birth'">
        <div class="cf-row">
          <label class="cf-field">
            <span>Дата рождения</span>
            <input v-model="form.date" class="cf-input" type="date" required>
          </label>
          <label class="cf-field">
            <span>Время рождения</span>
            <input
              v-model="form.time"
              class="cf-input"
              type="time"
              :disabled="form.timeUnknown"
              :required="!form.timeUnknown"
            >
          </label>
        </div>

        <label class="cf-check">
          <input v-model="form.timeUnknown" type="checkbox">
          <span>Время рождения неизвестно</span>
        </label>

        <p v-if="form.timeUnknown" class="hint cf-note">
          Тогда считаем на полдень. Накшатра Луны за сутки успевает смениться,
          поэтому и накшатра, и — у края знака — раши могут оказаться другими.
          Что именно оказалось под вопросом, будет написано в разборе.
        </p>

        <div class="cf-city">
          <CityField
            v-model:city="form.city"
            v-model:lat="form.lat"
            v-model:lon="form.lon"
            v-model:tz="form.tz"
            :date="form.date"
            :time="effectiveTime"
          />
        </div>

        <div class="cf-row">
          <label class="cf-field">
            <span>Широта</span>
            <input v-model.number="form.lat" class="cf-input" type="number" step="0.0001" required>
          </label>
          <label class="cf-field">
            <span>Долгота</span>
            <input v-model.number="form.lon" class="cf-input" type="number" step="0.0001" required>
          </label>
          <label class="cf-field">
            <span>UTC ±, ч</span>
            <input v-model.number="form.tz" class="cf-input" type="number" step="0.5" required>
          </label>
        </div>
      </template>

      <!-- ─── Только накшатра → 21 балл ────────────────────────────────── -->
      <template v-else>
        <label class="cf-field">
          <span>Накшатра Луны</span>
          <select v-model.number="nakNo" class="cf-input">
            <option v-for="n in NAK_NUMBERS" :key="n" :value="n">{{ nakLabel(n) }}</option>
          </select>
        </label>
        <p class="hint cf-note">
          Без знака Луны (раши) четыре куты из восьми посчитать не из чего —
          Варна, Вашья, Граха-майтри и Бхакут. Останется частичный расчёт
          на 21 балл: Гана, Йони, Тара и Нади.
        </p>
      </template>

      <p v-if="error" class="cf-error">Не удалось посчитать: {{ error }}</p>

      <UiButton type="submit" :disabled="!canSubmit || loading">
        {{ loading ? 'Считаем…' : 'Применить' }}
      </UiButton>
    </form>
  </UiCard>
</template>

<style scoped>
.cf-seg { margin-bottom: 16px; }
.cf-form { display: flex; flex-direction: column; gap: 14px; }
.cf-row { display: flex; gap: 12px; flex-wrap: wrap; }
.cf-field { display: flex; flex-direction: column; gap: 6px; flex: 1; min-width: 132px; }
.cf-field > span { font-size: 12.5px; color: var(--muted); }
.cf-input {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  color: var(--ink);
  font: inherit;
  font-size: 14px;
  outline: none;
}
.cf-input:focus { border-color: var(--accent-line); }
.cf-input:disabled { opacity: .45; cursor: not-allowed; }
.cf-check { display: flex; align-items: center; gap: 8px; font-size: 13.5px; color: var(--body); cursor: pointer; }
.cf-check input { width: 15px; height: 15px; accent-color: var(--accent); cursor: pointer; }
.cf-note { margin: 0; }
.cf-error { margin: 0; font-size: 13px; color: var(--bad); }

/* CityField свёрстан на глобальных классах старой раскладки и на светлых
   константах — в кабинете его надо привести к токенам, не трогая сам файл
   (тот же приём, что у .profile-form на /me). */
.cf-city :deep(.field--city) { width: 100%; }
.cf-city :deep(label) { font-size: 12.5px; font-weight: 400; color: var(--muted); margin-bottom: 6px; }
.cf-city :deep(.city-input) {
  padding: 9px 12px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  color: var(--ink);
  font-size: 14px;
}
.cf-city :deep(.city-input:focus) { box-shadow: none; border-color: var(--accent-line); }
.cf-city :deep(.city-dropdown) {
  background: var(--surface);
  border: 1px solid var(--line);
  box-shadow: var(--sh-md);
}
.cf-city :deep(.city-dropdown li) { color: var(--ink); }
.cf-city :deep(.city-dropdown li + li) { border-top: 1px solid var(--line); }
.cf-city :deep(.city-dropdown li:hover) { background: var(--surface-3); }
.cf-city :deep(.city-dropdown li .city-sub) { color: var(--muted); }
.cf-city :deep(.tz-hint) { color: var(--muted); }
.cf-city :deep(.tz-hint.warn) { color: var(--gold-ink); }
</style>
