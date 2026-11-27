export const LOGIN_RETURN_KEY = 'vedic_login_return'

export function safeLoginReturn(value: unknown): string {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//')) {
    return '/dashboard'
  }

  // Браузер может трактовать обратную косую как разделитель в URL.
  return /[\\\r\n\t]/.test(value) ? '/dashboard' : value
}
