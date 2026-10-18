import { englishText } from './english'

export class APIError extends Error {
  readonly status: number
  constructor(message: string, status = 0) { super(message); this.name = 'APIError'; this.status = status }
}

export async function requestJSON<T>(url: string, init: RequestInit = {}): Promise<T> {
  try {
    const signal = init.signal ? AbortSignal.any([init.signal, AbortSignal.timeout(8000)]) : AbortSignal.timeout(8000)
    const headers = new Headers(init.headers)
    headers.set('Accept', 'application/json')
    if (init.body !== undefined) headers.set('Content-Type', 'application/json')
    const response = await fetch(url, { ...init, headers, signal })
    if (!response.ok) {
      let detail = ''
      try {
        const payload: unknown = await response.json()
        if (payload && typeof payload === 'object' && 'detail' in payload && typeof payload.detail === 'string') detail = payload.detail.slice(0, 180)
      } catch { /* HTTP status remains actionable when there is no JSON body. */ }
      throw new APIError(detail ? englishText(detail) : `Backend returned HTTP ${response.status}.`, response.status)
    }
    if (response.status === 204) return undefined as T
    try { return await response.json() as T } catch { throw new APIError('The backend response is not valid JSON.', response.status) }
  } catch (error) {
    if (error instanceof APIError) throw error
    if (init.signal?.aborted) throw new APIError('Request cancelled.')
    throw new APIError('Connection failed or timed out. Check the backend URL and service status.')
  }
}
