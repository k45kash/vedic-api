<script setup lang="ts">
/**
 * Наватара-чакра — 27 накшатр, разложенные от Джанмы по девяти тарам
 * в три цикла (Джанмаркша 1–9, Кармаркша 10–18, Адханаркша 19–27).
 *
 * Данные целиком приходят из `calculators/tara.ts` → `taraChakra(janmaNo)`:
 * компонент ничего не считает, только раскладывает 27 клеток по сетке 9×3
 * и подсвечивает две из них — Джанму (позиция 1) и накшатру Луны сегодня,
 * если она известна. Не известна — подсветки просто нет.
 *
 * Тары 3 (Випат), 5 (Пратьяри) и 7 (Наидхана) ослабевают от цикла к циклу —
 * это метод школы, он подписан в легенде, а не подан как канон. Правило
 * 27-й накшатры помечено пометкой А8 (см. utils/method-notes.ts).
 */
import type { TaraChakraCell } from '~/composables/useJyotish'

const props = defineProps<{
  cells: TaraChakraCell[]
  /** Номер джанма-накшатры 1..27 — подпись под таблицей. */
  janmaName: string
  /** Накшатра Луны сегодня, 1..27. null — не запрашивали или не удалось. */
  todayNo?: number | null
  /** Название накшатры дня — для подписи под таблицей. */
  todayName?: string
  /** Накшатра Луны при рождении под вопросом (граница / неизвестное время). */
  janmaUncertain?: boolean
}>()

/** Заголовок сетки: девять тар в порядке от Джанмы. Берём из первых девяти
 * клеток — отдельного справочника для этого не нужно. */
const heads = computed(() =>
  props.cells.slice(0, 9).map((c) => ({
    n: c.taraN,
    name: c.taraName,
    quality: c.quality,
    dana: c.dana,
  })),
)

/** Три цикла по девять клеток. */
const CYCLE_LABEL = ['Джанмаркша', 'Кармаркша', 'Адханаркша'] as const
const CYCLE_RANGE = ['1–9', '10–18', '19–27'] as const

const rows = computed(() =>
  [1, 2, 3].map((g) => ({
    group: g,
    label: CYCLE_LABEL[g - 1],
    range: CYCLE_RANGE[g - 1],
    cells: props.cells.filter((c) => c.group === g),
  })),
)

const isToday = (c: TaraChakraCell) => !!props.todayNo && c.nakNo === props.todayNo
const isJanma = (c: TaraChakraCell) => c.pos === 1

/** Позиция накшатры дня от Джанмы — её же показывает тара-бала на «Сегодня». */
const todayCell = computed(() =>
  props.todayNo ? props.cells.find((c) => c.nakNo === props.todayNo) ?? null : null,
)
</script>

