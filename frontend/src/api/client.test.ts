import { afterEach, describe, expect, it, vi } from 'vitest'
import { getHealth, RequestError } from './client'

afterEach(() => vi.unstubAllGlobals())

describe('health API contract', () => {
  it('accepts the backend skeleton response', async () => {
    const data = { status: 'ok', mode: 'mock', ocr_ready: false }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(data)))
    expect(await getHealth()).toEqual(data)
  })

  it.each([
    { status: 'ok', mode: 'mock', ocr_ready: 'false' },
    { status: 'ok', mode: 'unknown', ocr_ready: false },
    { status: 'ok', mode: 'mock' },
    { status: 'ok', mode: 'mock', ocr_ready: false, extra: true },
  ])('rejects invalid success payload %#', async data => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(data)))
    await expect(getHealth()).rejects.toThrow('không đúng contract')
  })

  it('preserves a structured API error and HTTP status', async () => {
    const data = { error: { code: 'ocr_unavailable', message: 'OCR chưa sẵn sàng.', field: null } }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(data, { status: 503 })))
    await expect(getHealth()).rejects.toMatchObject({ message: 'OCR chưa sẵn sàng.', status: 503 })
  })

  it('falls back safely when an HTTP failure has a different shape', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json({ detail: 'private/path' }, { status: 500 })))
    await expect(getHealth()).rejects.toThrow('HTTP 500')
  })

  it('reports non-JSON responses', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>proxy error</html>', { status: 502 })))
    await expect(getHealth()).rejects.toThrow('không phải JSON')
  })

  it('reports connection failures without exposing low-level details', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('synthetic internal error')))
    await expect(getHealth()).rejects.toThrow('Không kết nối được backend')
  })

  it('reports deadlines separately from connection failures', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new DOMException('timeout', 'TimeoutError')))
    await expect(getHealth()).rejects.toBeInstanceOf(RequestError)
    await expect(getHealth()).rejects.toThrow('5 giây')
  })
})
