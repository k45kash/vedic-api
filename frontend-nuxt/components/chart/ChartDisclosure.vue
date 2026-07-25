<script setup lang="ts">
/**
 * Раскрывающийся блок трактовки.
 *
 * Намеренно на нативных <details>/<summary>: работает без JS, доступен с
 * клавиатуры и поиском по странице (Ctrl+F в Chrome раскрывает закрытые
 * details). Трактовок на карту приходится под три десятка — вываливать их
 * все сразу нельзя, страница перестаёт читаться.
 */
defineProps<{
  /** Заголовок строки: «5-й дом» / «Сатурн». */
  title: string
  /** Глиф слева, напр. «♄︎». */
  glyph?: string
  /** Серая приписка справа от заголовка. */
  meta?: string
  /** Чип-статус справа: достоинство, группа дома и т.п. */
  tag?: string
  tagTone?: 'good' | 'bad' | 'neutral'
  open?: boolean
}>()
</script>

<template>
  <details class="disc-item" :open="open">
    <summary class="disc-item__head">
      <span v-if="glyph" class="disc-item__glyph" aria-hidden="true">{{ glyph }}</span>
      <span class="disc-item__title">{{ title }}</span>
      <span v-if="meta" class="disc-item__meta">{{ meta }}</span>
      <span class="disc-item__spacer" />
      <UiChip v-if="tag" :variant="tagTone || 'neutral'" class="disc-item__tag">{{ tag }}</UiChip>
      <UiIcon name="chevron-down" class="disc-item__chev" />
    </summary>
    <div class="disc-item__body">
      <slot />
    </div>
  </details>
</template>
