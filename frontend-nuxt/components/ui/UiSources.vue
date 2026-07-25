<script setup lang="ts">
/**
 * Первоисточники и благодарности (content/sources.json) + легенда меток
 * достоверности из content/disclaimers.json.
 *
 * Зачем: тексты кабинета — самостоятельный пересказ классики, и ссылка на
 * первоисточники должна быть доступна с экрана, а не только в документации.
 * Блок свёрнут по умолчанию и грузит JSON (5 КБ) при первом раскрытии —
 * на обычный просмотр страницы он не влияет.
 */
import { fetchSources, KIND_LABEL, type SourcesData, type DisclaimerKind } from '../../composables/useContentTexts'

// Две разные вещи, и путать их нельзя:
//   • marks  — наши подписи к типам секций («сверено», «рабочая версия», «модель»);
//   • legend — легенда самого автора: пометки внутри его текстов.
// В данных связи между ними нет, поэтому и показываем их порознь.
const { legend } = useDisclaimers()
const marks = (Object.keys(KIND_LABEL) as DisclaimerKind[]).map((kind) => ({ kind, ...KIND_LABEL[kind] }))

const data = ref<SourcesData | null>(null)
const loading = ref(false)

async function onToggle(e: Event) {
  if (!(e.target as HTMLDetailsElement).open || data.value || loading.value) return
  loading.value = true
  try {
    data.value = await fetchSources()
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <details class="sources" @toggle="onToggle">
    <summary class="sources__head">
      <UiIcon name="book" />
      <span class="sources__title">Источники и метки достоверности</span>
      <UiIcon name="chevron-down" class="sources__chev" />
    </summary>

    <div class="sources__body">
      <p v-if="loading && !data" class="hint" style="margin:0">Загружаем список источников…</p>

      <template v-if="data">
        <p v-if="data.intro" class="sources__intro">{{ data.intro }}</p>

        <div v-for="g in data.groups" :key="g.title" class="sources__group">
          <div class="sources__gtitle">{{ g.title }}</div>
          <div v-for="it in g.items" :key="it.name" class="sources__item">
            <div class="sources__name">
              {{ it.name }}<span v-if="it.by && it.by !== '—'" class="sources__by"> — {{ it.by }}</span>
            </div>
            <div v-if="it.note" class="sources__note">{{ it.note }}</div>
          </div>
        </div>

        <p v-if="data.disclaimer" class="sources__note sources__note--foot">{{ data.disclaimer }}</p>
      </template>

      <div class="sources__gtitle sources__gtitle--legend">Как читать метки под разделами</div>
      <div v-for="m in marks" :key="m.kind" class="sources__legend">
        <span class="disc__mark" :class="`disc__mark--${m.kind}`">{{ m.mark }}</span>
        <span class="sources__note">{{ m.meaning }}</span>
      </div>
      <p class="sources__note sources__note--foot">
        Метка относится к источнику текста, а не к точности расчёта. Наши развилки
        методики помечены отдельно — значком с номером пункта рядом с заголовком.
      </p>

      <template v-if="legend.length">
        <div class="sources__gtitle sources__gtitle--legend">Пометки автора внутри текстов</div>
        <div v-for="l in legend" :key="l.mark" class="sources__legend">
          <span class="disc__mark disc__mark--inline">{{ l.mark }}</span>
          <span class="sources__note">{{ l.meaning }}</span>
        </div>
      </template>
    </div>
  </details>
</template>
