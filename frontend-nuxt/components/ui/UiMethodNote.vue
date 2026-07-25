<script setup lang="ts">
/**
 * Пометка спорной методики прямо на странице.
 *
 * Свёрнутая — маленький значок рядом с заголовком раздела, чтобы не шуметь.
 * Развёрнутая — что сделано сейчас и что нужно от астролога.
 *
 * Текст берётся из реестра `utils/method-notes.ts` по идентификатору, который
 * совпадает с пунктом в `docs/ASTROLOGER-REVIEW.md`. Своими словами тут писать
 * нечего: реестр — единственный источник правды.
 *
 * <UiMethodNote id="А1" />          — значок, раскрывается по клику
 * <UiMethodNote id="А5" expanded /> — сразу развёрнутая плашка
 */
import { methodNote, NOTE_KIND_LABEL } from '../../utils/method-notes'

const props = withDefaults(defineProps<{
  id: string
  /** Показать развёрнутой сразу. */
  expanded?: boolean
}>(), {
  expanded: false,
})

const note = computed(() => methodNote(props.id))
const open = ref(props.expanded)

const kindLabel = computed(() => (note.value ? NOTE_KIND_LABEL[note.value.kind] : ''))
</script>

<template>
  <span v-if="note" class="mnote" :class="[`mnote--${note.kind}`, { 'is-open': open }]">
    <button
      type="button"
      class="mnote__pin"
      :aria-expanded="open"
      :title="`${note.id}. ${note.title}`"
      @click="open = !open"
    >
      <UiIcon :name="note.kind === 'gap' ? 'alert' : 'info'" />
      <span class="mnote__id">{{ note.id }}</span>
      <span class="mnote__kind">{{ kindLabel }}</span>
    </button>

    <span v-if="open" class="mnote__body">
      <span class="mnote__title">{{ note.title }}</span>
      <span class="mnote__row"><b>Сейчас:</b> {{ note.current }}</span>
      <span v-if="note.ask" class="mnote__row mnote__row--ask"><b>На согласовании:</b> {{ note.ask }}</span>
    </span>
  </span>
</template>
