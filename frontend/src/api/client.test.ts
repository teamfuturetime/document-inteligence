import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import {api, ApiError} from './client'

describe('VT-043 OCR autosave HTTP contract', () => {
  const fetchMock = vi.fn()
  beforeEach(() => {fetchMock.mockReset(); vi.stubGlobal('fetch', fetchMock)})
  afterEach(() => vi.unstubAllGlobals())

  it('sends expected_revision with credentials and the authenticated CSRF token', async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({user: {id: 'owner'}, csrf_token: 'test-token'})))
    await api.me()
    const saved = {id: 'doc', ocr_revision: 4, ocr_text_cleaned: 'Tiếng Việt'}
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify(saved)))
    expect(await api.saveOcr('doc', 'Tiếng Việt', 3)).toEqual(saved)
    const [url, init] = fetchMock.mock.calls[1]
    expect(url).toBe('/api/v1/documents/doc/ocr-correction')
    expect(init.method).toBe('PATCH')
    expect(init.credentials).toBe('include')
    expect(init.headers.get('X-CSRF-Token')).toBe('test-token')
    expect(JSON.parse(init.body)).toEqual({text: 'Tiếng Việt', expected_revision: 3})
  })

  it.each([409, 500])('propagates HTTP %s as an ApiError without a success payload', async status => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({detail: 'Rejected'}), {status}))
    await expect(api.saveOcr('doc', 'Nháp', 0)).rejects.toMatchObject({status, message: 'Rejected'})
  })

  it('propagates network failure without manufacturing an acknowledgement', async () => {
    fetchMock.mockRejectedValueOnce(new TypeError('Network disconnected'))
    await expect(api.saveOcr('doc', 'Nháp', 0)).rejects.toThrow('Network disconnected')
  })

  it('preserves structured validation error detail', async () => {
    fetchMock.mockResolvedValueOnce(new Response(JSON.stringify({detail: [{msg: 'Field required'}]}), {status: 422}))
    await expect(api.saveOcr('doc', 'Nháp', 0)).rejects.toBeInstanceOf(ApiError)
  })
})
