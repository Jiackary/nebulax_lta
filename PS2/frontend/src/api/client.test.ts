import { afterEach, describe, expect, it, vi } from 'vitest'

import { ApiError, requestJson } from './client'

describe('requestJson', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('preserves the backend error envelope', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({
      error: { code: 'UPSTREAM_UNAVAILABLE', message: 'Live data is unavailable.', retryable: true },
    }), { status: 503, headers: { 'Content-Type': 'application/json' } })))

    await expect(requestJson('/api/trips/example')).rejects.toEqual(
      new ApiError('UPSTREAM_UNAVAILABLE', 'Live data is unavailable.', true, 503),
    )
  })

  it('uses a safe fallback when a gateway returns HTML', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<h1>Bad gateway</h1>', {
      status: 502,
      headers: { 'Content-Type': 'text/html' },
    })))

    await expect(requestJson('/api/trips/example')).rejects.toEqual(
      new ApiError('UPSTREAM_UNAVAILABLE', 'The service is temporarily unavailable. Please try again.', true, 502),
    )
  })

  it('encodes query values', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ results: [] }), {
      headers: { 'Content-Type': 'application/json' },
    }))
    vi.stubGlobal('fetch', fetchMock)

    await requestJson('/api/places/search', { query: { q: 'Blk 208B & clinic' } })

    expect(fetchMock).toHaveBeenCalledWith('/api/places/search?q=Blk+208B+%26+clinic', expect.any(Object))
  })

  it('does not retry a POST after a timeout', async () => {
    vi.useFakeTimers()
    const fetchMock = vi.fn((_url: string, init: RequestInit) => new Promise<Response>((_, reject) => {
      init.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))
    }))
    vi.stubGlobal('fetch', fetchMock)

    const request = requestJson('/api/trips', { method: 'POST', body: { appointment_at: '2026-10-20T09:00:00+08:00' }, timeoutMs: 10 })
    const rejection = expect(request).rejects.toEqual(
      new ApiError('UPSTREAM_UNAVAILABLE', 'The request took too long. Please try again.', true),
    )
    await vi.advanceTimersByTimeAsync(10)

    await rejection
    expect(fetchMock).toHaveBeenCalledTimes(1)
    vi.useRealTimers()
  })
})
