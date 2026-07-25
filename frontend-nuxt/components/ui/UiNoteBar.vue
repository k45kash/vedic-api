<script setup lang="ts">
/**
 * Нижняя поясняющая плашка на всю ширину (макет): что учтено в расчёте
 * и когда данные обновлялись.
 *
 * props: text, updated
 * слоты: default
 */
import type { IconName } from '../../utils/icons'

withDefaults(defineProps<{
  text?: string
  /** Время обновления, напр. «25 июля 2026, 10:30». */
  updated?: string
  icon?: IconName
}>(), {
  icon: 'sparkle',
})
</script>

<template>
  <div class="notebar">
    <UiIcon :name="icon" />
    <span><slot>{{ text }}</slot></span>
    <span v-if="updated" class="notebar__upd">
      Обновлено: {{ updated }}
      <UiIcon name="refresh" />
    </span>
  </div>
</template>
