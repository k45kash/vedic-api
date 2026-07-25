<script setup lang="ts">
/**
 * Мягкое пояснение (.disc) или предупреждение (.warn).
 * Тон намеренно некатегоричный: это ориентир, а не запрет и не диагноз.
 *
 * Два способа задать текст:
 *   • слот или props.text — контекстная формулировка самой страницы;
 *   • props.entry — готовая запись из content/disclaimers.json. Тогда рядом
 *     встаёт метка достоверности («классика» / «школы расходятся» /
 *     «реконструкция»), чтобы читатель понимал, на чём стоит текст.
 *
 * Метку ставим ТОЛЬКО у записей из content: у них тип задан автором. Своим
 * формулировкам тип не приписываем — это было бы выдумкой.
 *
 * props: tone ('soft' | 'warn'), icon, text, entry
 * слоты: default
 */
import type { IconName } from '../../utils/icons'
import type { DisclaimerEntry } from '../../composables/useContentTexts'

const props = withDefaults(defineProps<{
  /** 'soft' — серая сноска внизу страницы, 'warn' — розовая плашка. */
  tone?: 'soft' | 'warn'
  /** Своя иконка вместо стандартной. */
  icon?: IconName
  text?: string
  /** Запись из content/disclaimers.json (см. useDisclaimers). */
  entry?: DisclaimerEntry | null
}>(), {
  tone: 'soft',
})

const slots = useSlots()

const iconName = computed<IconName>(() => props.icon ?? (props.tone === 'warn' ? 'warn' : 'alert'))
const body = computed(() => props.entry?.text || props.text || '')
/** Пока справочник не приехал (entry === null), блок не рисуем вовсе. */
const visible = computed(() => !!body.value || !!slots.default)
</script>

<template>
  <component
    :is="tone === 'warn' ? 'div' : 'p'"
    v-if="visible"
    :class="tone === 'warn' ? 'warn' : 'disc'"
  >
    <UiIcon :name="iconName" />
    <span>
      <span
        v-if="entry"
        class="disc__mark"
        :class="`disc__mark--${entry.kind}`"
        :title="entry.meaning"
      >{{ entry.mark }}</span>
      <slot>{{ body }}</slot>
    </span>
  </component>
</template>
