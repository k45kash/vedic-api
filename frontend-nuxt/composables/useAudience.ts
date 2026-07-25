// Режим отображения: «Пользователь» (simple) или «Астролог» (pro).
// В прототипе это делал setAud(): на корне ставился класс .is-pro, и все блоки
// с классом .pro становились видимыми. Здесь класс вешает layouts/app.vue,
// а состояние хранится тут и запоминается в localStorage.

export type Audience = 'simple' | 'pro'

const STORAGE_KEY = 'vedic_audience'

let initialized = false

function readStoredAudience(): Audience | null {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved === 'simple' || saved === 'pro' ? saved : null
  } catch {
    return null
  }
}

export function useAudience() {
  const audience = useState<Audience>('vedic-audience', () => 'simple')

  function setAudience(next: Audience) {
    audience.value = next
    if (!import.meta.client) return
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // не критично
    }
  }

  function toggleAudience() {
    setAudience(audience.value === 'pro' ? 'simple' : 'pro')
  }

  if (import.meta.client && !initialized) {
    initialized = true
    const stored = readStoredAudience()
    if (stored) audience.value = stored
  }

  const isPro = computed(() => audience.value === 'pro')

  return { audience, isPro, setAudience, toggleAudience }
}
