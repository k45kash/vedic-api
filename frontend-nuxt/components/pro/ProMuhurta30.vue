<script setup lang="ts">
/**
 * 30 мухурт суток: 15 дневных (восход → закат) и 15 ночных (закат → восход).
 *
 * Времена берутся из `/api/panchang` (days[].muhurtas), описания — из
 * `content/muhurta30.json`; сшивает их `calculators/muhurta.ts` по номеру
 * мухурты. Сам компонент ничего не считает: он раскладывает готовые отрезки,
 * подсвечивает идущий сейчас и открывает разбор по клику.
 *
 * Две вещи показаны честно, а не приглажены:
 *   • дневная и ночная мухурта разной длины (летом ~66 и ~30 минут) — это
 *     следствие деления каждой половины суток на 15, а не ошибка;
 *   • имя из расчётного ядра отличается от имени контентной базы в 11
 *     позициях из 30 — там, где отличается, показаны оба.
 */
import type { DayMuhurta } from '~/composables/useJyotish'

const props = defineProps<{
  items: DayMuhurta[]
  /** Текущий момент — только если показаны сегодняшние сутки; иначе null. */
  now?: Date | null
}>()

const pad = (n: number) => String(n).padStart(2, '0')
const fmt = (d: Date) => `${pad(d.getHours())}:${pad(d.getMinutes())}`

const dayItems = computed(() => props.items.filter((m) => !m.night))
const nightItems = computed(() => props.items.filter((m) => m.night))

function isNow(m: DayMuhurta): boolean {
  const t = props.now
  return !!t && t >= m.start && t < m.end
}

/** Качество из таблицы расчётного ядра → тон карточки. */
function tone(q: string): 'good' | 'bad' | 'mixed' | 'neutral' {
  if (/неблаго/i.test(q)) return 'bad'
  if (/благоприятн/i.test(q)) return 'good'
  if (/смешан/i.test(q)) return 'mixed'
  return 'neutral'
}

/** Раскрытый разбор — номер мухурты или null. */
const openNo = ref<number | null>(null)
const open = computed(() => props.items.find((m) => m.n === openNo.value) ?? null)

function toggle(m: DayMuhurta) {
  openNo.value = openNo.value === m.n ? null : m.n
}

/** Сколько имён разошлось — показываем цифру, а не общие слова. */
const diffCount = computed(() => props.items.filter((m) => m.nameDiffers).length)
</script>

<template>
  <div class="m30">
    <div class="m30__half">
      <div class="m30__cap">
        Дневные · 15 мухурт
        <span v-if="dayItems.length" class="m30__caplen">
          по {{ dayItems[0].minutes }} мин
        </span>
      </div>
      <div class="m30__grid">
        <button
          v-for="m in dayItems"
          :key="m.n"
          type="button"
          class="m30__c"
          :class="[`is-${tone(m.quality)}`, {
            'is-now': isNow(m),
            'is-abhijit': m.abhijit,
            'is-open': openNo === m.n,
          }]"
          :aria-expanded="openNo === m.n"
          @click="toggle(m)"
        >
          <span class="m30__no">{{ m.n }}</span>
          <span class="m30__name">{{ m.name }}</span>
          <span class="m30__time">{{ fmt(m.start) }}–{{ fmt(m.end) }}</span>
          <span v-if="m.abhijit" class="m30__flag">Абхиджит</span>
          <span v-else-if="isNow(m)" class="m30__flag m30__flag--now">сейчас</span>
        </button>
      </div>
    </div>

    <div class="m30__half">
      <div class="m30__cap">
        Ночные · 15 мухурт
        <span v-if="nightItems.length" class="m30__caplen">
          по {{ nightItems[0].minutes }} мин
        </span>
      </div>
      <div class="m30__grid">
        <button
          v-for="m in nightItems"
          :key="m.n"
          type="button"
          class="m30__c"
          :class="[`is-${tone(m.quality)}`, { 'is-now': isNow(m), 'is-open': openNo === m.n }]"
          :aria-expanded="openNo === m.n"
          @click="toggle(m)"
        >
          <span class="m30__no">{{ m.n }}</span>
          <span class="m30__name">{{ m.name }}</span>
          <span class="m30__time">{{ fmt(m.start) }}–{{ fmt(m.end) }}</span>
          <span v-if="isNow(m)" class="m30__flag m30__flag--now">сейчас</span>
        </button>
      </div>
    </div>

    <!-- ─── Разбор выбранной мухурты ────────────────────────────────────── -->
    <div v-if="open" class="m30__det">
      <div class="m30__dethead">
        <span class="m30__detname">
          {{ open.n }}. {{ open.name }}
          <span v-if="open.skt" class="m30__skt">{{ open.skt }}</span>
        </span>
        <span class="m30__dettime">
          {{ fmt(open.start) }}–{{ fmt(open.end) }} · {{ open.minutes }} мин ·
          {{ open.night ? 'ночная' : 'дневная' }}
        </span>
        <UiChip :variant="tone(open.quality) === 'bad' ? 'bad' : tone(open.quality) === 'good' ? 'good' : 'neutral'">
          {{ open.quality }}
        </UiChip>
      </div>

      <UiKv k="Владыка" :v="open.lord" />
      <UiKv k="Тема" :v="open.theme" />

      <p class="m30__p">{{ open.meaning }}</p>
      <p class="m30__p"><b>Выбор времени:</b> {{ open.choose }}</p>
      <p class="m30__p"><b>Рождение в эту мухурту:</b> {{ open.birth }}</p>
      <p class="m30__p"><b>Прашна (вопрос):</b> {{ open.prashna }}</p>
      <p class="m30__p m30__p--muted">{{ open.deity }}</p>

      <p v-if="open.nameDiffers" class="m30__p m30__p--muted">
        В расчётной таблице сервиса эта мухурта названа «{{ open.calcName }}»:
        два источника дают для этой позиции разные варианты имени — где-то это
        разночтение транслитерации, где-то другое традиционное название того же
        отрезка. Порядок мухурт и границы времени от этого не меняются.
      </p>
      <p v-if="open.sources" class="m30__p m30__p--muted">
        Источники описания: {{ open.sources }}.
      </p>
    </div>
    <p v-else class="m30__hint">
      Нажмите на мухурту — откроется владыка, тема, значение и то, для чего
      её выбирают.
    </p>

    <p class="m30__hint">
      Дневные мухурты — пятнадцатые доли светлого времени, ночные — тёмного,
      поэтому их длительность разная и «48 минут» здесь номинал, а не факт.
      Качество отрезка показано по таблице расчётного ядра; в контентной базе
      оценки мухурты нет, там только описание.
      <template v-if="diffCount">
        Имена мухурт в расчётном ядре и в контентной базе записаны по-разному
        в {{ diffCount }} позициях из 30 — где так, второе имя показано в разборе.
      </template>
    </p>
  </div>
