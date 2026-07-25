// Набор линейных иконок кабинета (стиль прототипа: viewBox 24×24, обводка 1.6).
// Хранится отдельным модулем, чтобы тип IconName можно было импортировать
// в props любых компонентов UI-кита.
// Разметка статичная, из этого файла — пользовательских данных здесь нет.

export const ICONS = {
  // навигация
  user: '<circle cx="12" cy="8" r="3.6"/><path d="M4.8 20a7.2 7.2 0 0114.4 0"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.2 5.2l1.6 1.6M17.2 17.2l1.6 1.6M18.8 5.2l-1.6 1.6M6.8 17.2l-1.6 1.6" stroke-linecap="round"/>',
  moon: '<path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z"/>',
  calendar: '<rect x="3.5" y="5" width="17" height="15.5" rx="2.5"/><path d="M3.5 9.5h17M8 3.5v3M16 3.5v3" stroke-linecap="round"/>',
  heart: '<path d="M12 20s-7.2-4.3-7.2-9.2A4.3 4.3 0 0112 8.6a4.3 4.3 0 017.2 2.2C19.2 15.7 12 20 12 20z"/>',
  lotus: '<path d="M12 3.5c2.4 2.6 3.6 5.2 3.6 7.9S14.4 16.7 12 19.3c-2.4-2.6-3.6-5.2-3.6-7.9S9.6 6.1 12 3.5z"/><path d="M5 20.5h14" stroke-linecap="round"/>',
  book: '<path d="M4.5 5.5A2 2 0 016.5 3.5H19v17H6.5a2 2 0 01-2-2z"/><path d="M4.5 16.5h14.5"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 14.5a1.6 1.6 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.6 1.6 0 00-2.7 1.1v.3a2 2 0 11-4 0v-.2a1.6 1.6 0 00-2.7-1.1l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.6 1.6 0 00-1.1-2.7H3.5a2 2 0 110-4h.2a1.6 1.6 0 001.1-2.7l-.1-.1a2 2 0 112.8-2.8l.1.1a1.6 1.6 0 002.7-1.1V3.5a2 2 0 114 0v.2a1.6 1.6 0 002.7 1.1l.1-.1a2 2 0 112.8 2.8l-.1.1a1.6 1.6 0 001.1 2.7h.3a2 2 0 110 4h-.2a1.6 1.6 0 00-1.4 1z"/>',

  // служебные
  crown: '<path d="M4 18h16M4 18l-1.5-9 5 3.5L12 5l4.5 7.5 5-3.5L20 18z"/>',
  headset: '<path d="M4 13v-1a8 8 0 1116 0v1M4 13v3a2 2 0 002 2h1v-5H6a2 2 0 00-2 2zM20 13v3a2 2 0 01-2 2h-1v-5h1a2 2 0 012 2z"/>',
  burger: '<path d="M4 7h16M4 12h16M4 17h16" stroke-linecap="round"/>',
  bell: '<path d="M18 9.5a6 6 0 10-12 0c0 4.8-2 6-2 6h16s-2-1.2-2-6z"/><path d="M13.8 19.5a2.1 2.1 0 01-3.6 0" stroke-linecap="round"/>',
  pin: '<path d="M20 10.5c0 5.5-8 11-8 11s-8-5.5-8-11a8 8 0 1116 0z"/><circle cx="12" cy="10.3" r="2.8"/>',
  sparkle: '<path d="M11 3.5l1.7 4.8 4.8 1.7-4.8 1.7L11 16.5l-1.7-4.8-4.8-1.7 4.8-1.7z" stroke-linejoin="round"/><path d="M18 14.5l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8z" stroke-linejoin="round"/>',
  refresh: '<path d="M20.5 12a8.5 8.5 0 11-2.7-6.2"/><path d="M20.5 4.5V10H15" stroke-linecap="round" stroke-linejoin="round"/>',

  // стрелки
  'arrow-left': '<path d="M19.5 12H4.5M10.5 6l-6 6 6 6" stroke-linecap="round" stroke-linejoin="round"/>',
  'arrow-right': '<path d="M4.5 12h15M13.5 6l6 6-6 6" stroke-linecap="round" stroke-linejoin="round"/>',
  'chevron-left': '<path d="M14.5 5.5l-6.5 6.5 6.5 6.5" stroke-linecap="round" stroke-linejoin="round"/>',
  'chevron-right': '<path d="M9.5 5.5l6.5 6.5-6.5 6.5" stroke-linecap="round" stroke-linejoin="round"/>',
  'chevron-down': '<path d="M6 9.5l6 6 6-6" stroke-linecap="round" stroke-linejoin="round"/>',

  // маркеры и статусы
  check: '<path d="M20 6.5L9.4 17.5 4 12" stroke-linecap="round" stroke-linejoin="round"/>',
  'check-circle': '<circle cx="12" cy="12" r="9"/><path d="M8 12.3l2.7 2.7 5.3-5.6" stroke-linecap="round" stroke-linejoin="round"/>',
  warn: '<path d="M12 3l9 16H3z" stroke-linejoin="round"/><path d="M12 10v4M12 17h.01" stroke-linecap="round"/>',
  alert: '<circle cx="12" cy="12" r="9"/><path d="M12 8v5M12 16h.01" stroke-linecap="round"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11.2v5M12 8h.01" stroke-linecap="round"/>',

  // сферы жизни (полоски-рейтинги в макете)
  work: '<rect x="3" y="7.5" width="18" height="12.5" rx="2.5"/><path d="M8.5 7.5V6a2 2 0 012-2h3a2 2 0 012 2v1.5"/>',
  money: '<ellipse cx="12" cy="7" rx="7" ry="3"/><path d="M5 7v5c0 1.7 3.1 3 7 3s7-1.3 7-3V7"/><path d="M5 12v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5"/>',
  people: '<circle cx="9.2" cy="8.5" r="3.1"/><path d="M3.5 19.5a5.7 5.7 0 0111.4 0"/><path d="M16.2 6.3a3.1 3.1 0 010 5.9M17 19.5a5.7 5.7 0 00-1.6-4"/>',
} as const

export type IconName = keyof typeof ICONS
