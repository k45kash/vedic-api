// Светлая / тёмная тема кабинета.
// Значение живёт на <html data-theme="…"> (так же, как в prototype/v2.html),
// запоминается в localStorage и при первом заходе берётся из системной
// настройки prefers-color-scheme.

export type Theme = 'light' | 'dark'

const STORAGE_KEY = 'vedic_theme'

// Инициализируем один раз на загрузку страницы, а не на каждый вызов
// композабла (его дёргают и раскладка, и отдельные компоненты).
let initialized = false

function applyToDom(theme: Theme) {
  if (!import.meta.client) return
  document.documentElement.setAttribute('data-theme', theme)
}

function readStoredTheme(): Theme | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved === 'light' || saved === 'dark' ? saved : null
  } catch {
    // приватный режим / отключённое хранилище — просто игнорируем
    return null
  }
}

export function useTheme() {
  const theme = useState<Theme>('vedic-theme', () => 'light')

  function setTheme(next: Theme) {
    theme.value = next
    applyToDom(next)
    if (!import.meta.client) return
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // не критично: тема просто не переживёт перезагрузку
    }
  }

  function toggleTheme() {
    setTheme(theme.value === 'light' ? 'dark' : 'light')
  }

  if (import.meta.client && !initialized) {
    initialized = true
    const stored = readStoredTheme()
    if (stored) {
      // Выбор пользователя важнее системной настройки.
      theme.value = stored
      applyToDom(stored)
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      theme.value = prefersDark ? 'dark' : 'light'
      applyToDom(theme.value)
    }
  }

  const isDark = computed(() => theme.value === 'dark')

  return { theme, isDark, setTheme, toggleTheme }
}
