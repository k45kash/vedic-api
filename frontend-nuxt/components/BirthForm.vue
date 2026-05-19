<script setup lang="ts">
import type { BirthForm as BirthFormState } from '~/composables/useBirthForm'

defineProps<{
  form: BirthFormState
  submitLabel?: string
  submitting?: boolean
}>()

const emit = defineEmits<{ submit: [] }>()
</script>

<template>
  <form class="birth" @submit.prevent="emit('submit')">
    <div class="row">
      <div class="field">
        <label>Дата рождения</label>
        <input type="date" v-model="form.date" required />
      </div>
      <div class="field">
        <label>Время</label>
        <input type="time" v-model="form.time" required />
      </div>
    </div>

    <div class="row">
      <CityField
        v-model:city="form.city"
        v-model:lat="form.lat"
        v-model:lon="form.lon"
        v-model:tz="form.tz"
        :date="form.date"
        :time="form.time"
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

    <button type="submit" class="primary" :disabled="submitting">
      {{ submitLabel || 'Рассчитать' }}
    </button>
  </form>
</template>
