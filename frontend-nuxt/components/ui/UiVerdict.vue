<script setup lang="ts">
/**
 * Вердикт дня (.verdict): крупная оценка слева, текст и пояснения справа.
 *
 * props: score, tone ('good' | 'bad' | 'neutral'), text, note
 * слоты: default (текст вердикта), note (пояснение), chip
 */
withDefaults(defineProps<{
  /** Оценка в квадрате слева. */
  score?: string | number
  tone?: 'good' | 'bad' | 'neutral'
  /** Основная строка вердикта. */
  text?: string
  /** Пояснение под вердиктом. */
  note?: string
}>(), {
  tone: 'good',
})
</script>

<template>
  <div class="verdict">
    <div
      class="verdict__score"
      :class="tone === 'bad' ? 'verdict__score--bad' : tone === 'neutral' ? 'verdict__score--neutral' : null"
    >
      <slot name="score">{{ score }}</slot>
    </div>
    <div>
      <div class="verdict__text">
        <slot>{{ text }}</slot>
        <slot name="chip" />
      </div>
      <p v-if="note || $slots.note" style="margin:7px 0 0;font-size:14px">
        <slot name="note">{{ note }}</slot>
      </p>
      <slot name="extra" />
    </div>
  </div>
</template>
