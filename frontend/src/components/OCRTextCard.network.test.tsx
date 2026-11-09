import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import '@testing-library/jest-dom/vitest'
import { api } from '../api/client'
import OCRTextCard from './OCRTextCard'

describe('OCR save HTTP requests', () => {
  const fetchMock = vi.fn()
  beforeEach(() => { vi.useFakeTimers(); fetchMock.mockReset(); vi.stubGlobal('fetch', fetchMock) })
  afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals() })

  it('Cancel restores the textarea without PATCH/PUT/POST or any other HTTP request', async () => {
    render(<OCRTextCard cleanedText="Đã lưu" rawText="RAW" revision={2} onSave={(text, revision) => api.saveOcr('doc', text, revision)} />)
    fireEvent.click(screen.getByRole('button', {name: /Chỉnh sửa văn bản OCR/}))
    fireEvent.change(screen.getByRole('textbox'), {target: {value: 'Chưa lưu'}})
    fireEvent.click(screen.getByRole('button', {name: 'Hủy'}))
    expect(screen.getByRole('textbox')).toHaveValue('Đã lưu')
    expect(screen.getByRole('button', {name: 'Lưu OCR'})).toBeDisabled()
    await act(async () => {await vi.advanceTimersByTimeAsync(60000)})
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('TC01/03/06/07 sends zero requests while editing and exactly one PATCH after clicking Save', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ ocr_revision: 1, ocr_text_cleaned: 'Bản được lưu' })))
    const view = render(<OCRTextCard cleanedText="Bản đã lưu" rawText="RAW" revision={0} onSave={(text, revision) => api.saveOcr('doc', text, revision)} />)
    fireEvent.click(screen.getByRole('button', { name: /Chỉnh sửa văn bản OCR/ }))
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Bản được lưu' } })
    fireEvent.blur(screen.getByRole('textbox'))
    await act(async () => { await vi.advanceTimersByTimeAsync(60000) })
    fireEvent.click(screen.getByRole('tab', { name: 'OCR gốc' }))
    fireEvent.click(screen.getByRole('tab', { name: 'Cấu trúc tài liệu' }))
    fireEvent.click(screen.getByRole('tab', { name: 'Văn bản dễ đọc' }))
    expect(fetchMock).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Lưu OCR' }))
    fireEvent.click(screen.getByRole('button', { name: 'Đang lưu…' }))
    await act(async () => { await Promise.resolve() })
    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/v1/documents/doc/ocr-correction')
    expect(init.method).toBe('PATCH')
    expect(init.credentials).toBe('include')
    expect(JSON.parse(init.body)).toEqual({ text: 'Bản được lưu', expected_revision: 0 })
    view.unmount()
    await act(async () => { await vi.advanceTimersByTimeAsync(60000) })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})
