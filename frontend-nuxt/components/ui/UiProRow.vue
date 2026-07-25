<script setup lang="ts">
/**
 * Строка планеты (.prow): глиф, название, позиция, достоинство, описание.
 *
 * Флаг `pro` делает строку видимой только в режиме «Астролог» — точно так же,
 * как `.prow.pro` в прототипе (класс .is-pro на корне раскладки).
 *
 * props: name, glyph, position, dignity, dignityLabel, desc, pro
 * слоты: default (описание), position
 */
defineProps<{
  /** Название планеты. */
  name?: string
  /** Символ планеты, напр. «☉︎». */
  glyph?: string
  /** Позиция: «9-й дом · Телец». */
  position?: string
  /** Достоинство: экзальтация / свой знак / падение. */
  dignity?: 'ex' | 'own' | 'deb' | null
  /** Подпись достоинства; по умолчанию — стандартная для типа. */
  dignityLabel?: string
  /** Толкование справа. */
  desc?: string
  /** Показывать только в режиме «Астролог». */
  pro?: boolean
}>()

const DIGNITY_RU: Record<string, string> = {
  ex: 'экзальтация',
  own: 'свой знак',
  deb: 'падение',
}
</script>

<template>
  <div class="prow" :class="{ pro }">
    <div>
      <div class="prow__name">
        <span v-if="glyph" class="prow__glyph" aria-hidden="true">{{ glyph }}</span>{{ name }}
      </div>
      <div v-if="position || $slots.position" class="prow__pos">
        <slot name="position">{{ position }}</slot>
        <span v-if="dignity" class="dig" :class="`dig--${dignity}`">
          {{ dignityLabel || DIGNITY_RU[dignity] }}
        </span>
      </div>
    </div>
    <div class="prow__desc"><slot>{{ desc }}</slot></div>
  </div>
</template>
