<script setup lang="ts">
/**
 * Линейная иконка из общего набора (utils/icons.ts).
 * Размер задаётся снаружи через CSS родителя, поэтому существующие правила
 * (.nav__item svg, .rlist svg, .iconbtn svg …) работают без изменений.
 *
 * props: name — ключ иконки, width — толщина обводки
 */
import { ICONS, type IconName } from '../../utils/icons'

const props = withDefaults(defineProps<{
  name: IconName
  width?: number | string
}>(), {
  width: 1.6,
})

const paths = computed(() => ICONS[props.name] ?? '')
</script>

<template>
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    :stroke-width="width"
    aria-hidden="true"
    focusable="false"
    v-html="paths"
  />
</template>
