// Стор авторизации: токен + профиль пользователя + все операции входа.
// Токен лежит в useAuthToken (useState + localStorage), профиль подтягивается
// из GET /users/me.
import { ApiError } from '~/composables/useApi'

export interface AuthUser {
  id: string
  email: string
  is_active: boolean
  is_verified: boolean
  plan?: string | null
  role?: string | null
}

// Ответ GET /auth/providers. Поле telegram_bot необязательное — если бэкенд
// его пришлёт, на странице входа появится виджет Telegram Login.
export interface ProvidersInfo {
  providers: string[]
  telegram_bot?: string | null
}

// Payload от Telegram Login Widget (проверяется по HMAC на бэкенде).
export interface TelegramAuthPayload {
  id: number
  first_name?: string
  last_name?: string
  username?: string
  photo_url?: string
  auth_date: number
  hash: string
  [key: string]: unknown
}

// Коды ошибок fastapi-users → человеческий русский текст.
const ERROR_RU: Record<string, string> = {
  LOGIN_BAD_CREDENTIALS: 'Неверный email или пароль.',
  LOGIN_USER_NOT_VERIFIED: 'Email не подтверждён.',
  REGISTER_USER_ALREADY_EXISTS: 'Пользователь с таким email уже зарегистрирован.',
  REGISTER_INVALID_PASSWORD: 'Пароль не подходит: слишком короткий или слишком простой.',
  RESET_PASSWORD_BAD_TOKEN: 'Ссылка для сброса пароля недействительна или устарела.',
  RESET_PASSWORD_INVALID_PASSWORD: 'Новый пароль не подходит: слишком короткий или слишком простой.',
  VERIFY_USER_BAD_TOKEN: 'Ссылка подтверждения недействительна или устарела.',
}

// Переводим ошибку API в текст для пользователя.
export function humanizeAuthError(e: unknown): string {
  const raw = e instanceof Error ? e.message : String(e)
  return ERROR_RU[raw] || raw || 'Неизвестная ошибка.'
}

export function useAuth() {
  const api = useApi()
  const { token, setToken } = useAuthToken()
  const user = useState<AuthUser | null>('auth-user', () => null)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const plan = computed(() => user.value?.plan || 'free')
  const email = computed(() => user.value?.email || '')

  // Сбрасываем локальное состояние (без обращения к серверу).
  function clear() {
    setToken(null)
    user.value = null
  }

  // Профиль текущего пользователя. 401 = токен протух → чистим,
  // иначе пользователь залипнет в состоянии «залогинен, но ничего не работает».
  async function fetchUser(): Promise<AuthUser | null> {
    if (!token.value) {
      user.value = null
      return null
    }
    try {
      user.value = await api.get<AuthUser>('/users/me')
      return user.value
    } catch (e) {
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) clear()
      throw e
    }
  }

  async function login(mail: string, password: string) {
    const { access_token } = await api.postForm<{ access_token: string }>('/auth/jwt/login', {
      username: mail,
      password,
    })
    setToken(access_token)
    // Профиль не критичен для входа: если /users/me недоступен, вход не ломаем.
    await fetchUser().catch(() => null)
  }

  async function register(mail: string, password: string) {
    return api.post<AuthUser>('/auth/register', { email: mail, password })
  }

  function logout() {
    clear()
  }

  // Приём токена извне (OAuth-возврат на /auth/callback).
  async function loginWithToken(access_token: string) {
    setToken(access_token)
    await fetchUser().catch(() => null)
  }

  // Список включённых соц-провайдеров. Бэкенд может быть ещё не задеплоен —
  // тогда 404/сетевая ошибка, и мы просто не показываем кнопки.
  async function fetchProviders(): Promise<ProvidersInfo> {
    try {
      const data = await api.get<ProvidersInfo>('/auth/providers')
      return {
        providers: Array.isArray(data?.providers) ? data.providers : [],
        telegram_bot: data?.telegram_bot || null,
      }
    } catch {
      return { providers: [], telegram_bot: null }
    }
  }

  // Запрашиваем authorization_url и уводим браузер к провайдеру.
  async function startOAuth(provider: string) {
    const { authorization_url } = await api.get<{ authorization_url: string }>(
      `/auth/${provider}/authorize`,
    )
    if (!authorization_url) throw new Error('Бэкенд не вернул ссылку авторизации.')
    if (import.meta.client) window.location.href = authorization_url
  }

  // Telegram — не OAuth: виджет отдаёт подписанный payload, бэкенд проверяет HMAC.
  async function loginWithTelegram(payload: TelegramAuthPayload) {
    const { access_token } = await api.post<{ access_token: string }>('/auth/telegram', payload)
    setToken(access_token)
    await fetchUser().catch(() => null)
  }

  // Письма пока реально не уходят (SMTP не подключён) — предупреждаем в UI.
  async function forgotPassword(mail: string) {
    return api.post('/auth/forgot-password', { email: mail })
  }

  async function resetPassword(resetToken: string, password: string) {
    return api.post('/auth/reset-password', { token: resetToken, password })
  }

  return {
    token,
    user,
    isAuthenticated,
    isAdmin,
    plan,
    email,
    login,
    register,
    logout,
    fetchUser,
    loginWithToken,
    fetchProviders,
    startOAuth,
    loginWithTelegram,
    forgotPassword,
    resetPassword,
  }
}
