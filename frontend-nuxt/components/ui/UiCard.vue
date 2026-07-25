<script setup lang="ts">
/**
 * Карточка (.card) с необязательной шапкой (.card__head).
 *
 * props: title, subtitle, linkText, linkTo, note, flat, variant
 * слоты: head (вся шапка целиком), actions (правая часть шапки), default
 */
withDefaults(defineProps<{
  /** Заголовок карточки. */
  title?: string
  /** Пояснение под заголовком (макет: «Астрологические показатели дня…»). */
  subtitle?: string
  /** Текст ссылки справа в шапке. */
  linkText?: string
  /** Куда ведёт ссылка. Без него ссылка не рендерится. */
  linkTo?: string
  /** Серая подпись справа в шапке, напр. «пять элементов». */
  note?: string
  /** Без тени. */
  flat?: boolean
  /** 'mantra' — золотая карточка-мантра. */
  variant?: 'default' | 'mantra'
  /** Уровень заголовка: h2 по умолчанию. */
  headingLevel?: 2 | 3
}>(), {
  variant: 'default',
  headingLevel: 2,
})
</script>

<template>
  <div class="card" :class="[{ 'card--flat': flat }, variant === 'mantra' && 'mantra']">
    <div
      v-if="$slots.head || title"
      class="card__head"
      :class="{ 'card__head--stack': !!subtitle }"
    >
      <slot name="head">
        <div>
          <component :is="`h${headingLevel}`" class="card__title">{{ title }}</component>
          <div v-if="subtitle" class="card__sub">{{ subtitle }}</div>
        </div>
        <span v-if="note" class="hint" style="margin-left:auto">{{ note }}</span>
        <NuxtLink v-if="linkText && linkTo" class="card__link" :to="linkTo">{{ linkText }}</NuxtLink>
        <slot name="actions" />
      </slot>
    </div>
    <slot />
  </div>
</template>
