/**
 * Тексты кабинета, живущие в `content/`: дисклеймеры достоверности,
 * вводные абзацы разделов и список первоисточников.
 *
 * Зачем отдельный слой (задача 2.8): формулировки не должны дублироваться
 * в разметке страниц. Автор архива правит их в `content/*.json` — интерфейс
 * подставляет по ключу секции и ничего не сочиняет от себя.
 *
 * ВАЖНО: это НЕ то же самое, что `utils/method-notes.ts`.
 *   • здесь — оценка автора о надёжности ЕГО текстов (источники);
 *   • там   — наши развилки расчёта и отличия от исходной версии (методика).
 * Обе системы нужны, подменять одну другой нельзя.
 *
 * Загрузка ленивая и однократная: JSON едет отдельным чанком, разобранный
 * результат лежит в модульном кэше, поэтому вторая страница уже не ждёт сети.
 */
import { loadDisclaimers, loadUiTexts, loadSources } from './useJyotish'

// ─── Дисклеймеры достоверности (content/disclaimers.json) ───────────────────

/** Тип секции в disclaimers.json — насколько твёрд источник текста. */
export type DisclaimerKind = 'verified' | 'needs-check' | 'model'

export interface DisclaimerEntry {
  /** Ключ секции: 'placements', 'chart-full', 'event-picker'… */
  section: string
  /** Человеческое имя секции из файла. */
  sectionRu: string
  kind: DisclaimerKind
  text: string
  /** Метка достоверности из легенды файла: «классика», «школы расходятся»… */
  mark: string
  /** Расшифровка метки — показываем подсказкой. */
  meaning: string
}

/** Пометка из легенды автора — она про текст внутри раздела, а не про раздел. */
export interface LegendItem { mark: string; meaning: string }

const KIND_ORDER: DisclaimerKind[] = ['verified', 'needs-check', 'model']

/** Подписи к типам секций.
 *
 * Раньше они брались из `legend` по позиции — и это было ошибкой. В данных
 * НЕТ связи между `legend` и `type`: легенда описывает пометки внутри самих
 * текстов («классика», «школы расходятся», «реконструкция / не уверен»),
 * а `type` характеризует секцию целиком. Совпадение по три элемента в каждом
 * списке — случайность.
 *
 * Разница смысловая, а не косметическая: тексты секций `needs-check` говорят
 * «рабочая версия, для проверки с учителем» — это «ещё не сверено», а вовсе
 * не «традиции дают разные варианты». Подписав одно другим, мы бы приписали
 * автору утверждение, которого он не делал.
 *
 * Поэтому подписи выведены из самих типов. Легенда автора показывается
 * отдельно и целиком — в блоке «Источники».
 */
export const KIND_LABEL: Record<DisclaimerKind, { mark: string; meaning: string }> = {
  'verified': {
    mark: 'сверено',
    meaning: 'автор сверил эту часть с источниками',
  },
  'needs-check': {
    mark: 'рабочая версия',
    meaning: 'изложение по классике, которое автор пометил как требующее сверки с первоисточниками и учителем',
  },
  'model': {
    mark: 'модель',
    meaning: 'не канон, а способ взвесить факторы: ориентир, а не вердикт',
  },
}

interface DisclaimersData {
  map: Record<string, DisclaimerEntry>
  legend: LegendItem[]
}

let discParsed: DisclaimersData | null = null
let discPending: Promise<void> | null = null

function parseDisclaimers(raw: any): DisclaimersData {
  // Легенда автора отдаётся как есть — она описывает пометки внутри текстов
  // и живёт отдельно от типов секций (см. KIND_LABEL).
  const legend: LegendItem[] = (Array.isArray(raw?.legend) ? raw.legend : [])
    .map((l: any) => ({ mark: String(l?.mark ?? ''), meaning: String(l?.meaning ?? '') }))
    .filter((l: LegendItem) => !!l.mark)

  const map: Record<string, DisclaimerEntry> = {}
  for (const s of (raw?.sections ?? []) as any[]) {
    const key = String(s?.section ?? '')
    // Секция может встречаться дважды (house-info-popup) — берём первую:
    // вторая запись в файле уточняет ту же панель другими словами.
    if (!key || map[key]) continue
    const kind: DisclaimerKind = KIND_ORDER.includes(s?.type) ? s.type : 'needs-check'
    map[key] = {
      section: key,
      sectionRu: String(s?.section_ru ?? ''),
      kind,
      text: String(s?.text ?? ''),
      mark: KIND_LABEL[kind].mark,
      meaning: KIND_LABEL[kind].meaning,
    }
  }
  return { map, legend }
}

