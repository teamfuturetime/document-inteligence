import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import mockResult from '../../../../schemas/fixtures/extraction-success.json'
import { DocumentSelection } from './DocumentSelection'

const file = () => new File(['synthetic'], 'sample.png', { type: 'image/png' })

it('posts multipart and displays an explicitly labelled mock result', async () => {
  const fetch = vi.fn().mockResolvedValue(Response.json(mockResult))
  vi.stubGlobal('fetch', fetch)
  const user = userEvent.setup()
  render(<DocumentSelection />)
  await user.upload(screen.getByLabelText('Chọn PNG, JPG hoặc PDF'), file())
  await user.click(screen.getByRole('button', { name: 'Trích xuất hóa đơn' }))
  expect(await screen.findByText('Kết quả mock — chưa chạy OCR')).toBeVisible()
  expect(screen.getByText('SYN-0001')).toBeVisible()
  expect(screen.getByText(/không được suy ra từ tài liệu/)).toBeVisible()
  expect(screen.getByText(/Đã gửi lên server/)).toBeVisible()
  const [url, options] = fetch.mock.calls[0]
  expect(url).toBe('/api/v1/extract')
  expect(options.method).toBe('POST')
  expect(options.body.get('file').name).toBe('sample.png')
  expect(options.headers).not.toHaveProperty('Content-Type')
})

it('disables duplicate submission while upload is pending', async () => {
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(() => {})))
  const user = userEvent.setup()
  render(<DocumentSelection />)
  await user.upload(screen.getByLabelText('Chọn PNG, JPG hoặc PDF'), file())
  await user.click(screen.getByRole('button', { name: 'Trích xuất hóa đơn' }))
  expect(screen.getByRole('button', { name: 'Đang gửi…' })).toBeDisabled()
})

it('keeps the selected file and allows retry after upload failure', async () => {
  const fetch = vi.fn()
    .mockResolvedValueOnce(Response.json({ error: { code: 'invalid_document', message: 'Ảnh bị lỗi.', field: null } }, { status: 422 }))
    .mockResolvedValueOnce(Response.json(mockResult))
  vi.stubGlobal('fetch', fetch)
  const user = userEvent.setup()
  render(<DocumentSelection />)
  await user.upload(screen.getByLabelText('Chọn PNG, JPG hoặc PDF'), file())
  await user.click(screen.getByRole('button', { name: 'Trích xuất hóa đơn' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Ảnh bị lỗi.')
  expect(screen.getByText('sample.png')).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Trích xuất hóa đơn' }))
  expect(await screen.findByText('SYN-0001')).toBeVisible()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})

it('does not show a stale result after the selected file is replaced', async () => {
  let resolve!: (response: Response) => void
  let signal!: AbortSignal
  vi.stubGlobal('fetch', vi.fn((_url: string, options: RequestInit) => {
    signal = options.signal as AbortSignal
    return new Promise<Response>(done => { resolve = done })
  }))
  const user = userEvent.setup()
  render(<DocumentSelection />)
  const input = screen.getByLabelText('Chọn PNG, JPG hoặc PDF')
  await user.upload(input, file())
  await user.click(screen.getByRole('button', { name: 'Trích xuất hóa đơn' }))
  await user.upload(input, new File(['other'], 'replacement.pdf', { type: 'application/pdf' }))
  expect(signal.aborted).toBe(true)
  resolve(Response.json(mockResult))
  // Follow-up interaction flushes the resolved promise without sleeping.
  await user.click(screen.getByRole('button', { name: 'Bỏ chọn' }))
  expect(screen.queryByText('SYN-0001')).not.toBeInTheDocument()
  expect(screen.getByText('Chưa chọn tài liệu.')).toBeVisible()
})

it('clears a completed result when the file is removed', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue(Response.json(mockResult)))
  const user = userEvent.setup()
  render(<DocumentSelection />)
  await user.upload(screen.getByLabelText('Chọn PNG, JPG hoặc PDF'), file())
  await user.click(screen.getByRole('button', { name: 'Trích xuất hóa đơn' }))
  await screen.findByText('SYN-0001')
  await user.click(screen.getByRole('button', { name: 'Bỏ chọn' }))
  expect(screen.queryByText('SYN-0001')).not.toBeInTheDocument()
})
