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
      throw new APIError(detail || `后端返回 HTTP ${response.status}。`, response.status)
    }
    if (response.status === 204) return undefined as T
    try { return await response.json() as T } catch { throw new APIError('后端返回的内容不是有效 JSON。', response.status) }
  } catch (error) {
    if (error instanceof APIError) throw error
    if (init.signal?.aborted) throw new APIError('请求已取消。')
    throw new APIError('连接失败或请求超时，请检查后端地址和服务状态。')
  }
}
