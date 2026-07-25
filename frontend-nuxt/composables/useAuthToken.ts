// Низкоуровневое хранилище JWT-токена.
//
// Вынесено в отдельный composable намеренно: useAuth использует useApi,
// а useApi должен подставлять заголовок Authorization. Если бы useApi звал
// useAuth — получилась бы циклическая зависимость. Поэтому оба модуля
// читают токен отсюда, а useAuthToken не зависит ни от одного из них.
//
// Здесь НЕТ сетевых вызовов и никакой бизнес-логики — только useState + localStorage.

export const AUTH_TOKEN_KEY = 'vedic_auth_token'

export function useAuthToken() {
  const token = useState<string | null>('auth-token', () => null)

  // Восстанавливаем токен из localStorage при первом обращении.
  // В проекте ssr:false, но обращение к localStorage всё равно защищаем.
  if (import.meta.client && token.value === null) {
    token.value = localStorage.getItem(AUTH_TOKEN_KEY)
  }

  function setToken(value: string | null) {
    token.value = value
    if (!import.meta.client) return
    if (value) localStorage.setItem(AUTH_TOKEN_KEY, value)
    else localStorage.removeItem(AUTH_TOKEN_KEY)
  }

  return { token, setToken }
}