<template>
  <div class="nav9">
    <div class="nav9__scroll">
      <table class="nav9__t">
        <caption class="sr-only">
          Наватара-чакра: 27 накшатр от джанма-накшатры {{ janmaName }},
          девять тар в три цикла
        </caption>
        <thead>
          <tr>
            <th scope="col" class="nav9__corner">Цикл</th>
            <th
              v-for="h in heads"
              :key="h.n"
              scope="col"
              class="nav9__head"
              :class="`is-${h.quality}`"
            >
              <span class="nav9__headno">{{ h.n }}</span>
              {{ h.name }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.group">
            <th scope="row" class="nav9__cycle">
              {{ r.label }}
              <span class="nav9__range">{{ r.range }}</span>
            </th>
            <td
              v-for="c in r.cells"
              :key="c.pos"
              class="nav9__cell"
              :class="[
                `is-${c.quality}`,
                { 'is-janma': isJanma(c), 'is-today': isToday(c), 'is-avoid': c.schoolAvoid },
              ]"
            >
              <div class="nav9__nak">{{ c.nakName }}</div>
              <div class="nav9__meta">
                {{ c.pos }} · {{ c.ruler }}
              </div>
              <div v-if="isJanma(c) || isToday(c) || c.schoolAvoid" class="nav9__marks">
                <span v-if="isJanma(c)" class="nav9__mark nav9__mark--janma">Джанма</span>
                <span v-if="isToday(c)" class="nav9__mark nav9__mark--today">Луна сегодня</span>
                <span v-if="c.schoolAvoid" class="nav9__mark nav9__mark--avoid">27-я</span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p class="nav9__note">
      Отсчёт от вашей джанма-накшатры <b>{{ janmaName }}</b> — она стоит первой
      клеткой (тара Джанма).
      <template v-if="todayCell">
        Сегодня Луна идёт по накшатре <b>{{ todayName || todayCell.nakName }}</b> —
        это {{ todayCell.pos }}-я от Джанмы, тара «{{ todayCell.taraName }}»
        ({{ CYCLE_LABEL[todayCell.group - 1] }}).
      </template>
      <template v-else>
        Накшатра Луны на сегодня не запрашивалась — подсветки текущей клетки нет.
      </template>
    </p>

    <p v-if="janmaUncertain" class="nav9__note nav9__note--warn">
      Джанма-накшатра под вопросом (см. предупреждение выше) — вместе с ней
      сдвигается и вся чакра: она строится именно от неё.
    </p>

    <div class="nav9__legend">
      <div v-for="h in heads" :key="h.n" class="nav9__leg" :class="`is-${h.quality}`">
        <span class="nav9__legname">{{ h.n }}. {{ h.name }}</span>
        <span class="nav9__legdana">дана: {{ h.dana }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.nav9__scroll {
  overflow-x: auto;
  /* На узком экране таблица не ломается, а прокручивается: 27 клеток
     иначе схлопнутся в нечитаемые столбики. */
  -webkit-overflow-scrolling: touch;
}

.nav9__t {
  border-collapse: separate;
  border-spacing: 5px;
  /* Хватает на самые длинные названия («Пурва Бхадрапада») без наложения
     соседних клеток; уже этого таблица прокручивается внутри .nav9__scroll. */
  min-width: 980px;
  table-layout: fixed;
  width: 100%;
}

.nav9__corner {
  width: 96px;
  font-size: 11px;
  font-weight: 500;
  color: var(--muted);
  text-align: left;
  vertical-align: bottom;
  padding: 0 4px 4px;
}

.nav9__head {
  padding: 6px 5px;
  border-radius: var(--r-sm);
  background: var(--surface-2);
  border: 1px solid var(--line);
  font-size: 11.5px;
  font-weight: 500;
  color: var(--body);
  line-height: 1.25;
  text-align: center;
}
.nav9__head.is-good { border-color: var(--good-line); background: var(--good-soft); color: var(--good); }
.nav9__head.is-bad { border-color: var(--bad-line); background: var(--bad-soft); color: var(--bad); }

.nav9__headno {
  display: block;
  font-size: 10px;
  color: var(--muted);
}

.nav9__cycle {
  font-size: 11.5px;
  font-weight: 500;
  color: var(--body);
  text-align: left;
  vertical-align: middle;
  padding: 0 4px;
  line-height: 1.3;
}

.nav9__range {
  display: block;
  font-size: 10.5px;
  color: var(--muted);
}

.nav9__cell {
  padding: 8px 6px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  text-align: center;
  vertical-align: top;
}
.nav9__cell.is-good { border-color: var(--good-line); background: var(--good-soft); }
.nav9__cell.is-bad { border-color: var(--bad-line); background: var(--bad-soft); }

.nav9__cell.is-janma { outline: 2px solid var(--accent); outline-offset: -2px; }
.nav9__cell.is-today { outline: 2px solid var(--gold); outline-offset: -2px; }
.nav9__cell.is-avoid { border-style: dashed; }

.nav9__nak {
  font-family: var(--serif);
  font-size: 13.5px;
  color: var(--ink);
  line-height: 1.2;
  overflow-wrap: anywhere;
}

.nav9__meta {
  margin-top: 3px;
  font-size: 10.5px;
  color: var(--muted);
}

.nav9__marks {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 3px;
  margin-top: 5px;
}

.nav9__mark {
  padding: 1px 6px;
  border-radius: var(--r-pill);
  font-size: 9.5px;
  letter-spacing: .02em;
  white-space: nowrap;
}
.nav9__mark--janma { background: var(--accent-soft); color: var(--accent-ink); }
.nav9__mark--today { background: var(--gold-soft); color: var(--gold-ink); }
.nav9__mark--avoid { background: var(--surface-3); color: var(--muted); }

.nav9__note {
  margin: 14px 0 0;
  font-size: 13px;
  line-height: 1.55;
  color: var(--body);
}
.nav9__note b { color: var(--ink); font-weight: 600; }
.nav9__note--warn { color: var(--muted); }

.nav9__legend {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 6px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--line);
}

.nav9__leg {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding: 6px 9px;
  border-left: 3px solid var(--line-2);
  font-size: 11.5px;
  color: var(--muted);
}
.nav9__leg.is-good { border-left-color: var(--good); }
.nav9__leg.is-bad { border-left-color: var(--bad); }

.nav9__legname { color: var(--ink); font-size: 12.5px; }
.nav9__legdana { line-height: 1.35; }
</style>
