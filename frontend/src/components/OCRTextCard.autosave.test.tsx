import {act, cleanup, fireEvent, render, screen} from '@testing-library/react'
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import '@testing-library/jest-dom/vitest'
import {ApiError} from '../api/client'
import OCRTextCard from './OCRTextCard'

const editor = () => screen.getByRole('textbox', {name: 'Nội dung OCR đã hiệu chỉnh'})
const type = (text: string) => fireEvent.change(editor(), {target: {value: text}})
const save = () => fireEvent.click(screen.getByRole('button', {name: 'Lưu OCR'}))
const advance = (ms: number) => act(async () => {await vi.advanceTimersByTimeAsync(ms)})
function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: Error) => void
  const promise = new Promise<T>((yes, no) => {resolve = yes; reject = no})
  return {promise, resolve, reject}
}
const saved = (text: string, revision = 1) => ({ocr_text_cleaned: text, ocr_revision: revision})
function edit(onSave = vi.fn().mockImplementation(async (text: string, revision: number) => saved(text, revision + 1))) {
  const view = render(<OCRTextCard documentKey="doc" cleanedText="Ban đầu" rawText="OCR GỐC" revision={0} onSave={onSave}/>)
  fireEvent.click(screen.getByRole('button', {name: /Chỉnh sửa văn bản OCR/}))
  return {...view, onSave}
}

