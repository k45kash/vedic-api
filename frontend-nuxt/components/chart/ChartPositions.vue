<script setup lang="ts">
/**
 * Таблица положений: планета → знак → дом → накшатра → пада → достоинство.
 *
 * Колонки «градус», «управитель накшатры» и «скорость» видны только в режиме
 * «Астролог» — как и везде, через класс `.pro-cell`, а не через v-if: так
 * переключение режима не перестраивает таблицу.
 *
 * Дом показывается, только если он вообще осмыслен (`show-house`): при
 * неизвестном времени рождения дома недостоверны, и колонка исчезает целиком,
 * а не заполняется прочерками, которые читаются как «данных нет по планете».
 */

import type { PositionRow } from './types'

defineProps<{
  rows: PositionRow[]
  showHouse?: boolean
  /** Подпись колонки дома: «Дом» или «Дом от Луны». */
  houseLabel?: string
}>()

const DIGNITY_SHORT = { exalted: 'ex', own: 'own', debilitated: 'deb' } as const
const DIGNITY_RU = { exalted: 'экзальтация', own: 'свой знак', debilitated: 'падение' } as const
</script>

<template>
  <div class="ptable__scroll">
    <table class="ptable">
      <thead>
        <tr>
          <th scope="col">Планета</th>
          <th scope="col">Знак</th>
          <th scope="col" class="pro-cell">Градус</th>
          <th v-if="showHouse" scope="col">{{ houseLabel || 'Дом' }}</th>
          <th scope="col">Накшатра</th>
          <th scope="col">Пада</th>
          <th scope="col" class="pro-cell">Упр. накшатры</th>
          <th scope="col">Достоинство</th>
          <th scope="col">Движение</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.planet">
          <th scope="row">
            <span class="ptable__glyph" aria-hidden="true">{{ r.glyph }}</span>{{ r.planet }}
          </th>
          <td>{{ r.signRu }}</td>
          <td class="pro-cell ptable__num">{{ r.degDms }}</td>
          <td v-if="showHouse">{{ r.house ?? '—' }}</td>
          <td>{{ r.nakshatra }}</td>
          <td class="ptable__num">{{ r.pada }}</td>
          <td class="pro-cell">{{ r.nakLord }}</td>
          <td>
            <span
              v-if="r.dignity"
              class="dig"
              :class="`dig--${DIGNITY_SHORT[r.dignity]}`"
            >{{ DIGNITY_RU[r.dignity] }}</span>
            <span v-else class="ptable__dash">—</span>
          </td>
          <td>
            <template v-if="r.retro">
              <span class="ptable__retro">℞ вакри</span>
            </template>
            <template v-else>
              <span class="ptable__dash">директно</span>
            </template>
            <span v-if="r.stationary" class="ptable__stat">станция</span>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
