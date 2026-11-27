export function authStorage(area: 'localStorage' | 'sessionStorage', key: string, value?: string | null) {
  try {
    const storage = window[area]
    if (value === undefined) return storage.getItem(key)
    if (value === null) storage.removeItem(key)
    else storage.setItem(key, value)
    return value
  } catch {
    return null
  }
}
