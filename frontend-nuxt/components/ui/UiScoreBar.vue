<script setup lang="ts">
/**
 * Полоска-рейтинг из макета: иконка, название сферы, шкала и «9 / 10».
 * Цвет заливки зависит от значения (зелёный / оранжевый / красный).
 *
 * props: icon, label, value, max
 */
import type { IconName } from '../../utils/icons'

const props = withDefaults(defineProps<{
  icon?: IconName
  /** Название сферы, напр. «Работа». */
  label?: string
  /** Значение оценки. */
  value: number
  max?: number
}>(), {
  max: 10,
})

const ratio = computed(() => Math.max(0, Math.min(1, props.value / props.max)))
const toneClass = computed(() =>
  ratio.value >= 0.7 ? '' : ratio.value >= 0.5 ? 'scorebar__fill--mid' : 'scorebar__fill--low',
)
</script>

<template>
  <div
    class="scorebar"
    role="meter"
    :aria-valuenow="value"
    :aria-valuemin="0"
    :aria-valuemax="max"
    :aria-label="label"
  >
    <UiIcon v-if="icon" :name="icon" class="scorebar__icon" />
    <span class="scorebar__label">{{ label }}</span>
    <span class="scorebar__track">
      <span class="scorebar__fill" :class="toneClass" :style="{ width: `${ratio * 100}%` }" />
    </span>
    <span class="scorebar__val">{{ value }} / {{ max }}</span>
  </div>
</template>
