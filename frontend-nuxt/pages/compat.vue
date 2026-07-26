<script setup lang="ts">
// Страница «Совместимость» — ашта-кута пары (PLAN 2.10, SERVICE-IA §4.4).
//
// Источники данных:
//   useBirthProfile           → накшатра и раши Луны пользователя
//   POST /api/horoscope       → то же для партнёра (введённого на этой странице)
//   calculators/kuta.ts       → ashtaKutaFull (36) и ashtaKutaPartial (21),
//                               оба через ленивые обёртки useJyotish
//   content/glossary.json     → что означает каждая кута, словами автора базы
//   content/ui_texts.json     → kuta_notes (написаны под частичный расчёт)
//   content/disclaimers.json  → готовые оговорки; своих не сочиняем
//
// ДОМЕННОЕ ПРАВИЛО (HANDOFF §5.2, SERVICE-IA §4.4/§9): совместимость подаётся
// ТОЛЬКО как частичная и никогда как приговор. Даже 36 из 36 не закрывают
// Мангала-дошу, седьмые дома, навамшу и даши — список того, чего ашта-кута не
// покрывает, возвращает сам расчёт, и он показан обязательно.
//
// ЧЕГО ЗДЕСЬ НЕТ: процентов «совместимость 82 %», «энергии пары» и любых
// числовых оценок, которых нет в расчёте (ASTROLOGER-REVIEW Б6). Поле
// `percent` расчёт отдаёт, но на экран оно не выводится: «67 %» читается как
// приговор паре, а «24 из 36» — как балл одной конкретной методики.
import {
  useJyotish, ashtaKutaFull, ashtaKutaPartial, loadGlossary, nakName,
} from '~/composables/useJyotish'
import type { AshtaKutaFullResult, AshtaKutaResult, KutaFactor, KutaKey } from '~/composables/useJyotish'
import type { HoroPlanet } from '~/composables/useBirthProfile'
import type { CompatPerson, CompatRole } from '~/components/compat/types'
import { GLOSSARY_GROUP, KUTA_NO, fmtScore } from '~/components/compat/types'

definePageMeta({ layout: 'app', middleware: 'auth' })
useHead({ title: 'Совместимость — Jyotish' })

const { setPageHeader } = usePageHeader()
const {
  profile, horoscope, loading: meLoading, error: meError, hasProfile,
  timeUnknown, moonUncertain, fetchHoroscope,
} = useBirthProfile()
const { janmaNakshatraName } = useJyotish()
const { disclaimer } = useDisclaimers()
const { t } = useUiTexts()

const MONTHS_RU = [
  'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
  'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
]
const SIGN_RU = [
  'Овен', 'Телец', 'Близнецы', 'Рак', 'Лев', 'Дева',
  'Весы', 'Скорпион', 'Стрелец', 'Козерог', 'Водолей', 'Рыбы',
]

watchEffect(() => {
  setPageHeader({
    title: 'Совместимость',
    subtitle: 'ашта-кута по Луне обоих — один слой сверки, не решение за людей',
    subtitleLink: hasProfile.value ? { text: 'мои данные', to: '/me' } : null,
  })
})

onMounted(() => { if (hasProfile.value) fetchHoroscope() })

// ─── Кто есть кто ───────────────────────────────────────────────────────────
// Варна и Вашья несимметричны: при обмене ролями балл может измениться.
// Поэтому роль выбирается явно, а не угадывается.

const youAre = ref<CompatRole>('bride')

/** Пользователь — из постоянного профиля. */
const moonPlanet = computed<HoroPlanet | null>(
  () => (horoscope.value?.planets ?? []).find((p) => p.name === 'Луна') ?? null,
)

const meBirthLine = computed(() => {
  const p = profile.value
  if (!p?.date) return ''
  const [y, m, d] = p.date.split('-').map(Number)
  const date = Number.isFinite(y) ? `${d} ${MONTHS_RU[(m || 1) - 1]} ${y}` : p.date
  const time = p.timeUnknown ? 'время неизвестно' : p.time
  return [[date, time].filter(Boolean).join(', '), p.city].filter(Boolean).join(' · ')
})

/** Знак Луны при неизвестном времени: Луна проходит до 15,4° за сутки,
 *  у края знака он произволен. Та же граница, что на /chart. */
