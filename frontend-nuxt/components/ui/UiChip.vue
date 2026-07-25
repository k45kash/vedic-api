<script setup lang="ts">
/**
 * Чип-статус (.chip) — «✓ хороший день», «Благоприятная» и т. п.
 *
 * props: variant ('good' | 'bad' | 'neutral'), label, icon
 * слоты: default
 */
import type { IconName } from '../../utils/icons'

withDefaults(defineProps<{
  variant?: 'good' | 'bad' | 'neutral'
  label?: string
  /** Иконка слева от текста. */
  icon?: IconName
}>(), {
  variant: 'neutral',
})
</script>

<template>
  <span class="chip" :class="`chip--${variant}`">
    <UiIcon v-if="icon" :name="icon" style="width:12px;height:12px" />
    <slot>{{ label }}</slot>
  </span>
</template>
