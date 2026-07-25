<script setup lang="ts">
/**
 * Блок «Важно знать сегодня» из макета: строки «иконка + название + время
 * + подпись». Тон намеренно мягкий — это предостережение, а не запрет.
 *
 * props: items — массив { name, time, note, icon, tone }
 * слоты: default (вместо списка)
 */
import type { IconName } from '../../utils/icons'

interface WarnItem {
  /** Название периода, напр. «Раху-кала». */
  name: string
  /** Интервал, напр. «12:01 – 13:31». */
  time?: string
  /** Короткая подпись, напр. «Не начинайте важные дела». */
  note?: string
  icon?: IconName
  /** Окраска кружка с иконкой. */
  tone?: 'bad' | 'gold' | 'neutral' | 'good'
}

withDefaults(defineProps<{ items?: WarnItem[] }>(), {
  items: () => [],
})
</script>

<template>
  <div class="wlist">
    <slot>
      <div
        v-for="item in items"
        :key="item.name"
        class="wlist__row"
        :class="item.tone && item.tone !== 'bad' ? `wlist__row--${item.tone}` : null"
      >
        <span class="wlist__ic" aria-hidden="true">
          <UiIcon :name="item.icon || 'alert'" />
        </span>
        <div>
          <div class="wlist__name">{{ item.name }}</div>
          <div v-if="item.note" class="wlist__note">{{ item.note }}</div>
        </div>
        <div v-if="item.time" class="wlist__time">{{ item.time }}</div>
      </div>
    </slot>
  </div>
</template>
