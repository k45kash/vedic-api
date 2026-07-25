<script setup lang="ts">
/**
 * Кнопка (.btn / .btn--ghost). С `to` рендерится как NuxtLink, иначе — <button>.
 *
 * props: variant ('solid' | 'ghost'), to, type, disabled, icon
 * слоты: default
 */
import type { IconName } from '../../utils/icons'

withDefaults(defineProps<{
  variant?: 'solid' | 'ghost'
  /** Маршрут — тогда это ссылка, а не кнопка. */
  to?: string
  type?: 'button' | 'submit'
  disabled?: boolean
  icon?: IconName
}>(), {
  variant: 'solid',
  type: 'button',
})
</script>

<template>
  <component
    :is="to ? resolveComponent('NuxtLink') : 'button'"
    class="btn"
    :class="{ 'btn--ghost': variant === 'ghost' }"
    :to="to"
    :type="to ? undefined : type"
    :disabled="to ? undefined : disabled"
  >
    <UiIcon v-if="icon" :name="icon" style="width:15px;height:15px" />
    <slot />
  </component>
</template>
