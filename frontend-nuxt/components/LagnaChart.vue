<script setup lang="ts">
// Северо-индийский лагна-чарт. Принимает ответ /api/horoscope и рисует
// 12 ромбовидных секторов с планетами и подписями знаков.
const props = defineProps<{ horoscope: any }>()

const ABBR: Record<string, string> = {
  'Солнце': 'Su', 'Луна': 'Mo', 'Марс': 'Ma', 'Меркурий': 'Me',
  'Юпитер': 'Ju', 'Венера': 'Ve', 'Сатурн': 'Sa', 'Раху': 'Ra', 'Кету': 'Ke',
}
const SIGN_ABBR: Record<string, string> = {
  'Овен': 'Ari', 'Телец': 'Tau', 'Близнецы': 'Gem', 'Рак': 'Can',
  'Лев': 'Leo', 'Дева': 'Vir', 'Весы': 'Lib', 'Скорпион': 'Sco',
  'Стрелец': 'Sag', 'Козерог': 'Cap', 'Водолей': 'Aqu', 'Рыбы': 'Pis',
}

// Геометрия (viewBox 0 0 400 400)
const O  = [200, 200]
const TL = [20, 20],  TR = [380, 20],  BR = [380, 380], BL = [20, 380]
const TC = [200, 20], RC = [380, 200], BC = [200, 380], LC = [20, 200]
const I1 = [110, 110], I2 = [290, 110], I3 = [290, 290], I4 = [110, 290]

const houses = [
  { pts: [O, I2, TC, I1],  cx: 200, cy: 100, nx: 200, ny: 36  },
  { pts: [TL, TC, I1],     cx: 110, cy: 50,  nx: 55,  ny: 44  },
  { pts: [TL, I1, LC],     cx: 50,  cy: 110, nx: 44,  ny: 95  },
  { pts: [O, I4, LC, I1],  cx: 100, cy: 200, nx: 36,  ny: 200 },
  { pts: [LC, I4, BL],     cx: 50,  cy: 290, nx: 44,  ny: 308 },
  { pts: [I4, BC, BL],     cx: 110, cy: 352, nx: 55,  ny: 358 },
  { pts: [O, I3, BC, I4],  cx: 200, cy: 302, nx: 200, ny: 366 },
  { pts: [I3, BR, BC],     cx: 293, cy: 352, nx: 348, ny: 358 },
  { pts: [RC, BR, I3],     cx: 352, cy: 293, nx: 358, ny: 308 },
  { pts: [O, I2, RC, I3],  cx: 302, cy: 200, nx: 366, ny: 200 },
  { pts: [TR, RC, I2],     cx: 352, cy: 110, nx: 358, ny: 95  },
  { pts: [TC, TR, I2],     cx: 293, cy: 50,  nx: 348, ny: 44  },
]

const cells = computed(() => {
  const byHouse: Record<number, string[]> = {}
  props.horoscope.planets
    .filter((p: any) => p.available)
    .forEach((p: any) => {
      if (!byHouse[p.house]) byHouse[p.house] = []
      byHouse[p.house].push(ABBR[p.name] ?? p.name.slice(0, 2))
    })

  const houseSign: Record<number, string> = {}
  props.horoscope.lagna.houses?.forEach((h: any) => {
    houseSign[h.house] = SIGN_ABBR[h.sign_ru] ?? h.sign_ru?.slice(0, 3) ?? ''
  })

  return houses.map((h, i) => {
    const num = i + 1
    const planets = byHouse[num] ?? []
    const sign = houseSign[num] ?? ''
    const lines: string[] = []
    for (let j = 0; j < planets.length; j += 2) lines.push(planets.slice(j, j + 2).join(' '))
    const lineH = 13
    const startY = h.cy - (lines.length * lineH) / 2 + 6
    return {
      key:   num,
      poly:  h.pts.map(p => p.join(',')).join(' '),
      isLagna: num === 1,
      hNum:  num,
      nx: h.nx, ny: h.ny,
      sign,
      lines: lines.map((text, li) => ({ text, x: h.cx, y: startY + li * lineH })),
    }
  })
})
</script>

<template>
  <div class="card">
    <h2>Лагна-чарт</h2>
    <div class="chart-wrap">
      <svg viewBox="0 0 400 400" xmlns="http://www.w3.org/2000/svg" class="lagna-svg">
        <template v-for="cell in cells" :key="cell.key">
          <polygon :points="cell.poly" class="chart-house" :class="{ 'chart-lagna': cell.isLagna }" />
          <text :x="cell.nx" :y="cell.ny" text-anchor="middle" class="chart-hnum">{{ cell.hNum }}</text>
          <text v-if="cell.sign" :x="cell.nx" :y="cell.ny + 11" text-anchor="middle" class="chart-sign">{{ cell.sign }}</text>
          <text v-for="(ln, i) in cell.lines" :key="i" :x="ln.x" :y="ln.y" text-anchor="middle" class="chart-planet">{{ ln.text }}</text>
        </template>
      </svg>
    </div>
  </div>
</template>

<style scoped>
.chart-wrap { display: flex; justify-content: center; }
.lagna-svg  { width: 100%; max-width: 380px; height: auto; }
.chart-house { fill: #fdf8ee; stroke: #1d1d1f; stroke-width: 1.5; }
.chart-lagna { fill: #fff8e1; }
.chart-hnum  { font-size: 11px; font-weight: 600; fill: #a1a1a6; }
.chart-sign  { font-size: 9px; fill: #a1a1a6; }
.chart-planet{ font-size: 13px; font-weight: 600; fill: #1d1d1f; }
</style>
