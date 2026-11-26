<script setup lang="ts">
import type { PositionMode } from '~/composables/useBirthForm'

const mode = defineModel<PositionMode>({ required: true })
defineProps<{ disabled?: boolean }>()
</script>

<template>
  <div class="field">
    <label>
      Положения планет
      <select v-model="mode" :disabled="disabled">
        <option value="apparent">Видимые (по умолчанию)</option>
        <option value="geometric">Истинные геометрические</option>
      </select>
    </label>
    <small v-if="mode === 'apparent'">
      Направление, с которого приходит свет планеты. Расчёт учитывает время пути света.
    </small>
    <small v-else>
      Направление от Земли к планете в выбранный момент. Вблизи границы время смены титхи или накшатры может отличаться.
    </small>
  </div>
</template>