</template>

<style scoped>
.m30__half + .m30__half { margin-top: 18px; }

.m30__cap {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 9px;
  font-size: 13px;
  color: var(--ink);
  font-weight: 500;
}

.m30__caplen {
  font-size: 11.5px;
  color: var(--muted);
  font-weight: 400;
}

.m30__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
  gap: 7px;
}

.m30__c {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: var(--r-sm);
  background: var(--surface-2);
  text-align: left;
  cursor: pointer;
  color: inherit;
  transition: border-color var(--d-fast) var(--e-out), background var(--d-fast) var(--e-out);
}
.m30__c:hover { border-color: var(--accent-line); }
.m30__c.is-good { border-color: var(--good-line); background: var(--good-soft); }
.m30__c.is-bad { border-color: var(--bad-line); background: var(--bad-soft); }
.m30__c.is-mixed { border-color: var(--gold-line); background: var(--gold-soft); }
.m30__c.is-open { outline: 2px solid var(--accent); outline-offset: -2px; }
.m30__c.is-now { outline: 2px solid var(--gold); outline-offset: -2px; }
.m30__c.is-abhijit { border-color: var(--gold-line); }

.m30__no {
  font-size: 10.5px;
  color: var(--muted);
}

.m30__name {
  font-family: var(--serif);
  font-size: 14px;
  color: var(--ink);
  line-height: 1.2;
}

.m30__time {
  font-size: 11.5px;
  color: var(--body);
  font-variant-numeric: tabular-nums;
}

.m30__flag {
  margin-top: 3px;
  align-self: flex-start;
  padding: 1px 7px;
  border-radius: var(--r-pill);
  background: var(--gold-soft);
  color: var(--gold-ink);
  font-size: 10px;
}
.m30__flag--now { background: var(--accent-soft); color: var(--accent-ink); }

.m30__det {
  margin-top: 16px;
  padding: 15px 16px;
  border: 1px solid var(--line);
  border-left: 3px solid var(--accent);
  border-radius: var(--r-md);
  background: var(--surface-2);
}

.m30__dethead {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 10px;
}

.m30__detname {
  font-family: var(--serif);
  font-size: 18px;
  color: var(--ink);
}

.m30__skt {
  margin-left: 6px;
  font-size: 15px;
  color: var(--gold-ink);
}

.m30__dettime {
  font-size: 12.5px;
  color: var(--muted);
  font-variant-numeric: tabular-nums;
}

.m30__p {
  margin: 10px 0 0;
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--body);
}
.m30__p b { color: var(--ink); font-weight: 500; }
.m30__p--muted { font-size: 12.5px; color: var(--muted); }

.m30__hint {
  margin: 14px 0 0;
  font-size: 12.5px;
  line-height: 1.55;
  color: var(--muted);
}
</style>
