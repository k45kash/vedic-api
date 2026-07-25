<script setup lang="ts">
/**
 * Дришти (аспекты) и юти (соединения) натальной карты.
 *
 * Всё, что здесь видно, приходит из `content/yogakarma.json` через
 * `calculators/drishti.ts`: список аспектов каждой планеты, их описания,
 * 36 парных соединений с именованными йогами. Компонент только раскладывает.
 *
 * Метод и его границы (написаны прямо на странице, не спрятаны):
 *   • аспект считается по знакам в раскладке Whole Sign и только полный —
 *     градусной силы (дришти-бала) и частичных аспектов в данных нет;
 *   • соединение = стоянка в одном знаке, орбиса в градусах нет;
 *   • 5-й и 9-й аспекты узлов помечены в самом справочнике «по ряду школ» —
 *     эта пометка доезжает до клетки, а не теряется по дороге.
 */
import type { AspectRow, ConjunctionRow } from '~/composables/useJyotish'

defineProps<{
  rows: AspectRow[]
  conjunctions: ConjunctionRow[]
  /** Лагна достоверна — можно показывать номера домов, а не только знаки. */
  lagnaReliable: boolean
  /** Общий текст справочника про природу аспекта. */
  note?: string
  /** Глифы планет — приходят со страницы, чтобы не заводить второй справочник. */
  glyphs?: Record<string, string>
}>()
</script>

<template>
  <div class="asp">
    <!-- ─── Аспекты ─────────────────────────────────────────────────────── -->
    <div v-for="r in rows" :key="r.planet" class="asp__row">
      <div class="asp__who">
        <span v-if="glyphs?.[r.planet]" class="asp__glyph" aria-hidden="true">
          {{ glyphs[r.planet] }}
        </span>
        <span class="asp__name">{{ r.planet }}</span>
        <span class="asp__pos">
          <template v-if="lagnaReliable && r.house">{{ r.house }}-й дом · </template>{{ r.signName }}
        </span>
      </div>

      <div class="asp__targets">
        <div
          v-for="t in r.targets"
          :key="t.offset"
          class="asp__t"
          :class="{ 'is-disputed': t.disputed, 'is-hit': t.hits.length }"
        >
          <span class="asp__toff">{{ t.offset }}-й</span>
          <span class="asp__tsign">
            <template v-if="lagnaReliable && t.house">{{ t.house }}-й дом · </template>{{ t.signName }}
          </span>
          <span v-if="t.hits.length" class="asp__hits">→ {{ t.hits.join(', ') }}</span>
          <span v-else class="asp__empty">пусто</span>
          <span v-if="t.disputed" class="asp__disp">по ряду школ</span>
        </div>
      </div>

      <p class="asp__desc">{{ r.desc }}</p>
    </div>

    <p v-if="note" class="asp__note">{{ note }}</p>

    <!-- ─── Соединения ──────────────────────────────────────────────────── -->
    <template v-if="conjunctions.length">
      <div class="asp__sep">Соединения (юти)</div>
      <div v-for="(c, i) in conjunctions" :key="c.pair + c.sign" class="asp__conj">
        <div class="asp__who">
          <span class="asp__name">{{ c.pair }}</span>
          <span class="asp__pos">
            <template v-if="lagnaReliable && c.house">{{ c.house }}-й дом · </template>{{ c.signName }}
          </span>
          <UiChip v-if="c.tag" variant="neutral" class="asp__tag">{{ c.tag }}</UiChip>
        </div>
        <p class="asp__desc">{{ c.text }}</p>
        <!-- Скопление из трёх и более планет разбито на пары, но оговорка
             нужна один раз на знак, а не под каждой парой. -->
        <p v-if="c.group.length > 2 && conjunctions[i - 1]?.sign !== c.sign" class="asp__group">
          В этом знаке стоят сразу {{ c.group.length }} планеты ({{ c.group.join(', ') }}) —
          соединение читают целиком, а не по парам; парные описания здесь только
          как составляющие.
        </p>
      </div>
    </template>
    <p v-else class="asp__note">
      Соединений (двух и более планет в одном знаке) в этой карте нет.
    </p>
  </div>
</template>

<style scoped>
.asp__row,
.asp__conj {
  padding: 13px 0;
  border-top: 1px solid var(--line);
}
.asp__row:first-child { border-top: 0; padding-top: 0; }

.asp__who {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
}

.asp__glyph {
  color: var(--accent);
  font-size: 15px;
  font-family: "Apple Symbols", "Segoe UI Symbol", "Noto Sans Symbols 2", "DejaVu Sans", serif;
}

.asp__name {
  font-size: 14.5px;
  color: var(--ink);
  font-weight: 500;
}

.asp__pos {
  font-size: 12.5px;
  color: var(--muted);
}

.asp__tag { margin-left: 2px; }

.asp__targets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 9px;
}

.asp__t {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
  padding: 5px 10px;
  border: 1px solid var(--line);
  border-radius: var(--r-pill);
  background: var(--surface-2);
  font-size: 12px;
  color: var(--muted);
}
.asp__t.is-hit { border-color: var(--accent-line); background: var(--accent-soft); }
.asp__t.is-disputed { border-style: dashed; }

.asp__toff { color: var(--ink); font-weight: 600; }
.asp__tsign { color: var(--body); }
.asp__hits { color: var(--accent-ink); }
.asp__empty { color: var(--muted); }
.asp__disp {
  padding-left: 6px;
  border-left: 1px solid var(--line-2);
  font-size: 11px;
  color: var(--gold-ink);
}

.asp__desc {
  margin: 9px 0 0;
  font-size: 13.5px;
  line-height: 1.6;
  color: var(--body);
}

.asp__group {
  margin: 7px 0 0;
  font-size: 12.5px;
  line-height: 1.5;
  color: var(--muted);
}

.asp__note {
  margin: 14px 0 0;
  font-size: 12.5px;
  line-height: 1.55;
  color: var(--muted);
}

.asp__sep {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--line-2);
  font-family: var(--serif);
  font-size: 16px;
  color: var(--ink);
}
.asp__sep + .asp__conj { border-top: 0; padding-top: 10px; }

@media (max-width: 640px) {
  .asp__t { width: 100%; border-radius: var(--r-sm); }
}
</style>