const meMoonSignUncertain = computed(() => {
  const m = moonPlanet.value
  if (!m || !timeUnknown.value) return false
  return m.deg_in_sign < 7.7 || m.deg_in_sign > 30 - 7.7
})

/** Пользователь как участник расчёта. null — профиля/ответа API ещё нет. */
const meFromProfile = computed<CompatPerson | null>(() => {
  const h = horoscope.value
  if (!h) return null
  const m = moonPlanet.value
  return {
    nakNo: h.nk.num,
    // Знак Луны под вопросом — считаем, что раши нет: лучше частичный расчёт,
    // чем четыре куты, посчитанные по знаку, который мог быть другим.
    moonSign: m && !meMoonSignUncertain.value ? m.sign_num : null,
    moonDeg: m && !meMoonSignUncertain.value ? m.deg_in_sign : null,
    source: 'profile',
    birthLine: meBirthLine.value,
    timeUnknown: timeUnknown.value,
    moonSignUncertain: meMoonSignUncertain.value,
    nakUncertain: moonUncertain.value,
  }
})

/** Резервный ввод «себя», когда постоянного профиля нет вовсе. */
const meManual = ref<CompatPerson | null>(null)
const me = computed<CompatPerson | null>(() => meFromProfile.value ?? meManual.value)

const partner = ref<CompatPerson | null>(null)

const bride = computed<CompatPerson | null>(() => (youAre.value === 'bride' ? me.value : partner.value))
const groom = computed<CompatPerson | null>(() => (youAre.value === 'bride' ? partner.value : me.value))
const brideLabel = computed(() => (youAre.value === 'bride' ? 'Вы' : 'Партнёр'))
const groomLabel = computed(() => (youAre.value === 'bride' ? 'Партнёр' : 'Вы'))

// ─── Расчёт ─────────────────────────────────────────────────────────────────
// kuta.ts тянет nakshatras.json (279 КБ) — только через ленивые обёртки.

const full = ref<AshtaKutaFullResult | null>(null)
const partialResult = ref<AshtaKutaResult | null>(null)
const calcError = ref('')
const calculating = ref(false)

/** Полный расчёт возможен, только если у обоих известен знак Луны. */
const canFull = computed(() => !!bride.value?.moonSign && !!groom.value?.moonSign)
const ready = computed(() => !!bride.value && !!groom.value)

let seq = 0
watch([bride, groom], async () => {
  const b = bride.value, g = groom.value
  full.value = null
  partialResult.value = null
  calcError.value = ''
  if (!b || !g) return
  const my = ++seq
  calculating.value = true
  try {
    if (b.moonSign && g.moonSign) {
      const r = await ashtaKutaFull(
        { nakNo: b.nakNo, moonSign: b.moonSign, moonDeg: b.moonDeg ?? undefined },
        { nakNo: g.nakNo, moonSign: g.moonSign, moonDeg: g.moonDeg ?? undefined },
      )
      if (my === seq) full.value = r
    } else {
      const r = await ashtaKutaPartial(b.nakNo, g.nakNo)
      if (my === seq) partialResult.value = r
    }
  } catch (e) {
    if (my === seq) calcError.value = e instanceof Error ? e.message : String(e)
  } finally {
    if (my === seq) calculating.value = false
  }
}, { immediate: true, deep: true })

/** Куты в каноническом порядке Варна (1) → Нади (8).
 *  Полный расчёт и так отдаёт их в этом порядке, а частичный — в своём
 *  историческом (Гана, Йони, Тара, Нади), из-за чего номера в разборе шли
 *  вразнобой: 6, 4, 3, 8. Сортируем на выводе, расчёт не трогаем. */
const factors = computed<KutaFactor[]>(
  () => [...(full.value?.factors ?? partialResult.value?.factors ?? [])]
    .sort((a, b) => KUTA_NO[a.key] - KUTA_NO[b.key]),
)
const total = computed<number | null>(
  () => full.value?.total ?? partialResult.value?.total ?? null,
)
const maxScore = computed(() => (full.value ? 36 : 21))

