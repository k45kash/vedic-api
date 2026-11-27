// Низкоуровневое хранилище JWT-токена.
//
// Вынесено в отдельный composable намеренно: useAuth использует useApi,
// а useApi должен подставлять заголовок Authorization. Если бы useApi звал
// useAuth — получилась бы циклическая зависимость. Поэтому оба модуля
// читают токен отсюда, а useAuthToken не зависит ни от одного из них.
//
// Здесь НЕТ сетевых вызовов и никакой бизнес-логики — только useState и браузерное хранилище.

import { authStorage } from '~/utils/authStorage'

export const AUTH_TOKEN_KEY = 'vedic_auth_token'

export function useAuthToken() {
  const token = useState<string | null>('auth-token', () => null)

  const restored = useState('auth-token-restored', () => false)

  if (import.meta.client && !restored.value) {
    restored.value = true
    token.value = authStorage('sessionStorage', AUTH_TOKEN_KEY) ?? authStorage('localStorage', AUTH_TOKEN_KEY)
  }

  function setToken(value: string | null) {
    token.value = value
    if (!import.meta.client) return
    const persisted = authStorage('localStorage', AUTH_TOKEN_KEY, value)
    authStorage('sessionStorage', AUTH_TOKEN_KEY, persisted === value ? null : value)
  }

  return { token, setToken }
}