describe('OCR explicit save (autosave regression)', () => {
  beforeEach(() => {vi.useFakeTimers(); sessionStorage.clear()})
  afterEach(() => {cleanup(); vi.useRealTimers(); vi.restoreAllMocks()})

  it('TC01 typing, deleting, pausing and blur never call the save API', async () => {
    const {onSave} = edit()
    expect(screen.getByRole('button', {name: 'Lưu OCR'})).toBeDisabled()
    type('Bản nháp'); await advance(10000)
    type(''); fireEvent.blur(editor()); await advance(10000)
    type('Nội dung cuối'); await advance(60000)
    expect(onSave).not.toHaveBeenCalled()
    expect(sessionStorage.getItem('vt043:ocr-draft:doc')).toBeNull()
    expect(screen.getByRole('status')).toHaveTextContent('Chưa lưu')
  })

  it('TC02 unmount and remount discard only the local draft without saving', async () => {
    const first = edit(); type('Chưa lưu'); first.unmount(); await advance(5000)
    expect(first.onSave).not.toHaveBeenCalled()
    edit()
    expect(editor()).toHaveValue('Ban đầu')
    expect(screen.getByRole('button', {name: 'Lưu OCR'})).toBeDisabled()
  })

  it('TC03 sends only on click and reports saved only after acknowledgement', async () => {
    const request = deferred<ReturnType<typeof saved>>()
    const {onSave} = edit(vi.fn().mockReturnValue(request.promise)); type('Đã sửa')
    await advance(5000); expect(onSave).not.toHaveBeenCalled()
    save(); expect(onSave).toHaveBeenCalledWith('Đã sửa', 0)
    expect(screen.getByRole('status')).toHaveTextContent('Đang lưu')
    expect(screen.queryByText(/Đã lưu văn bản/)).not.toBeInTheDocument()
    await act(async () => request.resolve(saved('Đã sửa')))
    expect(screen.getByRole('status')).toHaveTextContent('Đã lưu văn bản OCR chỉnh sửa')
    expect(screen.getByRole('button', {name: 'Lưu OCR'})).toBeDisabled()
  })

  it('TC04 cancel restores the latest acknowledged text without an API call', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const {onSave} = edit(); type('Đã lưu lần một'); save(); await advance(0)
    type('Bản bỏ đi'); fireEvent.click(screen.getByRole('button', {name: 'Hủy'}))
    expect(onSave).toHaveBeenCalledTimes(1)
    expect(editor()).toHaveValue('Đã lưu lần một')
    expect(screen.getByRole('button', {name: 'Lưu OCR'})).toBeDisabled()
  })

  it.each([
    ['TC05 conflict', new ApiError(409, 'Revision conflict'), /xung đột/i],
    ['TC05 server error', new ApiError(500, 'Máy chủ lỗi'), /Máy chủ lỗi/],
    ['TC05 network failure', new TypeError('Failed to fetch'), /Failed to fetch/],
  ])('%s retains the draft and retries only after another click', async (_name, failure, message) => {
    const onSave = vi.fn().mockRejectedValueOnce(failure).mockResolvedValue(saved('Bản nháp cần giữ'))
    edit(onSave); type('Bản nháp cần giữ'); save(); await advance(0)
    expect(screen.getByRole('alert')).toHaveTextContent(message)
    expect(editor()).toHaveValue('Bản nháp cần giữ')
    expect(screen.queryByText(/Đã lưu văn bản/)).not.toBeInTheDocument()
    await advance(10000); expect(onSave).toHaveBeenCalledTimes(1)
    save(); await advance(0)
    expect(onSave).toHaveBeenCalledTimes(2)
    expect(screen.getByRole('status')).toHaveTextContent(/Đã lưu văn bản/)
  })

  it('TC06 rejects repeated clicks while a save is pending', async () => {
    const request = deferred<ReturnType<typeof saved>>()
    const {onSave} = edit(vi.fn().mockReturnValue(request.promise)); type('Một request')
    save()
    fireEvent.click(screen.getByRole('button', {name: 'Đang lưu…'}))
    fireEvent.click(screen.getByRole('button', {name: 'Đang lưu…'}))
    await advance(10000); expect(onSave).toHaveBeenCalledTimes(1)
    await act(async () => request.resolve(saved('Một request')))
  })

  it('TC07 changing OCR tabs preserves the draft without saving or discarding', async () => {
    const confirm = vi.spyOn(window, 'confirm')
    const {onSave} = edit(); type('Giữ bản nháp')
    fireEvent.click(screen.getByRole('tab', {name: 'OCR gốc'}))
    expect(screen.getByText('OCR GỐC')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', {name: 'Cấu trúc tài liệu'}))
    fireEvent.click(screen.getByRole('tab', {name: 'Văn bản dễ đọc'}))
    expect(editor()).toHaveValue('Giữ bản nháp')
    await advance(10000)
    expect(onSave).not.toHaveBeenCalled()
    expect(confirm).not.toHaveBeenCalled()
  })

  it('TC08 warns on reload until the submitted text is acknowledged', async () => {
    const request = deferred<ReturnType<typeof saved>>()
    edit(vi.fn().mockReturnValue(request.promise)); type('Chưa lưu')
    for (const sending of [false, true]) {
      if (sending) save()
      const event = new Event('beforeunload', {cancelable: true})
      window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true)
    }
    await act(async () => request.resolve(saved('Chưa lưu')))
    const event = new Event('beforeunload', {cancelable: true})
    window.dispatchEvent(event); expect(event.defaultPrevented).toBe(false)
  })

  it('TC09 manual save does not overwrite the raw OCR tab', async () => {
    edit(); type('Bản đã chỉnh sửa'); save(); await advance(0)
    fireEvent.click(screen.getByRole('tab', {name: 'OCR gốc'}))
    expect(screen.getByText('OCR GỐC')).toBeInTheDocument()
  })

  it('typing during an explicit save stays dirty and requires a second explicit save', async () => {
    const first = deferred<ReturnType<typeof saved>>()
    const onSave = vi.fn().mockReturnValueOnce(first.promise).mockImplementation(async (text: string, revision: number) => saved(text, revision + 1))
    edit(onSave); type('Bản A'); save(); type('Bản B')
    await act(async () => first.resolve(saved('Bản A', 1)))
    expect(editor()).toHaveValue('Bản B')
    expect(screen.getByRole('status')).toHaveTextContent('Chưa lưu')
    await advance(10000); expect(onSave).toHaveBeenCalledTimes(1)
    save(); await advance(0)
    expect(onSave).toHaveBeenLastCalledWith('Bản B', 1)
  })

  it('does not silently rebase an unsaved draft onto another client revision', async () => {
    const {onSave, rerender} = edit(); type('Bản nháp của tôi')
    rerender(<OCRTextCard cleanedText="Bản từ client khác" rawText="OCR GỐC" revision={1} onSave={onSave}/>)
    await advance(10000); expect(onSave).not.toHaveBeenCalled()
    save(); expect(onSave).toHaveBeenCalledWith('Bản nháp của tôi', 0)
  })

  it('never saves confirmed documents', async () => {
    const {rerender, onSave} = edit(); type('Chưa gửi')
    rerender(<OCRTextCard cleanedText="Ban đầu" rawText="OCR GỐC" revision={0} readOnly onSave={onSave}/>)
    await advance(10000)
    expect(onSave).not.toHaveBeenCalled()
    expect(editor()).toBeDisabled()
    expect(screen.getByRole('button', {name: 'Lưu OCR'})).toBeDisabled()
  })

  it('ignores a manual save response after the old document unmounts', async () => {
    const oldRequest = deferred<ReturnType<typeof saved>>()
    const old = edit(vi.fn().mockReturnValue(oldRequest.promise)); type('Tài liệu cũ'); save(); old.unmount()
    const current = edit(); type('Tài liệu mới')
    await act(async () => oldRequest.resolve(saved('Tài liệu cũ')))
    expect(editor()).toHaveValue('Tài liệu mới')
    await advance(10000); expect(current.onSave).not.toHaveBeenCalled()
  })

  it('rejects whitespace only when Save is clicked and retains it', async () => {
    const {onSave} = edit(); type(' \n\t '); await advance(5000)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    save(); expect(onSave).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('không được để trống')
    expect(editor()).toHaveValue(' \n\t ')
  })

  it('does not claim success without a valid server acknowledgement', async () => {
    edit(vi.fn().mockResolvedValue(saved('Nội dung khác'))); type('Bản cần lưu'); save(); await advance(0)
    expect(screen.getByRole('alert')).toHaveTextContent('chưa xác nhận nội dung OCR')
    expect(editor()).toHaveValue('Bản cần lưu')
  })

  it('never restores or auto-submits a legacy sessionStorage draft', async () => {
    sessionStorage.setItem('vt043:ocr-draft:doc', JSON.stringify({text: 'Nháp cũ', expected_revision: 0}))
    const {onSave} = edit(); await advance(10000)
    expect(editor()).toHaveValue('Ban đầu'); expect(onSave).not.toHaveBeenCalled()
  })
})
