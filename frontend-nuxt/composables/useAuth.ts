// Временный минимальный auth-стор для внутренних тестов.
// TODO(PLAN.md 1.11): заменить на полноценный стор с провайдерами (VK/Telegram/Yandex),
// когда дойдём до фронтенда авторизации в Фазе 1.
const TOKEN_KEY = 'vedic_auth_token'

const token = useState<string | null>('auth-token', () => null)

function restoreToken() {
  if (import.meta.client && token.value === null) {
    token.value = localStorage.getItem(TOKEN_KEY)
  }
}

export function useAuth() {
  restoreToken()
  const api = useApi()
  const isAuthenticated = computed(() => !!token.value)

  async function login(email: string, password: string) {
    const { access_token } = await api.postForm<{ access_token: string }>('/auth/jwt/login', {
      username: email,
      password,
    })
    token.value = access_token
    if (import.meta.client) localStorage.setItem(TOKEN_KEY, access_token)
  }

  function logout() {
    token.value = null
    if (import.meta.client) localStorage.removeItem(TOKEN_KEY)
  }

  return { token, isAuthenticated, login, logout }
}
