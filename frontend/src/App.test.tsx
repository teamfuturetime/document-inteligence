import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import App from './App'

const health = { status: 'ok', mode: 'mock', ocr_ready: false }

it('shows implementation status and sends no requests before interaction', () => {
  const fetch = vi.fn()
  vi.stubGlobal('fetch', fetch)
  render(<App />)
  expect(screen.getByRole('heading', { level: 1 })).toBeVisible()
  expect(screen.getByText('Chưa chọn tài liệu.')).toBeVisible()
  expect(screen.getByText('OCR · Review · Xuất JSON')).toBeVisible()
  expect(fetch).not.toHaveBeenCalled()
})

it('shows loading and then distinguishes connectivity from OCR readiness', async () => {
  let resolve!: (response: Response) => void
  vi.stubGlobal('fetch', vi.fn(() => new Promise<Response>(done => { resolve = done })))
  const user = userEvent.setup()
  render(<App />)
  await user.click(screen.getByRole('button', { name: 'Kiểm tra kết nối' }))
  expect(screen.getByRole('button', { name: 'Đang kiểm tra…' })).toBeDisabled()
  resolve(Response.json(health))
  expect(await screen.findByText('Backend đang hoạt động.')).toBeVisible()
  expect(screen.getByText('Mock')).toBeVisible()
  expect(screen.getByText('Chưa sẵn sàng')).toBeVisible()
})

it('allows retry after backend failure', async () => {
  const fetch = vi.fn().mockRejectedValueOnce(new TypeError('network')).mockResolvedValueOnce(Response.json(health))
  vi.stubGlobal('fetch', fetch)
  const user = userEvent.setup()
  render(<App />)
  await user.click(screen.getByRole('button', { name: 'Kiểm tra kết nối' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Không kết nối được backend')
  await user.click(screen.getByRole('button', { name: 'Kiểm tra kết nối' }))
  expect(await screen.findByText('Backend đang hoạt động.')).toBeVisible()
  expect(screen.queryByRole('alert')).not.toBeInTheDocument()
})

it('aborts the request when the component is unmounted', async () => {
  let signal!: AbortSignal
  vi.stubGlobal('fetch', vi.fn((_url: string, options: RequestInit) => {
    signal = options.signal as AbortSignal
    return new Promise<Response>(() => {})
  }))
  const user = userEvent.setup()
  const { unmount } = render(<App />)
  await user.click(screen.getByRole('button', { name: 'Kiểm tra kết nối' }))
  unmount()
  expect(signal.aborted).toBe(true)
})

it('selects and clears a file without uploading it', async () => {
  const fetch = vi.fn()
  vi.stubGlobal('fetch', fetch)
  const user = userEvent.setup()
  render(<App />)
  await user.upload(screen.getByLabelText('Chọn PNG, JPG hoặc PDF'), new File(['synthetic'], 'sample.png', { type: 'image/png' }))
  expect(screen.getByText('sample.png')).toBeVisible()
  expect(screen.getByText(/Chưa gửi lên server/)).toBeVisible()
  await user.click(screen.getByRole('button', { name: 'Bỏ chọn' }))
  expect(screen.getByText('Chưa chọn tài liệu.')).toBeVisible()
  expect(fetch).not.toHaveBeenCalled()
})

it('clears the previous valid selection when a replacement is invalid', async () => {
  const user = userEvent.setup({ applyAccept: false })
  render(<App />)
  const input = screen.getByLabelText('Chọn PNG, JPG hoặc PDF')
  await user.upload(input, new File(['sample'], 'sample.pdf', { type: 'application/pdf' }))
  await user.upload(input, new File(['unsupported'], 'sample.txt', { type: 'text/plain' }))
  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Chỉ hỗ trợ'))
  expect(screen.queryByText('sample.pdf')).not.toBeInTheDocument()
  expect(screen.getByText('Chưa chọn tài liệu.')).toBeVisible()
})
