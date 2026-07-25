<script setup lang="ts">
/**
 * Список «Астрологическая причина дня» из макета: маркер (галочка,
 * восклицание, инфо) плюс объяснение, почему день сложился именно так.
 *
 * props: items — массив { text, tone }
 * слоты: default (вместо списка)
 */
type ReasonTone = 'good' | 'warn' | 'info' | 'bad'

interface ReasonItem {
  text: string
  tone?: ReasonTone
}

withDefaults(defineProps<{ items?: ReasonItem[] }>(), {
  items: () => [],
})

// Маркер подбираем по тону: галочка / восклицание / инфо.
const MARK = {
  good: 'check-circle',
  warn: 'warn',
  bad: 'alert',
  info: 'info',
} as const
</script>

<template>
  <ul class="rlist">
    <slot>
      <li v-for="(item, i) in items" :key="i">
        <UiIcon
          :name="MARK[item.tone || 'info']"
          class="rlist__m"
          :class="`rlist__m--${item.tone || 'info'}`"
        />
        <span>{{ item.text }}</span>
      </li>
    </slot>
  </ul>
</template>
