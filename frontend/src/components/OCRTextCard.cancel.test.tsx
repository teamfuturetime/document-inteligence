import {act, cleanup, fireEvent, render, screen} from '@testing-library/react'
import {afterEach, beforeEach, describe, expect, it, vi} from 'vitest'
import '@testing-library/jest-dom/vitest'
import OCRTextCard from './OCRTextCard'

const original = 'OCR GỐC DO MÁY NHẬN DẠNG'
const initial = 'HÓA ĐƠN THANH TOÁN'
const changed = 'HÓA ĐƠN THANH TOÁN ĐÃ THAY ĐỔI'
const editor = () => screen.getByRole('textbox', {name: 'Nội dung OCR đã hiệu chỉnh'})
const type = (value: string) => fireEvent.change(editor(), {target: {value}})
const cancel = () => fireEvent.click(screen.getByRole('button', {name: 'Hủy'}))
const save = () => fireEvent.click(screen.getByRole('button', {name: 'Lưu OCR'}))
const flush = () => act(async () => {await Promise.resolve()})
function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(yes => {resolve = yes})
  return {promise, resolve}
}
function view(onSave = vi.fn().mockImplementation(async (text: string, revision: number) => ({ocr_text_cleaned: text, ocr_revision: revision + 1}))) {
  const onDirtyChange = vi.fn()
  const result = render(<OCRTextCard cleanedText={initial} rawText={original} revision={3} corrected onSave={onSave} onDirtyChange={onDirtyChange}/>)
  fireEvent.click(screen.getByRole('button', {name: /Chỉnh sửa văn bản OCR/}))
  return {...result, onSave, onDirtyChange}
}

describe('OCR Cancel restores the acknowledged correction', () => {
  beforeEach(() => {vi.spyOn(window, 'confirm').mockReturnValue(false)})
  afterEach(() => {cleanup(); vi.restoreAllMocks()})

  it('TC01/05/06 resets the controlled textarea immediately and clears dirty without any confirmation or save', () => {
    const {onSave, onDirtyChange} = view()
    type(changed); cancel()
    expect(editor()).toHaveValue(initial)
    expect(screen.getByRole('button', {name: 'Lưu OCR'})).toBeDisabled()
    expect(onDirtyChange).toHaveBeenLastCalledWith(false)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(onSave).not.toHaveBeenCalled()
    expect(window.confirm).not.toHaveBeenCalled()
    expect(screen.getByText('Đã được người dùng chỉnh sửa')).toBeInTheDocument()
  })

  it('TC02 cancel then remount still reads the same persisted content', () => {
    const first = view(); type(changed); cancel(); first.unmount()
    const second = view()
    expect(editor()).toHaveValue(initial)
    expect(first.onSave).not.toHaveBeenCalled()
    expect(second.onSave).not.toHaveBeenCalled()
  })

  it('TC03 restores the newest acknowledged save, even while parent props still contain an older value', async () => {
    const {onSave} = view()
    type(changed); save(); await flush()
    expect(screen.getByRole('status')).toHaveTextContent('Đã lưu')
    type('Sửa lần thứ hai'); cancel()
    expect(editor()).toHaveValue(changed)
    expect(onSave).toHaveBeenCalledTimes(1)
    expect(onSave).toHaveBeenCalledWith(changed, 3)
    expect(screen.getByRole('button', {name: 'Lưu OCR'})).toBeDisabled()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('TC04 tab changes keep the draft until Cancel restores the saved correction', () => {
    const {onSave} = view(); type(changed)
    fireEvent.click(screen.getByRole('tab', {name: 'OCR gốc'}))
    expect(screen.getByText(original)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', {name: 'Cấu trúc tài liệu'}))
    fireEvent.click(screen.getByRole('tab', {name: 'Văn bản dễ đọc'}))
    expect(editor()).toHaveValue(changed)
    cancel(); expect(editor()).toHaveValue(initial)
    expect(onSave).not.toHaveBeenCalled()
  })

  it('TC07 failed save retains the draft and Cancel restores saved text without retrying', async () => {
    const {onSave} = view(vi.fn().mockRejectedValue(new Error('Lưu thất bại')))
    type(changed); save(); await flush()
    expect(editor()).toHaveValue(changed)
    expect(screen.getByRole('alert')).toHaveTextContent('Lưu thất bại')
    cancel()
    expect(editor()).toHaveValue(initial)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
    expect(screen.getByRole('button', {name: 'Lưu OCR'})).toBeDisabled()
    expect(onSave).toHaveBeenCalledTimes(1)
  })

  it('TC08 disables Cancel during a pending save and resets newer typing only after its acknowledgement', async () => {
    const request = deferred<{ocr_text_cleaned: string; ocr_revision: number}>()
    const {onSave} = view(vi.fn().mockReturnValue(request.promise))
    type(changed); save(); type('Bản nhập khi request đang chạy')
    expect(screen.getByRole('button', {name: 'Hủy'})).toBeDisabled()
    cancel()
    expect(editor()).toHaveValue('Bản nhập khi request đang chạy')
    await act(async () => request.resolve({ocr_text_cleaned: changed, ocr_revision: 4}))
    expect(editor()).toHaveValue('Bản nhập khi request đang chạy')
    expect(screen.getByRole('button', {name: 'Hủy'})).toBeEnabled()
    cancel(); await flush()
    expect(editor()).toHaveValue(changed)
    expect(screen.getByRole('button', {name: 'Lưu OCR'})).toBeDisabled()
    expect(onSave).toHaveBeenCalledTimes(1)
  })

  it('TC08 incoming parent props do not reapply a discarded draft or older raw OCR', async () => {
    const {onSave, onDirtyChange, rerender} = view()
    type(changed); save(); await flush()
    type('Bản sẽ hủy'); cancel()
    rerender(<OCRTextCard cleanedText={initial} rawText={original} revision={3} corrected onSave={onSave} onDirtyChange={onDirtyChange}/>)
    expect(editor()).toHaveValue(changed)
    expect(screen.getByRole('button', {name: 'Lưu OCR'})).toBeDisabled()
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('TC09 Cancel does not change raw OCR or mark an unsaved correction as saved', () => {
    const onSave = vi.fn()
    render(<OCRTextCard cleanedText={initial} rawText={original} corrected={false} onSave={onSave}/>)
    fireEvent.click(screen.getByRole('button', {name: /Chỉnh sửa văn bản OCR/}))
    type(changed); cancel()
    expect(screen.queryByText('Đã được người dùng chỉnh sửa')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', {name: 'OCR gốc'}))
    expect(screen.getByText(original)).toBeInTheDocument()
    expect(onSave).not.toHaveBeenCalled()
  })
})
