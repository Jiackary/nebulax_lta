type Query = Record<string, string | number | boolean | null | undefined>

type RequestOptions = Omit<RequestInit, 'body' | 'method' | 'signal'> & {
  body?: unknown
  method?: 'DELETE' | 'GET' | 'POST'
  query?: Query
  signal?: AbortSignal
  timeoutMs?: number
}

type ErrorEnvelope = { error?: { code?: string; message?: string; retryable?: boolean } }

export class ApiError extends Error {
  readonly code: string
  readonly retryable: boolean
  readonly status?: number

  constructor(code: string, message: string, retryable: boolean, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.retryable = retryable
    this.status = status
  }
}

function requestUrl(path: string, query?: Query) {
  if (!query) return path
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== null && value !== undefined) params.set(key, String(value))
  }
  const search = params.toString()
  return search ? `${path}?${search}` : path
}

async function responseBody(response: Response): Promise<unknown> {
  const text = await response.text()
  if (!text) return undefined
  try {
    return JSON.parse(text) as unknown
  } catch {
    return undefined
  }
}

export async function requestJson<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { body, method = 'GET', query, signal, timeoutMs = 20_000, headers, ...rest } = options
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort('timeout'), timeoutMs)
  const abortFromCaller = () => controller.abort(signal?.reason)
  signal?.addEventListener('abort', abortFromCaller, { once: true })

  try {
    const response = await fetch(requestUrl(path, query), {
      ...rest,
      method,
      signal: controller.signal,
      headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}), ...headers },
      ...(body ? { body: JSON.stringify(body) } : {}),
    })
    const payload = await responseBody(response)
    if (!response.ok) {
      const error = (payload as ErrorEnvelope | undefined)?.error
      throw new ApiError(
        error?.code ?? 'UPSTREAM_UNAVAILABLE',
        error?.message ?? 'The service is temporarily unavailable. Please try again.',
        error?.retryable ?? response.status >= 500,
        response.status,
      )
    }
    return payload as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (controller.signal.aborted && controller.signal.reason === 'timeout') {
      throw new ApiError('UPSTREAM_UNAVAILABLE', 'The request took too long. Please try again.', true)
    }
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('REQUEST_CANCELLED', 'The request was cancelled.', false)
    }
    throw new ApiError('UPSTREAM_UNAVAILABLE', 'The service is temporarily unavailable. Please try again.', true)
  } finally {
    window.clearTimeout(timer)
    signal?.removeEventListener('abort', abortFromCaller)
  }
}