/** Вердикт словами самого расчёта. В частичном режиме его нет — и выдумывать
 *  его нельзя: 21 балл не сравнивается с порогом, рассчитанным на 36.
 *
 *  Берём только хвост после «N из 36 — »: сумма уже стоит рядом в квадрате,
 *  и повторять её незачем. Заодно уходит расхождение в разделителе дробной
 *  части: расчёт склеивает строку через шаблон и печатает «26.5», а весь
 *  остальной кабинет пишет «26,5». Формулировка самого вердикта не меняется. */
const verdictTail = computed(() => {
  const v = full.value?.verdict ?? ''
  const i = v.indexOf(' — ')
  return i === -1 ? v : v.slice(i + 3)
})

/** Тон плашки. «Слабо» намеренно не красное: ашта-кута — не диагноз пары. */
const verdictTone = computed<'good' | 'neutral'>(() => {
  const lvl = full.value?.level
  return lvl === 'excellent' || lvl === 'good' ? 'good' : 'neutral'
})

const nadiDosha = computed(() => !!(full.value?.nadiDosha ?? partialResult.value?.nadiDosha))
const bhakutaDosha = computed(() => !!full.value?.bhakutaDosha)

/** Условие смягчения бхакут-доши, которое вернул расчёт (общий управитель раши
 *  или дружественные управители). Балл оно не меняет — так и написано. */
const bhakutaRelief = computed(() => {
  const s = factors.value.find((f) => f.key === 'bhakuta')?.school ?? ''
  const m = s.match(/^Смягчение:[^.]*\./)
  return m ? m[0] : ''
})

// ─── Глоссарий: что означает каждая кута ────────────────────────────────────

const glossary = ref<any | null>(null)
onMounted(async () => {
  try { glossary.value = await loadGlossary() } catch { /* блок просто не появится */ }
})

function glossaryFor(key: KutaKey) {
  const needle = GLOSSARY_GROUP[key]
  if (!needle || !glossary.value?._groups) return null
  const g = (glossary.value._groups as any[]).find((x) => String(x?.group ?? '').startsWith(needle))
  if (!g) return null
  return {
    intro: String(g.intro ?? ''),
    // Термины показываем только там, где их немного: «Как читать» у йони,
    // три потока у нади. Иначе карточка куты превращается в статью.
    terms: (g.terms ?? []).filter((tm: any) => String(tm?.t ?? '') === 'Как читать')
      .map((tm: any) => ({ t: String(tm.t), d: String(tm.d) })),
  }
}

/** Порог для брака и состав восьми кут — цитата из глоссария, не наша формула. */
const kutaGlossary = computed(() => {
  const g = (glossary.value?._groups as any[] | undefined)
    ?.find((x) => String(x?.group ?? '').startsWith('Ашта-кута'))
  if (!g) return null
  return { intro: String(g.intro ?? ''), terms: (g.terms ?? []) as Array<{ t: string; d: string }> }
})

// ─── Мягкие формулировки для чувствительного ────────────────────────────────
// Взяты дословно из docs/DESIGN-SYSTEM.md §4 «Тон дисклеймеров» — эталонные
// формулировки астролога для нади-доши. Своими словами тут писать нечего.

const NADI_SOFT =
  'Совпадение нади — фактор, на который в традиции обращают внимание. Это не запрет на союз, ' +
  'а повод отнестись вдумчиво; при желании есть традиционные средства (упайи). ' +
  'Полную картину даёт астролог.'

// ─── Подписи участников ─────────────────────────────────────────────────────

function personLine(p: CompatPerson | null): string {
  if (!p) return 'не заполнено'
  const parts: string[] = []
  if (p.moonSign) parts.push(`Луна: ${SIGN_RU[p.moonSign - 1]}`)
  if (p.birthLine) parts.push(p.birthLine)
  return parts.join(' · ') || 'только накшатра'
}

/** Имя накшатры пользователя. Из ответа API, если он есть; иначе — из таблицы
 *  имён (резервный ввод «только накшатра», когда профиля нет вовсе). */
const meNakName = computed(
  () => janmaNakshatraName.value || (me.value ? nakName(me.value.nakNo) : ''),
)
</script>

