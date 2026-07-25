<script setup lang="ts">
// Форма ввода/редактирования постоянного профиля рождения (новый кабинет).
// Город, координаты и часовой пояс — переиспользованный CityField.vue
// (автодополнение Nominatim + /api/tz с поправкой на исторический DST).
//
// Вёрстка намеренно минимальная, на глобальных классах из layouts/default.vue
// (.birth / .row / .field / button.primary) — дизайн накладывает другой агент.
import { emptyBirthProfile, type BirthProfile } from '~/composables/useBirthProfile'

const props = withDefaults(defineProps<{
  submitLabel?: string
  /** Показывать поле имени (для приветствия). */
  withName?: boolean
}>(), { submitLabel: 'Сохранить и рассчитать', withName: true })

const emit = defineEmits<{ saved: [profile: BirthProfile] }>()

const { profile, loading, error, saveProfile, fetchHoroscope } = useBirthProfile()

// Локальная копия: правки не должны менять сохранённый профиль до сабмита
// (иначе кэш гороскопа сбрасывался бы на каждый набранный символ).
const form = reactive<BirthProfile>({ ...emptyBirthProfile(), ...(profile.value || {}) })

// Профиль мог восстановиться из localStorage уже после монтирования формы.
watch(profile, (p) => { if (p) Object.assign(form, p) }, { immediate: true })

// Время неизвестно → поле времени гасим, для /api/tz подставляем полдень.
const effectiveTime = computed(() => (form.timeUnknown ? '12:00' : form.time))

async function onSubmit() {
  saveProfile({ ...form })
  await fetchHoroscope()
  if (!error.value) emit('saved', { ...form })
}
</script>

<template>
  <form class="birth" @submit.prevent="onSubmit">
    <div v-if="props.withName" class="row">
      <div class="field">
        <label>Имя (необязательно)</label>
        <input type="text" v-model="form.name" placeholder="Как к вам обращаться" />
      </div>
    </div>

    <div class="row">
      <div class="field">
        <label>Дата рождения</label>
        <input type="date" v-model="form.date" required />
      </div>
      <div class="field">
        <label>Время рождения</label>
        <input
          type="time"
          v-model="form.time"
          :disabled="form.timeUnknown"
          :required="!form.timeUnknown"
        />
      </div>
    </div>

    <div class="row">
      <label class="check">
        <input type="checkbox" v-model="form.timeUnknown" />
        <span>Время рождения неизвестно</span>
      </label>
    </div>

    <p v-if="form.timeUnknown" class="note">
      Расчёт пойдёт «по Луне»: за точку берём полдень. Накшатра Луны и панчанга
      останутся рабочими, но <strong>лагна (асцендент) и дома будут недоступны</strong> —
      за сутки асцендент проходит все 12 знаков. Накшатра Луны тоже может оказаться
      пограничной: покажем предупреждение, если попадёте на стык.
    </p>

    <div class="row">
      <CityField
        v-model:city="form.city"
        v-model:lat="form.lat"
        v-model:lon="form.lon"
        v-model:tz="form.tz"
        :date="form.date"
        :time="effectiveTime"
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

    <p v-if="error" class="error">Ошибка: {{ error }}</p>

    <button type="submit" class="primary" :disabled="loading">
      {{ loading ? 'Считаем…' : props.submitLabel }}
    </button>
  </form>
</template>

<style scoped>
/* Только то, чего нет в глобальных стилях layouts/default.vue. */
.check { display: flex; align-items: center; gap: 8px; font-size: 14px; cursor: pointer; }
.check input { width: 16px; height: 16px; }
.note { font-size: 13px; line-height: 1.5; color: #6e6e73; }
.field input:disabled { opacity: 0.45; cursor: not-allowed; }
</style>
