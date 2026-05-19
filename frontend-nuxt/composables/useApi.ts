export function useApi() {
  const config = useRuntimeConfig()
  const base = config.public.apiUrl

  async function post<T = unknown>(path: string, body: unknown): Promise<T> {
    const r = await fetch(`${base}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!r.ok) {
      const err = await r.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${r.status}`)
    }
    return r.json()
  }

  async function get<T = unknown>(path: string): Promise<T> {
    const r = await fetch(`${base}${path}`)
    if (!r.ok) {
      const err = await r.json().catch(() => ({}))
      throw new Error(err.detail || `HTTP ${r.status}`)
    }
    return r.json()
  }

  return { base, post, get }
}
