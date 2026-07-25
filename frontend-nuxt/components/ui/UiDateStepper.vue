<script setup lang="ts">
/**
 * Простой степпер даты из прототипа (.dstep): ‹ дата ›.
 * Для шапки кабинета есть более богатый UiDateNav (по макету).
 *
 * props: label
 * события: prev, next
 */
defineProps<{ label?: string }>()
defineEmits<{ prev: []; next: [] }>()
</script>

<template>
  <div class="dstep">
    <button type="button" aria-label="Предыдущий день" @click="$emit('prev')">‹</button>
    <span>{{ label }}</span>
    <button type="button" aria-label="Следующий день" @click="$emit('next')">›</button>
  </div>
</template>
