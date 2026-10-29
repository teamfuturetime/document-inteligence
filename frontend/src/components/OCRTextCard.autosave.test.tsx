import {act, cleanup, fireEvent, render, screen} from '@testing-library/react'
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import '@testing-library/jest-dom/vitest'
import {ApiError} from '../api/client'
import OCRTextCard from './OCRTextCard'

const editor = () => screen.getByRole('textbox', {name: 'Nội dung OCR đã hiệu chỉnh'})
const type = (text: string) => fireEvent.change(editor(), {target: {value: text}})
const advance = (ms: number) => act(async () => {await vi.advanceTimersByTimeAsync(ms)})
function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: Error) => void
  const promise = new Promise<T>((yes, no) => {resolve = yes; reject = no})
  return {promise, resolve, reject}
}
const saved = (text: string, revision = 1) => ({ocr_text_cleaned: text, ocr_revision: revision})
function edit(onSave = vi.fn().mockImplementation(async (text: string, revision: number) => saved(text, revision + 1))) {
  const view = render(<OCRTextCard cleanedText="Ban đầu" rawText="OCR GỐC" revision={0} onSave={onSave}/>)
  fireEvent.click(screen.getByRole('button', {name: /Chỉnh sửa văn bản OCR/}))
  return {...view, onSave}
}

