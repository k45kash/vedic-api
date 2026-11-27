<script setup lang="ts">
import type { BirthForm as BirthFormState } from '~/composables/useBirthForm'

defineProps<{
  form: BirthFormState
  submitLabel?: string
  submitting?: boolean
}>()

const fieldId = useId()

const emit = defineEmits<{ submit: [] }>()
</script>

<template>
  <form class="birth" @submit.prevent="emit('submit')">
    <div class="row">
      <div class="field">
        <label :for="`${fieldId}-date`">Дата рождения</label>
        <input :id="`${fieldId}-date`" type="date" v-model="form.date" required />
      </div>
      <div class="field">
        <label :for="`${fieldId}-time`">Время</label>
        <input :id="`${fieldId}-time`" type="time" v-model="form.time" required />
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
        <label :for="`${fieldId}-lat`">Широта</label>
        <input :id="`${fieldId}-lat`" type="number" v-model.number="form.lat" step="0.0001" required />
      </div>
      <div class="field">
        <label :for="`${fieldId}-lon`">Долгота</label>
        <input :id="`${fieldId}-lon`" type="number" v-model.number="form.lon" step="0.0001" required />
      </div>
      <div class="field">
        <label :for="`${fieldId}-tz`">UTC ±, ч</label>
        <input :id="`${fieldId}-tz`" type="number" v-model.number="form.tz" step="any" required />
      </div>
    </div>

    <PositionModeField v-model="form.position_mode" :disabled="submitting" />
    <button type="submit" class="primary" :disabled="submitting">
      {{ submitLabel || 'Рассчитать' }}
    </button>
  </form>
</template>