<template>
  <section class="panel cp-page" aria-label="Совместимость">
    <!-- ─── Вводная: что это вообще такое ────────────────────────────────── -->
    <UiCard
      title="Ашта-кута — восемь признаков схождения по Луне"
      subtitle="Сравниваются накшатра и знак Луны обоих. Это один слой сверки, а не вывод о людях."
    >
      <p v-if="kutaGlossary?.intro" class="cp-lead">{{ kutaGlossary.intro }}</p>
      <p v-for="term in kutaGlossary?.terms || []" :key="term.t" class="cp-lead cp-lead--term">
        <b>{{ term.t }}.</b> {{ term.d }}
      </p>
      <div class="cp-pins">
        <UiMethodNote id="Б4" />
      </div>
    </UiCard>

    <!-- ─── Ввод пары ────────────────────────────────────────────────────── -->
    <UiSectionHead title="Кто с кем" />

    <div class="grid-2 cp-pair">
      <!-- Вы -->
      <UiCard v-if="!hasProfile && !meManual" title="Вы" :heading-level="3">
        <p class="cp-msg">
          Данные рождения ещё не заполнены. Заполните их один раз на странице «Обо мне» —
          и совместимость посчитается на все 36 баллов, а заодно заработают карта и остальные разделы.
        </p>
        <UiButton to="/me">Заполнить данные рождения</UiButton>
        <p class="hint cp-fallback-hint">
          Либо укажите ниже только свою накшатру — тогда будет доступен частичный расчёт.
        </p>
      </UiCard>

      <UiCard v-else-if="hasProfile && meError" title="Вы" :heading-level="3">
        <p class="cp-msg">{{ meError }}</p>
        <UiButton @click="fetchHoroscope()">Повторить</UiButton>
      </UiCard>

      <UiCard v-else-if="hasProfile && !horoscope" title="Вы" :heading-level="3">
        <p class="hint" style="margin:0">
          {{ meLoading ? 'Считаем вашу карту…' : 'Карта ещё не рассчитана.' }}
        </p>
      </UiCard>

      <UiCard v-else-if="me" title="Вы" :heading-level="3">
        <UiKv k="Накшатра Луны">
          {{ meNakName || `№ ${me.nakNo}` }}
        </UiKv>
        <UiKv k="Знак Луны (раши)">
          <template v-if="me.moonSign">{{ SIGN_RU[me.moonSign - 1] }}</template>
          <template v-else>—</template>
        </UiKv>
        <UiKv v-if="me.birthLine" k="Рождение">{{ me.birthLine }}</UiKv>

        <UiDisclaimer v-if="me.nakUncertain" tone="warn">
          Накшатра вашей Луны под вопросом
          <template v-if="me.timeUnknown">
            — время рождения не указано, а за сутки Луна успевает сменить накшатру.
          </template>
          <template v-else>
            — Луна стоит у самой границы накшатры.
          </template>
          Гана, Йони, Тара и Нади считаются именно от неё, поэтому результат ниже
          может относиться к соседней накшатре.
          <br>
          <NuxtLink to="/me">Уточнить данные рождения</NuxtLink>
        </UiDisclaimer>

        <p v-else-if="!me.moonSign && me.timeUnknown" class="hint cp-note">
          Знак Луны под вопросом (время рождения не указано, Луна у края знака), поэтому
          четыре куты из восьми не считаем — останется частичный расчёт.
        </p>
      </UiCard>

      <!-- Партнёр -->
      <CompatPersonForm
        title="Партнёр"
        subtitle="Нигде не сохраняется — данные живут только пока открыта страница."
        @update:person="partner = $event"
      />
    </div>

    <!-- Резервный ввод себя, когда профиля нет -->
    <CompatPersonForm
      v-if="!hasProfile"
      class="cp-selfform"
      title="Вы — только накшатра"
      subtitle="Быстрый вариант без полного профиля: хватит на частичный расчёт (21 балл)."
      default-mode="nakshatra"
      @update:person="meManual = $event"
    />

    <!-- ─── Роли ─────────────────────────────────────────────────────────── -->
    <UiCard v-if="ready" title="Роли в расчёте" :heading-level="3">
      <div class="seg cp-roles" role="group" aria-label="Роли в расчёте">
        <button
          type="button"
          :class="{ 'is-on': youAre === 'bride' }"
          :aria-pressed="youAre === 'bride'"
          @click="youAre = 'bride'"
        >
          Вы — невеста
        </button>
        <button
          type="button"
          :class="{ 'is-on': youAre === 'groom' }"
          :aria-pressed="youAre === 'groom'"
          @click="youAre = 'groom'"
        >
          Вы — жених
        </button>
      </div>
      <p class="hint cp-note">
        Две куты из восьми несимметричны — Варна и Вашья. Варна сравнивает «уровень» знаков
        и даёт балл, когда варна жениха не ниже варны невесты; таблица Вашьи тоже читается
        по строке невесты и столбцу жениха. Поменяйте роли — эти два балла могут измениться,
        остальные шесть останутся прежними.
        <template v-if="!canFull">
          В частичном расчёте обе эти куты не участвуют, поэтому смена ролей сейчас
          ничего не меняет.
        </template>
      </p>
      <div class="cp-roleline">
        <div><span class="cp-rolekey">Невеста ({{ brideLabel }}):</span> {{ personLine(bride) }}</div>
        <div><span class="cp-rolekey">Жених ({{ groomLabel }}):</span> {{ personLine(groom) }}</div>
      </div>
    </UiCard>

    <!-- ─── Результат ────────────────────────────────────────────────────── -->
    <template v-if="ready">
      <UiSectionHead title="Что получилось" />

      <UiCard v-if="calcError" title="Не удалось посчитать">
        <p class="cp-msg">{{ calcError }}</p>
      </UiCard>

      <UiCard v-else-if="calculating || total === null">
        <p class="hint" style="margin:0">Считаем ашта-куту…</p>
      </UiCard>

      <template v-else>
        <UiCard>
          <UiVerdict :tone="verdictTone">
            <template #score>{{ fmtScore(total) }}</template>
            <template v-if="full">
              {{ fmtScore(total) }} из 36 — {{ verdictTail }}
            </template>
            <template v-else>
              {{ fmtScore(total) }} из 21 — частичный расчёт, четыре куты из восьми
            </template>

            <template #note>
              <template v-if="full">
                Порог, о котором говорит традиция, — от 18 из 36 и при отсутствии нади-доши.
                Это ориентир одной методики, а не оценка людей.
              </template>
              <template v-else>
                Знак Луны известен не у обоих, поэтому Варна, Вашья, Граха-майтри и Бхакут
                (ещё 15 баллов) не посчитаны. Сравнивать {{ fmtScore(total) }} из 21
                с порогом 18 из 36 нельзя — это разные шкалы.
              </template>
            </template>
          </UiVerdict>

          <UiDisclaimer v-if="full && !full.complete" tone="warn">
            Часть кут посчитать не удалось, поэтому итог заведомо занижен —
            смотрите на разбор по кутам, а не на сумму.
          </UiDisclaimer>

          <div class="cp-pins">
            <UiMethodNote id="Б4" />
            <UiMethodNote id="А5" />
          </div>
        </UiCard>

        <!-- Обязательная оговорка о неполноте: текст возвращает сам расчёт -->
        <UiCard v-if="full" title="Чего этот расчёт не покрывает" :heading-level="3">
          <p class="cp-msg">{{ full.disclaimer }}</p>
          <ul class="cp-list">
            <li v-for="item in full.notCovered" :key="item">
              <UiIcon name="info" />
              <span>{{ item }}</span>
            </li>
          </ul>
        </UiCard>

        <!-- В частичном режиме оговорки берём из content/ui_texts.json:
             kuta_notes писались ровно под этот расчёт на 21 балл. -->
        <UiCard v-else title="Чего этот расчёт не покрывает" :heading-level="3">
          <p v-if="t('kuta_notes.result_note')" class="cp-msg">{{ t('kuta_notes.result_note') }}</p>
          <p v-if="t('kuta_notes.full_note')" class="cp-msg cp-msg--muted">{{ t('kuta_notes.full_note') }}</p>
        </UiCard>

        <!-- ─── Доши: мягко, как повод к разговору ─────────────────────── -->
        <template v-if="nadiDosha || bhakutaDosha">
          <UiSectionHead title="На что традиция смотрит отдельно" />

          <UiCard v-if="nadiDosha" title="Нади-доша" :heading-level="3">
            <p class="cp-msg">{{ NADI_SOFT }}</p>
            <p class="cp-msg cp-msg--muted">
              Нади — самая дорогая кута: восемь баллов из тридцати шести. Именно поэтому
              вопрос о том, из какого поля она читается, вынесен астрологу отдельно.
            </p>
            <div class="cp-pins">
              <UiMethodNote id="А1" expanded />
            </div>
          </UiCard>

          <UiCard v-if="bhakutaDosha" title="Бхакут-доша" :heading-level="3">
            <p class="cp-msg">
              Знаки Луны стоят в том взаимном положении, которое традиция отмечает как
              требующее внимания. Балл здесь выставлен строго по таблице — ноль,
              как в публичных калькуляторах.
            </p>
            <p v-if="bhakutaRelief" class="cp-msg cp-relief">
              <UiIcon name="check-circle" />
              <span>{{ bhakutaRelief }} Часть школ при таком условии возвращает все семь баллов —
                мы этого не делаем, чтобы не подгонять сумму; решение за астрологом.</span>
            </p>
            <p v-else class="cp-msg cp-msg--muted">
              Классических условий отмены (общий управитель обоих раши либо взаимно
              дружественные управители) расчёт здесь не нашёл. Другие условия отмены,
              которые применяют школы, — например аспект Юпитера на седьмой дом —
              требуют полной карты и здесь не проверяются.
            </p>
          </UiCard>
        </template>

        <!-- ─── Разбор по кутам ────────────────────────────────────────── -->
        <div class="sechead">
          Разбор по кутам
          <span class="flag">{{ full ? 'восемь из восьми' : 'четыре из восьми' }}</span>
        </div>

        <div class="cp-kutas">
          <CompatKuta
            v-for="f in factors"
            :key="f.key"
            :factor="f"
            :glossary="glossaryFor(f.key)"
          />
        </div>

        <!-- ─── Сводка расхождений школ ────────────────────────────────── -->
        <!-- Карточка стоит ВСЕГДА, а не только когда расчёт вернул оговорки:
             гана-кута симметрична (А6) и йони упрощена (А7) в любом раскладе,
             а спорные клетки Вашьи и выбор дружбы планет — в А5. Молчать об
             этом на «удачных» парах значило бы прятать вопрос. -->
        <UiCard title="Где школы расходятся" :heading-level="3">
          <p class="cp-msg">
            Ашта-кута — не один канон, а семейство таблиц. Ниже собрано всё, что в этом
            расчёте выбрано из нескольких вариантов; у своих кут эти же оговорки стоят рядом.
          </p>
          <ul v-if="full && full.caveats.length" class="cp-list">
            <li v-for="(c, i) in full.caveats" :key="i">
              <UiIcon name="info" />
              <span>{{ c }}</span>
            </li>
          </ul>
          <p v-else-if="full" class="hint cp-note">
            В этой паре ни одна кута не попала на спорную клетку таблиц —
            но сами развилки методики никуда не делись, они перечислены ниже.
          </p>
          <p v-else class="hint cp-note">
            Частичный расчёт задействует Гану, Йони, Тару и Нади — развилки по ним ниже.
          </p>
          <div class="cp-pins">
            <!-- А1 здесь сознательно нет: она стоит у самой нади-куты и,
                 когда доша нашлась, в карточке про неё — трижды повторять
                 один и тот же вопрос незачем. -->
            <UiMethodNote v-if="full" id="А5" expanded />
            <UiMethodNote id="А6" />
            <UiMethodNote id="А7" />
          </div>
        </UiCard>

        <!-- Дисклеймер достоверности из content/disclaimers.json. Секции про
             ашта-куту в файле сейчас нет — блок не рисуется вовсе (UiDisclaimer
             при entry === null молчит). Появится в файле — появится и здесь. -->
        <UiDisclaimer :entry="disclaimer('kuta')" />

        <UiNoteBar>
          Ашта-кута смотрит только на Луну обоих. Возраст, здоровье, договорённости и
          согласие людей лежат вне джьотиша — и весят больше любой суммы баллов.
        </UiNoteBar>
      </template>
    </template>

    <UiCard v-else-if="hasProfile || meManual" class="cp-waiting">
      <p class="hint" style="margin:0">
        Заполните данные партнёра — и разбор появится здесь.
      </p>
    </UiCard>
  </section>
</template>

<style scoped>
/* Оформление живёт в assets/css/tokens.css (секция «ЭКРАН СОВМЕСТИМОСТЬ»),
   здесь — только то, что нужно ровно этой странице. */
.cp-selfform { margin-top: 16px; }
.cp-waiting { margin-top: 16px; }
</style>
