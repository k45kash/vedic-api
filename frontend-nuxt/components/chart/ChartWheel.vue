<script setup lang="ts">
/**
 * Раши-чакра (D1) в двух традиционных начертаниях.
 *
 * Геометрия НЕ рисуется «на глаз»: полигоны, центры подписей и сетка берутся
 * из `content/chart_geometry.json` (поля north.polygons / north.label_centers /
 * south.grid_positions / south.cell). Компонент — чистая презентация: что
 * считать первым домом и какие планеты где стоят, решает страница.
 *
 * Разница начертаний принципиальная, её нельзя путать:
 *   • северное — дома закреплены за ромбами (1-й всегда наверху), знаки едут;
 *   • южное   — знаки закреплены за клетками сетки 4×4, дома едут.
 *
 * ВАЖНО про `south.grid_positions` в chart_geometry.json: в исходнике коллеги
 * это кольцо клеток индексировалось номером ДОМА — там рисовалась справочная
 * карта без лагны, и дом 1 просто ставили в первую клетку кольца. В настоящей
 * южно-индийской карте клетки закреплены за ЗНАКАМИ: Овен — вторая клетка
 * верхнего ряда, дальше по часовой стрелке. Кольцо клеток то же самое, поэтому
 * мы берём геометрию как есть и пере-ключаем её со «домов» на знаки —
 * смещение ровно на две позиции (см. southKeyForSign).
 */

import type { WheelHouse, WheelPlanet } from './types'

const props = withDefaults(defineProps<{
  /** Разобранный content/chart_geometry.json; null — пока грузится. */
  geometry: Record<string, any> | null
  variant?: 'north' | 'south'
  houses: WheelHouse[]
  /** Подсветить группы домов (только когда дома вообще осмысленны). */
  groups?: boolean
  /** Показывать номера домов. При недостоверной лагне номера скрываются. */
  showHouses?: boolean
  /** Подпись в центре южной карты: «от Лагны» / «от Луны». */
  originLabel?: string
  ariaLabel?: string
}>(), {
  variant: 'north',
  groups: false,
  showHouses: true,
  originLabel: '',
  ariaLabel: '',
})

/** Заливка по группе дома. Красим мягко: это классификация силы дома,
 * а не приговор — тона берём из общей палитры, своих не вводим. */
const GROUP_FILL: Record<string, string> = {
  'Трикона': 'var(--good-soft)',
  'Кендра': 'var(--neu-soft)',
  'Духстана': 'var(--bad-soft)',
  'Упачая': 'var(--gold-soft)',
}

function fillFor(h: WheelHouse): string {
  if (!props.groups || !props.showHouses) return 'transparent'
  return GROUP_FILL[h.group || ''] || 'transparent'
}

/** Сколько меток планет помещается в строку клетки.
 * В северной карте угловые дома (3, 5, 9, 11) — узкие треугольники, и три
 * метки в строку из них вылезают за рамку; проверено на карте с тремя
 * планетами в 5-м доме. */
const PER_LINE = { north: 2, south: 3 }

function planetLines(h: WheelHouse, per: number): WheelPlanet[][] {
  const out: WheelPlanet[][] = []
  for (let i = 0; i < h.planets.length; i += per) out.push(h.planets.slice(i, i + per))
  return out
}

/** Цвет метки планеты: достоинство говорит само за себя, без подписей. */
function planetColor(p: WheelPlanet): string {
  if (p.dignity === 'exalted') return 'var(--good)'
  if (p.dignity === 'debilitated') return 'var(--bad)'
  return 'var(--gold-ink)'
}

function planetLabel(p: WheelPlanet): string {
  // ℞ — общепринятая пометка вакри; станция отмечается отдельно точкой.
  return p.short + (p.retro ? '℞' : '') + (p.stationary ? '·' : '')
}

// ─── Северное начертание: дома фиксированы ──────────────────────────────────

const northCells = computed(() => {
  const g = props.geometry?.north
  if (!g) return []
  return props.houses.map((h) => {
    const poly: number[][] = g.polygons?.[String(h.house)] ?? []
    const c: number[] = g.label_centers?.[String(h.house)] ?? [0, 0]
    return {
      ...h,
      poly: poly.map((p) => p.join(',')).join(' '),
      cx: c[0],
      cy: c[1],
      fill: fillFor(h),
      lines: planetLines(h, PER_LINE.north),
    }
  })
})

const northFrame = computed(() => props.geometry?.north?.outer_frame ?? null)

// ─── Южное начертание: знаки фиксированы ────────────────────────────────────

/** Ключ в south.grid_positions для знака (см. пояснение в шапке файла). */
function southKeyForSign(sign: number): string {
  return String(((sign + 1) % 12) + 1)
}

