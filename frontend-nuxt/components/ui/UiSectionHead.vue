<script setup lang="ts">
/**
 * Заголовок секции (.sechead) с необязательной меткой-флажком (.flag),
 * например «Карта домов [Астролог]».
 *
 * props: title, flag
 * слоты: default (вместо title), flag
 */
defineProps<{
  title?: string
  /** Текст плашки справа от заголовка. */
  flag?: string
}>()
</script>

<template>
  <div class="sechead">
    <slot>{{ title }}</slot>
    <span v-if="flag || $slots.flag" class="flag"><slot name="flag">{{ flag }}</slot></span>
  </div>
</template>