/**
 * Дисклеймеры по ключу секции.
 *
 *   const { disclaimer } = useDisclaimers()
 *   <UiDisclaimer :entry="disclaimer('placements')" />
 *
 * Пока файл не приехал, `disclaimer()` возвращает null и блок просто не
 * рисуется — это честнее, чем показать заглушку.
 */
export function useDisclaimers() {
  const data = useState<DisclaimersData>('vd-disclaimers', () => ({ map: {}, legend: [] }))

  if (!discParsed) {
    if (!discPending) {
      discPending = loadDisclaimers()
        .then((raw) => { discParsed = parseDisclaimers(raw) })
        .catch(() => { discParsed = { map: {}, legend: [] } })
    }
    discPending.then(() => { if (discParsed) data.value = discParsed })
  } else {
    data.value = discParsed
  }

  const legend = computed(() => data.value.legend)
  const disclaimer = (section: string): DisclaimerEntry | null => data.value.map[section] ?? null

  return { disclaimer, legend }
}

// ─── Вводные тексты разделов (content/ui_texts.json) ────────────────────────

let uiParsed: Record<string, any> | null = null
let uiPending: Promise<void> | null = null

/**
 * Тексты интерфейса по ключу: `t('picker_lead')`, `t('kuta_notes.result_note')`.
 *
 * Файл писался под другой интерфейс, поэтому часть формулировок ссылается на
 * разделы, которых у нас нет, — такие ключи мы намеренно не используем
 * (перечень — в отчёте по задаче 2.8), а не подгоняем текст.
 */
export function useUiTexts() {
  const data = useState<Record<string, any>>('vd-ui-texts', () => ({}))

  if (!uiParsed) {
    if (!uiPending) {
      uiPending = loadUiTexts()
        .then((raw) => { uiParsed = raw ?? {} })
        .catch(() => { uiParsed = {} })
    }
    uiPending.then(() => { if (uiParsed) data.value = uiParsed })
  } else {
    data.value = uiParsed
  }

  /** Значение по пути через точку; пусто, если ключа нет. */
  const t = (path: string): string => {
    let cur: any = data.value
    for (const part of path.split('.')) {
      if (cur == null) return ''
      cur = cur[part]
    }
    return typeof cur === 'string' ? cur : ''
  }

  return { t }
}

// ─── Первоисточники (content/sources.json) ──────────────────────────────────

export interface SourceItem { name: string; by: string; note: string }
export interface SourceGroup { title: string; items: SourceItem[] }
export interface SourcesData { intro: string; groups: SourceGroup[]; disclaimer: string }

let srcParsed: SourcesData | null = null
let srcPending: Promise<SourcesData> | null = null

const EMPTY_SOURCES: SourcesData = { intro: '', groups: [], disclaimer: '' }

/** Список первоисточников. Грузится по требованию — блок сворачиваемый. */
export function fetchSources(): Promise<SourcesData> {
  if (srcParsed) return Promise.resolve(srcParsed)
  if (!srcPending) {
    srcPending = loadSources()
      .then((raw): SourcesData => {
        srcParsed = {
          intro: String(raw?.intro ?? ''),
          groups: (raw?.groups ?? []).map((g: any) => ({
            title: String(g?.title ?? ''),
            items: (g?.items ?? []).map((i: any) => ({
              name: String(i?.name ?? ''),
              by: String(i?.by ?? ''),
              note: String(i?.note ?? ''),
            })),
          })),
          disclaimer: String(raw?.disclaimer ?? ''),
        }
        return srcParsed
      })
      .catch(() => EMPTY_SOURCES)
  }
  return srcPending
}
