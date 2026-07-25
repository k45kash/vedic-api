<script setup lang="ts">
/**
 * Строка «ключ — значение» (.kv). Из таких строк собрана панчанга дня.
 *
 * props: k, v, tone ('good' | 'bad')
 * слоты: default (значение), key (ключ)
 */
defineProps<{
  /** Название показателя. */
  k?: string
  /** Значение. */
  v?: string | number
  /** Смысловая окраска значения. */
  tone?: 'good' | 'bad'
}>()
</script>

<template>
  <div class="kv">
    <span class="kv__k"><slot name="key">{{ k }}</slot></span>
    <span class="kv__v" :class="tone === 'good' ? 'txt-good' : tone === 'bad' ? 'txt-bad' : null">
      <slot>{{ v }}</slot>
    </span>
  </div>
</template>
