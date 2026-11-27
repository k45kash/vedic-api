<script setup lang="ts">
import type { TaraGoal } from '~/calculators/tara-windows'

defineProps<{ goal: TaraGoal }>()
</script>

<template>
  <details class="tara-coverage" :open="goal.missing ? true : undefined">
    <summary>Что учитывает расчёт</summary>
    <p>
      <strong>Учитываются</strong> Тара-бала по вашему профилю, Раху-кала, Бхадра,
      предупреждения для 22-й и 27-й позиций и для Абхиджит в среду.
      Абхиджит также отмечается в пояснениях к старту.
    </p>
    <p v-if="goal.taras && goal.missing"><strong>Ориентир по Тара-бале</strong> · {{ goal.reason }}. Используется общая трактовка из справочника.</p>
    <p v-if="!goal.taras"><strong>Обзор условий</strong> показывает тару и предупреждения. Отдельной оценки пригодности для этого события пока нет.</p>
    <p><strong>Чего не хватает</strong></p>
    <p v-if="goal.missing">{{ goal.missing }}</p>
    <p>Титхи и йога в оценке конкретного времени сейчас не участвуют.</p>
  </details>
</template>

<style scoped>
.tara-coverage { margin: 8px 0; font-size: 14px; }
.tara-coverage summary { cursor: pointer; color: var(--accent-ink); }
.tara-coverage p { margin: 6px 0; }
</style>
