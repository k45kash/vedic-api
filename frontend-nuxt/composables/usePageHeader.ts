// Содержимое шапки кабинета задаёт страница, а не раскладка.
// Страница вызывает setPageHeader({...}) в setup, layouts/app.vue это читает.
// Состояние сбрасывается при каждом setPageHeader, чтобы «хвосты» предыдущей
// страницы (навигатор даты, кнопка «назад») не переезжали на следующую.

export interface PageHeaderLink {
  text: string
  to?: string
}

// Навигатор даты в центре шапки (макет concepte.png).
// Обработчики отдаёт страница — данные и календарь появятся на следующем этапе.
export interface PageHeaderDateNav {
  label: string
  onPrev?: () => void
  onNext?: () => void
  onPick?: () => void
}

// Блок локации справа: город + локальное время.
export interface PageHeaderPlace {
  city: string
  time?: string
}

export interface PageHeader {
  title: string
  subtitle?: string
  /** Ссылка-хвост подзаголовка, например «изменить данные». */
  subtitleLink?: PageHeaderLink | null
  /** Маршрут для стрелки «назад» слева от заголовка. null — стрелки нет. */
  back?: string | null
  dateNav?: PageHeaderDateNav | null
  place?: PageHeaderPlace | null
}

const EMPTY: PageHeader = {
  title: '',
  subtitle: '',
  subtitleLink: null,
  back: null,
  dateNav: null,
  place: null,
}

export function usePageHeader() {
  const header = useState<PageHeader>('vedic-page-header', () => ({ ...EMPTY }))

  function setPageHeader(next: PageHeader) {
    header.value = { ...EMPTY, ...next }
  }

  function resetPageHeader() {
    header.value = { ...EMPTY }
  }

  return { header, setPageHeader, resetPageHeader }
}
