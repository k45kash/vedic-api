<script setup lang="ts">
/**
 * Герой накшатры (.hero): номер, название, транслитерация и градусы,
 * бейдж управителя, шакти и мета-строка.
 *
 * props: no, name, sub, shakti, meta
 * слоты: badge, default (шакти), meta, footer
 */
defineProps<{
  /** Номер накшатры, напр. «04». */
  no?: string | number
  /** Название, напр. «Рохини». */
  name?: string
  /** Строка под названием: транслитерация, перевод, градусы. */
  sub?: string
  /** Шакти — сила накшатры. */
  shakti?: string
  /** Мета-строка внизу (лагна, пада, гана, цель). */
  meta?: string
}>()
</script>

<template>
  <div class="hero">
    <div v-if="no !== undefined && no !== null" class="hero__no">{{ no }}</div>
    <div>
      <h2 class="hero__name">{{ name }}</h2>
      <div v-if="sub" class="hero__dev">{{ sub }}</div>
      <slot name="badge" />
      <p v-if="shakti || $slots.default" class="shakti">
        <slot>{{ shakti }}</slot>
      </p>
      <div v-if="meta || $slots.meta" class="metaline">
        <slot name="meta">{{ meta }}</slot>
      </div>
      <div v-if="$slots.footer" style="margin-top:13px"><slot name="footer" /></div>
    </div>
  </div>
</template>
