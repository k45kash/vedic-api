// Ошибка HTTP-запроса. Помимо человекочитаемого message несёт статус и сырой
// detail из тела ответа — по нему useAuth различает коды fastapi-users
// (LOGIN_BAD_CREDENTIALS, REGISTER_USER_ALREADY_EXISTS, …) и ловит 401.
export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(message: string, status: number, detail: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

// Достаём текст ошибки из тела ответа FastAPI.
// detail бывает строкой ("REGISTER_USER_ALREADY_EXISTS"), объектом
// ({code, reason}) или списком ошибок валидации pydantic.
function extractMessage(detail: unknown, status: number): string {
  if (typeof detail === 'string' && detail) return detail
  if (detail && typeof detail === 'object') {
    const d = detail as Record<string, unknown>
    if (typeof d.reason === 'string') return d.reason
    if (typeof d.code === 'string') return d.code
    if (Array.isArray(detail)) {
      const first = detail[0] as Record<string, unknown> | undefined
      if (first && typeof first.msg === 'string') return first.msg
    }
  }
  return `HTTP ${status}`
}

export function useApi() {
  const config = useRuntimeConfig()
  const base = config.public.apiUrl
  // Токен читаем напрямую из низкоуровневого хранилища, а не через useAuth —
  // иначе useApi ↔ useAuth зациклились бы (см. комментарий в useAuthToken.ts).
  const { token } = useAuthToken()

  // Если токен есть — подставляем его во все запросы.
  // Публичные ручки (/api/*) от лишнего заголовка не страдают.
  function authHeaders(extra: Record<string, string> = {}): Record<string, string> {
    return token.value ? { ...extra, Authorization: `Bearer ${token.value}` } : { ...extra }
  }

  async function handle<T>(r: Response): Promise<T> {
    if (!r.ok) {
      const body = await r.json().catch(() => ({} as Record<string, unknown>))
      const detail = (body as Record<string, unknown>).detail
      throw new ApiError(extractMessage(detail, r.status), r.status, detail)
    }
    // 202/204 могут прийти без тела — не падаем на пустом JSON.
    if (r.status === 204) return undefined as T
    return (await r.json().catch(() => ({}))) as T
  }

  async function post<T = unknown>(path: string, body: unknown): Promise<T> {
    const r = await fetch(`${base}${path}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(body),
    })
    return handle<T>(r)
  }

  async function get<T = unknown>(path: string): Promise<T> {
    const r = await fetch(`${base}${path}`, { headers: authHeaders() })
    return handle<T>(r)
  }

  // fastapi-users' /auth/jwt/login ждёт OAuth2PasswordRequestForm —
  // form-urlencoded, а не JSON, поэтому отдельный метод.
  async function postForm<T = unknown>(path: string, body: Record<string, string>): Promise<T> {
    const r = await fetch(`${base}${path}`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/x-www-form-urlencoded' }),
      body: new URLSearchParams(body),
    })
    return handle<T>(r)
  }

  return { base, post, get, postForm }
}
