<script setup lang="ts">
/**
 * Блок локации из макета: булавка, город и локальное время расчёта.
 *
 * props: city, time
 */
defineProps<{
  /** Город расчёта, напр. «Москва, Россия». */
  city?: string
  /** Дата и время, напр. «25 июля 2026, 10:30». */
  time?: string
}>()
</script>

<template>
  <div class="place">
    <UiIcon name="pin" />
    <div>
      <div class="place__city">{{ city }}</div>
      <div v-if="time" class="place__time">{{ time }}</div>
    </div>
  </div>
</template>
