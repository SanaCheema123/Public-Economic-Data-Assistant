const rawBase = import.meta.env.VITE_API_URL || ''
export const API_BASE = rawBase.replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  detail: string
  constructor(status: number, detail: string) {
    super(detail)
    this.status = status
    this.detail = detail
  }
}

async function parseError(response: Response) {
  try {
    const body = await response.json()
    return typeof body?.detail === 'string' ? body.detail : JSON.stringify(body?.detail ?? body)
  } catch {
    return response.statusText || 'Request failed'
  }
}

async function doFetch(path: string, init: RequestInit = {}, retry = true): Promise<Response> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: 'include',
    headers: {
      ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(init.headers || {})
    }
  })
  if (response.status === 401 && retry && !path.includes('/auth/login') && !path.includes('/auth/register') && !path.includes('/auth/refresh')) {
    const refresh = await fetch(`${API_BASE}/api/auth/refresh`, { method: 'POST', credentials: 'include' })
    if (refresh.ok) return doFetch(path, init, false)
  }
  return response
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await doFetch(path, init)
  if (!response.ok) throw new ApiError(response.status, await parseError(response))
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export const get = <T>(path: string) => api<T>(path)
export const post = <T>(path: string, body?: unknown) => api<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: 'PATCH', body: JSON.stringify(body) })
export const del = <T>(path: string) => api<T>(path, { method: 'DELETE' })

export async function download(path: string, body: unknown, filename: string) {
  const response = await doFetch(path, { method: 'POST', body: JSON.stringify(body) })
  if (!response.ok) throw new ApiError(response.status, await parseError(response))
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}
