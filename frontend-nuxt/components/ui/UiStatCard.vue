<script setup lang="ts">
/**
 * Богатая карточка-показатель из макета concepte.png: номерной бейдж,
 * крупный глиф, значение, «до 15:27», персональная оценка «Для вас: 8/10»,
 * чип статуса, список «Подходит для:» и ссылка «Подробнее».
 * Существующий UiTile остаётся — он для компактного верхнего ряда.
 *
 * props: no, label, glyph, icon, value, until, score, scoreMax, chip,
 *        chipVariant, text, listTitle, list, moreText, moreTo, highlight
 * слоты: glyph, default (свободный текст), chip, more
 */
import type { IconName } from '../../utils/icons'

const props = withDefaults(defineProps<{
  /** Порядковый номер в кружке слева. */
  no?: string | number
  /** Название показателя, напр. «Титхи». */
  label?: string
  /** Текстовый символ по центру, напр. «☾︎». */
  glyph?: string
  /** Либо иконка из набора вместо символа. */
  icon?: IconName
  /** Значение показателя, напр. «Шукла Дашами». */
  value?: string
  /** Подпись «до 15:27». */
  until?: string
  /** Персональная оценка 0–10; null — строку не показываем. */
  score?: number | null
  scoreMax?: number
  /** Текст чипа статуса, напр. «Благоприятная». */
  chip?: string
  chipVariant?: 'good' | 'bad' | 'neutral'
  /** Свободный поясняющий текст. */
  text?: string
  /** Заголовок списка, напр. «Подходит для:». */
  listTitle?: string
  /** Пункты списка с галочками. */
  list?: string[]
  moreText?: string
  moreTo?: string
  /** Выделенная карточка — золотая рамка и мягкий фон. */
  highlight?: boolean
}>(), {
  scoreMax: 10,
  chipVariant: 'good',
  moreText: 'Подробнее',
})

// Цвет оценки: та же логика, что у полосок-рейтингов.
const scoreTone = computed(() => {
  if (props.score === null || props.score === undefined) return null
  const ratio = props.score / props.scoreMax
  if (ratio >= 0.7) return ''
  if (ratio >= 0.5) return 'statcard__score--mid'
  return 'statcard__score--low'
})
</script>

<template>
  <div class="statcard" :class="{ 'statcard--hl': highlight }">
    <div class="statcard__head">
      <span v-if="no !== undefined && no !== null" class="statcard__no" aria-hidden="true">{{ no }}</span>
      <span class="statcard__label">{{ label }}</span>
    </div>

    <div v-if="glyph || icon || $slots.glyph" class="statcard__glyph" aria-hidden="true">
      <slot name="glyph">
        <UiIcon v-if="icon" :name="icon" :width="1.3" />
        <template v-else>{{ glyph }}</template>
      </slot>
    </div>

    <div v-if="value" class="statcard__value">{{ value }}</div>
    <div v-if="until" class="statcard__until">{{ until }}</div>

    <div v-if="score !== null && score !== undefined" class="statcard__score" :class="scoreTone">
      Для вас: <b>{{ score }}/{{ scoreMax }}</b>
    </div>

    <div v-if="chip || $slots.chip" class="statcard__chips">
      <slot name="chip">
        <UiChip :variant="chipVariant">{{ chip }}</UiChip>
      </slot>
    </div>

    <p v-if="text" class="statcard__text">{{ text }}</p>
    <slot />

    <div v-if="listTitle" class="statcard__listhead">{{ listTitle }}</div>
    <ul v-if="list && list.length" class="statcard__list">
      <li v-for="item in list" :key="item">
        <UiIcon name="check" :width="2.2" />
        <span>{{ item }}</span>
      </li>
    </ul>

    <div v-if="moreTo || $slots.more" class="statcard__more">
      <slot name="more">
        <NuxtLink :to="moreTo">{{ moreText }}</NuxtLink>
      </slot>
    </div>
  </div>
</template>
