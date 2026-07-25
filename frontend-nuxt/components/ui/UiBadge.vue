<script setup lang="ts">
/**
 * Золотой бейдж (.badge), напр. «☾ управитель Луна».
 *
 * props: icon, label
 * слоты: default
 */
import type { IconName } from '../../utils/icons'

defineProps<{
  icon?: IconName
  label?: string
}>()
</script>

<template>
  <span class="badge">
    <UiIcon v-if="icon" :name="icon" :width="1.5" />
    <slot>{{ label }}</slot>
  </span>
</template>
