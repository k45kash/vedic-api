<script setup lang="ts">
/**
 * Навигатор даты из макета: ‹ | «Сегодня, 25 июля 2026» | календарь | ›
 * Живёт в центре шапки кабинета, пригодится на вкладке «Сегодня».
 *
 * props: label, pickable (показывать кнопку календаря)
 * события: prev, next, pick
 */
withDefaults(defineProps<{
  /** Подпись, напр. «Сегодня, 25 июля 2026». */
  label?: string
  pickable?: boolean
}>(), {
  pickable: true,
})

defineEmits<{ prev: []; next: []; pick: [] }>()
</script>

<template>
  <div class="datenav">
    <button type="button" aria-label="Предыдущий день" @click="$emit('prev')">
      <UiIcon name="chevron-left" />
    </button>
    <span class="datenav__label">{{ label }}</span>
    <button v-if="pickable" type="button" aria-label="Выбрать дату" @click="$emit('pick')">
      <UiIcon name="calendar" />
    </button>
    <button type="button" aria-label="Следующий день" @click="$emit('next')">
      <UiIcon name="chevron-right" />
    </button>
  </div>
</template>
