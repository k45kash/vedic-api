<script setup lang="ts">
import { eventRuleForGoal, type TaraGoal } from '~/calculators/tara-windows'

const props = defineProps<{ goal: TaraGoal }>()
const rule = computed(() => eventRuleForGoal(props.goal))
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
    <p v-if="!goal.taras"><strong>Обзор условий</strong> показывает тару и предупреждения. Персонального ориентира по Тара-бале для этой цели пока нет.</p>
    <p v-if="rule"><strong>Титхи и йога</strong> оцениваются по правилам события «{{ rule.name }}». Стоп-титхи исключает окно из подбора. В проверке выбранного времени она видна как предупреждение.</p>
    <p v-else>Действующие титхи и йога показаны для справки. Для оценки нужна методика этой цели.</p>
    <p v-if="goal.missing"><strong>Чего не хватает</strong></p>
    <p v-if="goal.missing">{{ goal.missing }}</p>

  </details>
</template>

<style scoped>
.tara-coverage { margin: 8px 0; font-size: 14px; }
.tara-coverage summary { cursor: pointer; color: var(--accent-ink); }
.tara-coverage p { margin: 6px 0; }
</style>
