<script setup lang="ts">
/**
 * Мягкое пояснение (.disc) или предупреждение (.warn).
 * Тон намеренно некатегоричный: это ориентир, а не запрет и не диагноз.
 *
 * props: tone ('soft' | 'warn'), icon, text
 * слоты: default
 */
import type { IconName } from '../../utils/icons'

const props = withDefaults(defineProps<{
  /** 'soft' — серая сноска внизу страницы, 'warn' — розовая плашка. */
  tone?: 'soft' | 'warn'
  /** Своя иконка вместо стандартной. */
  icon?: IconName
  text?: string
}>(), {
  tone: 'soft',
})

const iconName = computed<IconName>(() => props.icon ?? (props.tone === 'warn' ? 'warn' : 'alert'))
</script>

<template>
  <component :is="tone === 'warn' ? 'div' : 'p'" :class="tone === 'warn' ? 'warn' : 'disc'">
    <UiIcon :name="iconName" />
    <span><slot>{{ text }}</slot></span>
  </component>
</template>