describe('VT-043 automatic OCR saving', () => {
  beforeEach(() => {vi.useFakeTimers(); sessionStorage.clear()})
  afterEach(() => {cleanup(); vi.useRealTimers(); vi.restoreAllMocks()})

  it('FT-01/02 waits 800 ms after the last keystroke and sends one draft', async () => {
    const {onSave} = edit()
    type('Bản 1'); await advance(500)
    type('Bản 2'); await advance(799)
    expect(onSave).not.toHaveBeenCalled()
    expect(screen.getByRole('status')).toHaveTextContent('Chưa lưu')
    await advance(1)
    expect(onSave).toHaveBeenCalledTimes(1)
    expect(onSave).toHaveBeenCalledWith('Bản 2', 0)
    expect(editor()).toHaveValue('Bản 2')
  })

  it('FT-03 only reports saved after the server acknowledges the exact draft', async () => {
    const request = deferred<ReturnType<typeof saved>>()
    edit(vi.fn().mockReturnValue(request.promise)); type('Đã sửa')
    await advance(800)
    expect(screen.getByRole('status')).toHaveTextContent('Đang lưu')
    expect(screen.queryByText(/Đã lưu văn bản/)).not.toBeInTheDocument()
    await act(async () => request.resolve(saved('Đã sửa')))
    expect(screen.getByRole('status')).toHaveTextContent('Đã lưu văn bản OCR chỉnh sửa')
  })

  it.each([
    ['FT-04 conflict', new ApiError(409, 'Revision conflict'), /xung đột/i],
    ['FT-05 server error', new ApiError(500, 'Máy chủ lỗi'), /Máy chủ lỗi/],
    ['FT-06 network failure', new TypeError('Failed to fetch'), /Failed to fetch/],
  ])('%s retains the draft and does not report success', async (_name, failure, message) => {
    const {onSave} = edit(vi.fn().mockRejectedValue(failure))
    type('Bản nháp cần giữ'); await advance(800)
    expect(screen.getByRole('alert')).toHaveTextContent(message)
    expect(editor()).toHaveValue('Bản nháp cần giữ')
    expect(screen.queryByText(/Đã lưu văn bản/)).not.toBeInTheDocument()
    await advance(5000)
    expect(onSave).toHaveBeenCalledTimes(1)
  })

  it('FT-07/08 serializes requests and never acknowledges new typing with an old response', async () => {
    const first = deferred<ReturnType<typeof saved>>()
    const second = deferred<ReturnType<typeof saved>>()
    const onSave = vi.fn().mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    edit(onSave); type('Bản A'); await advance(800)
    type('Bản B'); await advance(800)
    expect(onSave).toHaveBeenCalledTimes(1)
    await act(async () => first.resolve(saved('Bản A', 1)))
    expect(editor()).toHaveValue('Bản B')
    expect(screen.getByRole('status')).toHaveTextContent('Chưa lưu')
    expect(screen.queryByText(/Đã lưu văn bản/)).not.toBeInTheDocument()
    await advance(800)
    expect(onSave).toHaveBeenLastCalledWith('Bản B', 1)
    await act(async () => second.resolve(saved('Bản B', 2)))
    expect(editor()).toHaveValue('Bản B')
    expect(screen.getByRole('status')).toHaveTextContent('Đã lưu văn bản OCR chỉnh sửa')
  })

  it('FT-09 never saves a confirmed document, including a queued edit becoming read-only', async () => {
    const {rerender, onSave} = edit()
    type('Chưa gửi')
    rerender(<OCRTextCard cleanedText="Ban đầu" rawText="OCR GỐC" revision={0} readOnly onSave={onSave}/>)
    await advance(800)
    expect(onSave).not.toHaveBeenCalled()
    expect(screen.getByRole('textbox')).toBeDisabled()
    expect(screen.getByRole('textbox')).toHaveValue('Chưa gửi')
    expect(screen.queryByText(/Đã lưu văn bản/)).not.toBeInTheDocument()
  })

  it('FT-10 cancels queued work on unmount and ignores an old instance response', async () => {
    const queued = edit(); type('Chưa gửi'); queued.unmount(); await advance(1000)
    expect(queued.onSave).not.toHaveBeenCalled()
    const oldRequest = deferred<ReturnType<typeof saved>>()
    const old = edit(vi.fn().mockReturnValue(oldRequest.promise))
    type('Tài liệu cũ'); await advance(800); old.unmount()
    edit(); type('Tài liệu mới')
    await act(async () => oldRequest.resolve(saved('Tài liệu cũ')))
    expect(editor()).toHaveValue('Tài liệu mới')
    expect(screen.getByRole('status')).toHaveTextContent('Chưa lưu')
  })

  it('warns before leaving while a draft or request is unacknowledged', async () => {
    const request = deferred<ReturnType<typeof saved>>()
    edit(vi.fn().mockReturnValue(request.promise)); type('Chưa lưu'); await advance(800)
    const event = new Event('beforeunload', {cancelable: true})
    window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
    await act(async () => request.resolve(saved('Chưa lưu')))
    const cleanEvent = new Event('beforeunload', {cancelable: true})
    window.dispatchEvent(cleanEvent)
    expect(cleanEvent.defaultPrevented).toBe(false)
  })

  it('rejects whitespace locally without losing it', async () => {
    const {onSave} = edit(); type(' \n\t '); await advance(800)
    expect(onSave).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('không được để trống')
    expect(editor()).toHaveValue(' \n\t ')
  })

  it('does not claim success for a response that did not persist the submitted content', async () => {
    edit(vi.fn().mockResolvedValue(saved('Nội dung khác')))
    type('Bản cần lưu'); await advance(800)
    expect(screen.getByRole('alert')).toHaveTextContent('chưa xác nhận nội dung OCR')
    expect(editor()).toHaveValue('Bản cần lưu')
    expect(screen.queryByText(/Đã lưu văn bản/)).not.toBeInTheDocument()
  })

  it('does not silently rebase an unsaved draft onto an externally updated revision', async () => {
    const {onSave, rerender} = edit()
    type('Bản nháp của tôi')
    rerender(<OCRTextCard cleanedText="Bản từ client khác" rawText="OCR GỐC" revision={1} onSave={onSave}/>)
    await advance(800)
    expect(onSave).toHaveBeenCalledWith('Bản nháp của tôi', 0)
    expect(editor()).toHaveValue('Bản nháp của tôi')
  })

  it('persists a user revert made while a different draft is in flight', async () => {
    const request = deferred<ReturnType<typeof saved>>()
    const onSave = vi.fn().mockReturnValueOnce(request.promise).mockImplementation(async (text: string, revision: number) => saved(text, revision + 1))
    edit(onSave); type('Bản đang gửi'); await advance(800)
    type('Ban đầu')
    await act(async () => request.resolve(saved('Bản đang gửi')))
    expect(screen.getByRole('status')).toHaveTextContent('Chưa lưu')
    await advance(800)
    expect(onSave).toHaveBeenLastCalledWith('Ban đầu', 1)
    expect(screen.getByRole('status')).toHaveTextContent(/Đã lưu văn bản/)
  })

  it('retains newer typing with the acknowledged revision for recovery after an in-flight save', async () => {
    const request = deferred<ReturnType<typeof saved>>()
    const onSave = vi.fn().mockReturnValue(request.promise)
    const view = render(<OCRTextCard documentKey="doc" cleanedText="Ban đầu" revision={0} onSave={onSave}/>)
    fireEvent.click(screen.getByRole('button', {name: /Chỉnh sửa văn bản OCR/}))
    type('Bản A'); await advance(800); type('Bản B')
    await act(async () => request.resolve(saved('Bản A', 1)))
    view.unmount()
    render(<OCRTextCard documentKey="doc" cleanedText="Bản A" revision={1} onSave={vi.fn()}/>)
    expect(editor()).toHaveValue('Bản B')
    expect(screen.getByRole('note')).toHaveTextContent('Đã khôi phục bản nháp')
    expect(JSON.parse(sessionStorage.getItem('vt043:ocr-draft:doc')!)).toEqual({text: 'Bản B', expected_revision: 1})
  })

  it('keeps recovered confirmed drafts visible and read-only until explicitly discarded', async () => {
    sessionStorage.setItem('vt043:ocr-draft:doc', JSON.stringify({text: 'Cần đối chiếu', expected_revision: 0}))
    const onSave = vi.fn()
    render(<OCRTextCard documentKey="doc" cleanedText="Đã xác nhận" revision={1} readOnly onSave={onSave}/>)
    await advance(800)
    expect(editor()).toBeDisabled()
    expect(editor()).toHaveValue('Cần đối chiếu')
    expect(screen.getByRole('note')).toHaveTextContent('Đã khôi phục bản nháp')
    expect(onSave).not.toHaveBeenCalled()
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    fireEvent.click(screen.getByRole('button', {name: /Hủy/}))
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    expect(sessionStorage.getItem('vt043:ocr-draft:doc')).toBeNull()
  })

  it('warns explicitly when browser storage cannot protect a draft during navigation', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {throw new DOMException('Quota exceeded', 'QuotaExceededError')})
    render(<OCRTextCard documentKey="doc" cleanedText="Ban đầu" revision={0} onSave={vi.fn()}/>)
    fireEvent.click(screen.getByRole('button', {name: /Chỉnh sửa văn bản OCR/})); type('Nháp đang nhập')
    expect(editor()).toHaveValue('Nháp đang nhập')
    expect(screen.getByRole('note')).toHaveTextContent('Hãy sao chép nội dung trước khi điều hướng')
  })

  it('copies the visible recovered draft even after the document becomes read-only', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText}})
    sessionStorage.setItem('vt043:ocr-draft:doc', JSON.stringify({text: 'Nháp cần đối chiếu', expected_revision: 0}))
    render(<OCRTextCard documentKey="doc" cleanedText="Bản server" revision={1} readOnly onSave={vi.fn()}/>)
    fireEvent.click(screen.getByRole('button', {name: 'Sao chép bản nháp'}))
    await act(async () => {await Promise.resolve()})
    expect(writeText).toHaveBeenCalledWith('Nháp cần đối chiếu')
    expect(editor()).toHaveValue('Nháp cần đối chiếu')
  })

  it('requires a server acknowledgement for a revert after an ambiguous network failure', async () => {
    const onSave = vi.fn().mockRejectedValueOnce(new TypeError('Connection lost')).mockImplementation(async (text: string, revision: number) => saved(text, revision + 1))
    edit(onSave); type('Có thể đã lưu tại server'); await advance(800)
    expect(screen.getByRole('alert')).toHaveTextContent('Connection lost')
    type('Ban đầu')
    expect(screen.getByRole('status')).toHaveTextContent('Chưa lưu')
    await advance(800)
    expect(onSave).toHaveBeenLastCalledWith('Ban đầu', 0)
    expect(screen.getByRole('status')).toHaveTextContent(/Đã lưu văn bản/)
  })

  it('copies the displayed raw OCR after autosave when switching out of the clean editor', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText}})
    edit(); type('Bản đã chỉnh sửa'); await advance(800)
    fireEvent.click(screen.getByRole('tab', {name: 'OCR gốc'}))
    expect(screen.getByText('OCR GỐC')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', {name: 'Sao chép'}))
    await act(async () => {await Promise.resolve()})
    expect(writeText).toHaveBeenCalledWith('OCR GỐC')
  })
})
