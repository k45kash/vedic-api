<script setup lang="ts">
/**
 * Карточка мантры (.card.mantra): деванагари, IAST-транслитерация, пояснение.
 *
 * props: title, devanagari, translit, note
 */
defineProps<{
  /** Заголовок карточки, необязателен. */
  title?: string
  /** Мантра деванагари. */
  devanagari?: string
  /** Транслитерация IAST. */
  translit?: string
  /** Пояснение по-русски. */
  note?: string
}>()
</script>

<template>
  <div class="card mantra">
    <div v-if="title" class="card__head">
      <h3 class="card__title" style="margin:0 auto">{{ title }}</h3>
    </div>
    <div class="mantra__dn">{{ devanagari }}</div>
    <div v-if="translit" class="mantra__ia">{{ translit }}</div>
    <div v-if="note" class="mantra__ru">{{ note }}</div>
    <slot />
  </div>
</template>
