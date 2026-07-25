<script setup lang="ts">
/**
 * Плитка-показатель из прототипа (.tile): метка, значение, подпись, глиф.
 *
 * props: label, value, meta, glyph
 * слоты: default (вместо value), meta, glyph
 */
defineProps<{
  /** Верхняя серая метка, напр. «Восходящий знак». */
  label?: string
  /** Крупное значение (серифом). */
  value?: string | number
  /** Подпись под значением, напр. «лагна». */
  meta?: string
  /** Символ в правом верхнем углу, напр. «♍︎». */
  glyph?: string
}>()
</script>

<template>
  <div class="tile">
    <div v-if="label" class="tile__label">{{ label }}</div>
    <div class="tile__value">
      <slot>{{ value }}</slot>
    </div>
    <div v-if="meta || $slots.meta" class="tile__meta">
      <slot name="meta">{{ meta }}</slot>
    </div>
    <div v-if="glyph || $slots.glyph" class="tile__glyph" aria-hidden="true">
      <slot name="glyph">{{ glyph }}</slot>
    </div>
  </div>
</template>
