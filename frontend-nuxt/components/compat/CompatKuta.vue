<script setup lang="ts">
/**
 * Одна кута в разборе: балл, что она означает, из чего сложилась и где школы
 * расходятся.
 *
 * Три источника текста, и они намеренно разделены — читатель должен видеть,
 * что откуда:
 *   • «Что это» — статья из content/glossary.json словами автора базы.
 *     Для Вашьи, Граха-майтри и Бхакута статьи в глоссарии нет — тогда блока
 *     нет вовсе, а не выдуманное описание.
 *   • «Как считается» — пересказ алгоритма из calculators/kuta.ts (MECHANICS).
 *   • «Из чего сложилось» — строка `note`, которую вернул сам расчёт.
 *
 * Оговорка `school` (расхождение школ) показывается ВСЕГДА, а не под режимом
 * «Астролог»: прятать её было бы выдачей одного варианта за канон.
 */
import type { KutaFactor } from '~/composables/useJyotish'
import { MECHANICS, KUTA_METHOD_NOTE, KUTA_NO, fmtScore } from './types'

const props = defineProps<{
  factor: KutaFactor
  /** Статья глоссария: { intro, terms } — уже найденная страницей. */
  glossary?: { intro?: string; terms?: Array<{ t: string; d: string }> } | null
}>()

/** Доля заполнения шкалы. Это не «процент совместимости», а ровно балл
 *  относительно максимума самой куты — то, что вернул расчёт. */
const ratio = computed(() => {
  const s = props.factor.score
  if (s === null || !props.factor.max) return 0
  return Math.max(0, Math.min(1, s / props.factor.max))
})

const noteId = computed(() => KUTA_METHOD_NOTE[props.factor.key])
const no = computed(() => KUTA_NO[props.factor.key])
const mech = computed(() => MECHANICS[props.factor.key])

/** Доша — не «плохо», а повод разобраться: помечаем золотом, не красным. */
const isDosha = computed(() => !!props.factor.dosha)
</script>

<template>
  <div class="ck" :class="{ 'ck--dosha': isDosha }">
    <div class="ck__head">
      <span class="ck__no" aria-hidden="true">{{ no }}</span>
      <h3 class="ck__name">{{ factor.label }}</h3>
      <span class="ck__score">
        <b>{{ fmtScore(factor.score) }}</b> из {{ factor.max }}
      </span>
    </div>

    <div
      class="ck__bar"
      role="meter"
      :aria-valuenow="factor.score ?? 0"
      :aria-valuemin="0"
      :aria-valuemax="factor.max"
      :aria-label="`${factor.label}: ${fmtScore(factor.score)} из ${factor.max}`"
    >
      <span class="ck__fill" :style="{ width: `${ratio * 100}%` }" />
    </div>

    <p class="ck__note">{{ factor.note }}</p>

    <p v-if="glossary?.intro" class="ck__what">
      <b>Что это.</b> {{ glossary.intro }}
    </p>
    <p v-for="term in glossary?.terms || []" :key="term.t" class="ck__term">
      <b>{{ term.t }}.</b> {{ term.d }}
    </p>

    <p class="ck__mech"><b>Как считается.</b> {{ mech }}</p>

    <p v-if="!glossary?.intro" class="hint ck__gap">
      Отдельной статьи об этой куте в справочнике нет — показан только способ расчёта.
    </p>

    <div v-if="factor.school" class="ck__school">
      <UiIcon name="info" />
      <span><b>Школы расходятся.</b> {{ factor.school }}</span>
    </div>

    <div v-if="noteId" class="ck__pin">
      <UiMethodNote :id="noteId" />
    </div>
  </div>
</template>