const southCells = computed(() => {
  const g = props.geometry?.south
  if (!g) return []
  const cell: number = g.cell ?? 90
  return props.houses.map((h) => {
    const pos: number[] = g.grid_positions?.[southKeyForSign(h.sign)] ?? [0, 0]
    const x = pos[1] * cell
    const y = pos[0] * cell
    return {
      ...h,
      x,
      y,
      cell,
      cx: x + cell / 2,
      fill: fillFor(h),
      lines: planetLines(h, PER_LINE.south),
    }
  })
})

const southCenter = computed<number[]>(() => props.geometry?.south?.center_rect ?? [90, 90, 180, 180])

const viewBox = computed(() => {
  const v = props.geometry?.[props.variant]?.viewBox ?? [0, 0, 360, 360]
  return v.join(' ')
})
</script>

<template>
  <svg
    v-if="geometry && houses.length"
    class="rchart"
    :viewBox="viewBox"
    role="img"
    :aria-label="ariaLabel"
  >
    <!-- ─── северное начертание ─────────────────────────────────────────── -->
    <template v-if="variant === 'north'">
      <rect
        v-if="northFrame"
        :x="northFrame.x" :y="northFrame.y"
        :width="northFrame.width" :height="northFrame.height"
        fill="none" stroke="var(--line-2)" :stroke-width="northFrame.stroke_width || 1.5"
      />
      <g v-for="c in northCells" :key="c.house">
        <polygon
          :points="c.poly"
          :fill="c.fill"
          :stroke="showHouses && c.house === 1 ? 'var(--accent)' : 'var(--line-2)'"
          :stroke-width="showHouses && c.house === 1 ? 2 : 1"
        />
        <text
          :x="c.cx" :y="c.cy - 11"
          text-anchor="middle" font-size="12"
          :fill="showHouses && c.house === 1 ? 'var(--accent)' : 'var(--muted)'"
        >
          <template v-if="showHouses">{{ c.house }} · </template>{{ c.signShort }}
        </text>
        <text
          v-for="(line, li) in c.lines"
          :key="li"
          :x="c.cx" :y="c.cy + 3 + li * 12"
          text-anchor="middle" font-size="11" font-weight="600"
        >
          <!-- Пробел между метками задаём через dx: обычный пробел в начале
               tspan SVG схлопывает, и метки слипаются («Са℞Ра»). -->
          <tspan
            v-for="(p, pi) in line"
            :key="p.name"
            :dx="pi ? 5 : 0"
            :fill="planetColor(p)"
          >{{ planetLabel(p) }}</tspan>
        </text>
      </g>
    </template>

    <!-- ─── южное начертание ────────────────────────────────────────────── -->
    <template v-else>
      <g v-for="c in southCells" :key="c.house">
        <rect
          :x="c.x" :y="c.y" :width="c.cell" :height="c.cell"
          :fill="c.fill"
          :stroke="showHouses && c.house === 1 ? 'var(--accent)' : 'var(--line-2)'"
          :stroke-width="showHouses && c.house === 1 ? 2 : 1"
        />
        <text
          :x="c.x + 8" :y="c.y + 18"
          font-size="12" fill="var(--muted)"
        >{{ c.signShort }}</text>
        <text
          v-if="showHouses"
          :x="c.x + c.cell - 8" :y="c.y + 18"
          text-anchor="end" font-size="12"
          :fill="c.house === 1 ? 'var(--accent)' : 'var(--muted)'"
        >{{ c.house }}</text>
        <text
          v-for="(line, li) in c.lines"
          :key="li"
          :x="c.cx" :y="c.y + 40 + li * 15"
          text-anchor="middle" font-size="11.5" font-weight="600"
        >
          <!-- Пробел между метками задаём через dx: обычный пробел в начале
               tspan SVG схлопывает, и метки слипаются («Са℞Ра»). -->
          <tspan
            v-for="(p, pi) in line"
            :key="p.name"
            :dx="pi ? 4 : 0"
            :fill="planetColor(p)"
          >{{ planetLabel(p) }}</tspan>
        </text>
      </g>
      <rect
        :x="southCenter[0]" :y="southCenter[1]"
        :width="southCenter[2]" :height="southCenter[3]"
        fill="var(--surface-2)" stroke="var(--line-2)"
      />
      <text
        :x="southCenter[0] + southCenter[2] / 2"
        :y="southCenter[1] + southCenter[3] / 2 - 4"
        text-anchor="middle" font-size="14" fill="var(--gold-ink)"
      >Раши · D1</text>
      <text
        v-if="originLabel"
        :x="southCenter[0] + southCenter[2] / 2"
        :y="southCenter[1] + southCenter[3] / 2 + 15"
        text-anchor="middle" font-size="11.5" fill="var(--muted)"
      >{{ originLabel }}</text>
    </template>
  </svg>

  <p v-else class="hint" style="margin:0">Готовим карту…</p>
</template>
